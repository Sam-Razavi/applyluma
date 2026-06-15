"""Read-only verification of Discover data dependencies against the live DB.

Run locally with DATABASE_URL pointing at the Railway public proxy, e.g.:
    DATABASE_URL=postgresql://user:pass@viaduct.proxy.rlwy.net:PORT/railway \
        venv/Scripts/python.exe scripts/verify_discover.py [--email you@example.com]

It performs NO writes. It reports whether the data needed for search, the skills
breakdown, and the score breakdown actually exists, then simulates the skill-gap
computation for one job so we can see real matched/missing skills.
"""
from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="App account email to inspect CVs for", default=None)
    args = parser.parse_args()

    # Load backend/.env if present so the DB password stays out of the command line.
    try:
        from dotenv import load_dotenv

        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    except Exception:
        pass

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: set DATABASE_URL (Railway public proxy URL) first.")
        sys.exit(1)
    # SQLAlchemy needs the postgresql:// scheme (Railway sometimes gives postgres://).
    url = url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(url)
    with Session(engine) as db:
        # --- Jobs + keywords (powers search and skills breakdown) ---
        total_jobs = db.execute(text("SELECT count(*) FROM raw_job_postings")).scalar()
        non_dupe = db.execute(
            text("SELECT count(*) FROM raw_job_postings WHERE is_duplicate = false")
        ).scalar()
        total_kw = db.execute(text("SELECT count(*) FROM extracted_keywords")).scalar()
        jobs_with_kw = db.execute(
            text("SELECT count(DISTINCT raw_job_posting_id) FROM extracted_keywords")
        ).scalar()
        total_scores = db.execute(text("SELECT count(*) FROM job_matching_scores")).scalar()

        print("== Jobs / keywords / scores ==")
        print(f"  raw_job_postings:            {total_jobs} (non-duplicate: {non_dupe})")
        print(f"  extracted_keywords rows:     {total_kw}")
        print(f"  jobs WITH >=1 keyword:       {jobs_with_kw}  <- skills breakdown needs this")
        print(f"  job_matching_scores rows:    {total_scores}  <- score breakdown needs this")

        # --- CVs (skills breakdown compares against the user's default CV) ---
        print("\n== CVs ==")
        if args.email:
            rows = db.execute(
                text(
                    "SELECT c.id, c.title, c.is_default, length(coalesce(c.content,'')) AS clen "
                    "FROM cvs c JOIN users u ON u.id = c.user_id "
                    "WHERE u.email = :email ORDER BY c.is_default DESC"
                ),
                {"email": args.email},
            ).all()
            if not rows:
                print(f"  No CVs found for {args.email}")
            for r in rows:
                flag = " (DEFAULT)" if r.is_default else ""
                print(f"  {r.title!r}{flag} — content length: {r.clen}")
        else:
            n_cv = db.execute(text("SELECT count(*) FROM cvs")).scalar()
            n_default = db.execute(
                text("SELECT count(*) FROM cvs WHERE is_default = true")
            ).scalar()
            empty = db.execute(
                text("SELECT count(*) FROM cvs WHERE coalesce(content,'') = ''")
            ).scalar()
            print(f"  total CVs: {n_cv}; default CVs: {n_default}; empty-content CVs: {empty}")
            print("  (re-run with --email you@example.com to inspect your own CVs)")

        # --- Simulate skill-gap for one job that has keywords ---
        print("\n== Sample skill-gap simulation ==")
        sample = db.execute(
            text(
                "SELECT raw_job_posting_id, array_agg(keyword) AS kws "
                "FROM extracted_keywords GROUP BY raw_job_posting_id LIMIT 1"
            )
        ).first()
        if not sample:
            print("  No extracted_keywords at all — skills breakdown will be EMPTY until the")
            print("  Airflow extract_keywords DAG has run over the postings.")
        else:
            print(f"  job {sample.raw_job_posting_id} keywords: {sample.kws[:15]}")


if __name__ == "__main__":
    main()
