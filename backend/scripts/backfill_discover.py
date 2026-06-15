"""One-off backfill for Discover: populate extracted_keywords + job_matching_scores.

The scraped postings were never run through the Airflow keyword/matching pipeline,
so the Discover skills + score breakdowns have no data. This script replicates what
that pipeline would have produced. It is ADDITIVE and idempotent:

  * Keywords: extracts typed keywords from each non-duplicate posting's description
    and inserts extracted_keywords rows. Postings that already have keywords are
    skipped, so re-running is safe.
  * Scores: computes match scores for the target user's default CV across all
    non-duplicate postings and UPSERTs job_matching_scores.

It never edits or deletes existing raw_job_postings / CV data.

Usage (loads backend/.env for DATABASE_URL):
    venv/Scripts/python.exe scripts/backfill_discover.py --email you@example.com
    venv/Scripts/python.exe scripts/backfill_discover.py --email you@example.com --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_all_models() -> None:
    """Import every app.models.* module so SQLAlchemy can resolve relationships."""
    import importlib
    import pkgutil

    import app.models as models_pkg

    for mod in pkgutil.iter_modules(models_pkg.__path__):
        importlib.import_module(f"app.models.{mod.name}")


def _load_env() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    except Exception:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: set DATABASE_URL in backend/.env first.")
        sys.exit(1)
    return url.replace("postgres://", "postgresql://", 1)


def backfill_keywords(db, dry_run: bool) -> int:
    from app.models.job import ExtractedKeyword, RawJobPosting
    from app.services.keyword_extractor import KeywordExtractor

    extractor = KeywordExtractor()
    postings = (
        db.query(RawJobPosting)
        .filter(RawJobPosting.is_duplicate.is_(False))
        .all()
    )
    # Skip postings that already have keywords (idempotent re-runs).
    already = {
        pid for (pid,) in db.query(ExtractedKeyword.raw_job_posting_id).distinct().all()
    }

    inserted = 0
    processed = 0
    for posting in postings:
        if posting.id in already:
            continue
        processed += 1
        extracted = extractor.extract_keywords(posting.description or "")
        for category, items in extracted.items():
            for item in items:
                inserted += 1
                if not dry_run:
                    db.add(
                        ExtractedKeyword(
                            raw_job_posting_id=posting.id,
                            keyword=item["keyword"],
                            keyword_type=category,
                            confidence_score=item["confidence"],
                            frequency=item["frequency"],
                        )
                    )
        if not dry_run and processed % 100 == 0:
            db.commit()
            print(f"  ...committed keywords for {processed} postings")

    if not dry_run:
        db.commit()
    print(f"Keywords: processed {processed} postings, {inserted} keyword rows "
          f"{'(dry-run, not written)' if dry_run else 'inserted'}.")
    return inserted


def backfill_scores(db, email: str, dry_run: bool) -> int:
    from app.models.cv import CV
    from app.models.job import JobMatchingScore, RawJobPosting
    from app.models.user import User
    from app.services.matching_service import MatchingService

    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        print(f"Scores: no user found for {email!r} — skipping score backfill.")
        return 0
    default_cv = (
        db.query(CV).filter(CV.user_id == user.id, CV.is_default.is_(True)).first()
    )
    if not default_cv or not default_cv.content:
        print(f"Scores: user {email} has no default CV with content — skipping.")
        return 0

    service = MatchingService(db)
    postings = (
        db.query(RawJobPosting)
        .filter(RawJobPosting.is_duplicate.is_(False))
        .all()
    )
    existing = {
        pid: row
        for pid, row in (
            (r.raw_job_posting_id, r)
            for r in db.query(JobMatchingScore).filter(JobMatchingScore.user_id == user.id).all()
        )
    }

    scored = 0
    for posting in postings:
        job_data = {
            "description": posting.description,
            "title": posting.title,
            "salary_min": posting.salary_min,
            "salary_max": posting.salary_max,
            "location": posting.location,
            "remote_allowed": posting.remote_allowed,
        }
        try:
            result = service.calculate_match_score(user.id, posting.id, job_data)
        except Exception:
            continue
        scored += 1
        if dry_run:
            continue
        now = datetime.now(UTC)
        row = existing.get(posting.id)
        if row:
            row.overall_score = result["overall_score"]
            row.skills_match = result["skills_match"]
            row.experience_match = result["experience_match"]
            row.salary_match = result["salary_match"]
            row.education_match = result["education_match"]
            row.location_match = result["location_match"]
            row.explanation = result["explanation"]
            row.computed_at = now
            row.cached_at = now
        else:
            db.add(
                JobMatchingScore(
                    user_id=user.id,
                    raw_job_posting_id=posting.id,
                    overall_score=result["overall_score"],
                    skills_match=result["skills_match"],
                    experience_match=result["experience_match"],
                    salary_match=result["salary_match"],
                    education_match=result["education_match"],
                    location_match=result["location_match"],
                    explanation=result["explanation"],
                    computed_at=now,
                    cached_at=now,
                )
            )
        if scored % 200 == 0:
            db.commit()
            print(f"  ...committed scores for {scored} postings")

    if not dry_run:
        db.commit()
    print(f"Scores: computed {scored} for {email} "
          f"{'(dry-run, not written)' if dry_run else 'upserted'}.")
    return scored


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="App account email to score jobs for")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write")
    args = parser.parse_args()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    engine = create_engine(_load_env())
    _load_all_models()
    with Session(engine) as db:
        print(f"=== Backfill (dry_run={args.dry_run}) ===")
        backfill_keywords(db, args.dry_run)
        backfill_scores(db, args.email, args.dry_run)
        print("Done.")


if __name__ == "__main__":
    main()
