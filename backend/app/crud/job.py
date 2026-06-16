"""CRUD operations for Phase 10A job discovery."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.application import Application
from app.models.cv import CV
from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting, SavedJob
from app.schemas.job import ExternalJobBookmarkRequest, SaveJobRequest, UpdateSavedJobRequest
from app.services.keyword_extractor import KeywordExtractor

# ------------------------------------------------------------------
# Jobs
# ------------------------------------------------------------------

def list_jobs(
    db: Session,
    user_id: uuid.UUID,
    *,
    location: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    keywords: list[str] | None = None,
    source: str | None = None,
    match_score_min: float | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "score_desc",
) -> list[dict[str, Any]]:
    """Return a paginated list of jobs with match scores for the user."""
    q = (
        db.query(RawJobPosting, JobMatchingScore, Application, SavedJob)
        .options(selectinload(RawJobPosting.keywords))
        .outerjoin(
            JobMatchingScore,
            (JobMatchingScore.raw_job_posting_id == RawJobPosting.id)
            & (JobMatchingScore.user_id == user_id),
        )
        .outerjoin(
            Application,
            (Application.raw_job_posting_id == RawJobPosting.id)
            & (Application.user_id == user_id),
        )
        .outerjoin(
            SavedJob,
            (SavedJob.raw_job_posting_id == RawJobPosting.id)
            & (SavedJob.user_id == user_id),
        )
        .filter(RawJobPosting.is_duplicate.is_(False))
    )

    if location:
        q = q.filter(RawJobPosting.location.ilike(f"%{location}%"))
    if salary_min is not None:
        q = q.filter(
            (RawJobPosting.salary_min >= salary_min)
            | (RawJobPosting.salary_min.is_(None))
        )
    if salary_max is not None:
        q = q.filter(
            (RawJobPosting.salary_max <= salary_max)
            | (RawJobPosting.salary_max.is_(None))
        )
    if source:
        q = q.filter(RawJobPosting.source == source)
    if match_score_min is not None:
        q = q.filter(JobMatchingScore.overall_score >= match_score_min)
    if search:
        q = q.filter(
            RawJobPosting.title.ilike(f"%{search}%")
            | RawJobPosting.company.ilike(f"%{search}%")
        )
    if keywords:
        keyword_ids = (
            db.query(ExtractedKeyword.raw_job_posting_id)
            .filter(ExtractedKeyword.keyword.in_(keywords))
            .subquery()
        )
        q = q.filter(RawJobPosting.id.in_(keyword_ids))

    if sort == "salary_desc":
        q = q.order_by(nullslast(desc(RawJobPosting.salary_max)))
    elif sort == "date_posted":
        q = q.order_by(desc(RawJobPosting.scraped_at))
    else:
        q = q.order_by(nullslast(desc(JobMatchingScore.overall_score)))

    offset = (page - 1) * limit
    rows = q.offset(offset).limit(limit).all()

    results = []
    for posting, score, application, saved_job in rows:
        results.append(
            _job_to_dict(posting, score, application, saved_job, keywords=posting.keywords)
        )
    return results


def get_job_with_score(
    db: Session,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Return a job with its match score for the given user."""
    row = (
        db.query(RawJobPosting, JobMatchingScore, Application, SavedJob)
        .outerjoin(
            JobMatchingScore,
            (JobMatchingScore.raw_job_posting_id == RawJobPosting.id)
            & (JobMatchingScore.user_id == user_id),
        )
        .outerjoin(
            Application,
            (Application.raw_job_posting_id == RawJobPosting.id)
            & (Application.user_id == user_id),
        )
        .outerjoin(
            SavedJob,
            (SavedJob.raw_job_posting_id == RawJobPosting.id)
            & (SavedJob.user_id == user_id),
        )
        .filter(RawJobPosting.id == job_id)
        .first()
    )
    if not row:
        return None

    posting, score, application, saved_job = row
    matched_skills, missing_skills = _compute_skill_gap(db, user_id, posting)
    return _job_to_dict(
        posting,
        score,
        application,
        saved_job,
        include_description=True,
        keywords=posting.keywords,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )


def get_job_keywords(
    db: Session,
    job_id: uuid.UUID,
) -> dict[str, list[str]]:
    """Return extracted keywords grouped by type."""
    keywords = (
        db.query(ExtractedKeyword)
        .filter(ExtractedKeyword.raw_job_posting_id == job_id)
        .order_by(ExtractedKeyword.keyword_type, ExtractedKeyword.confidence_score.desc())
        .all()
    )

    result: dict[str, list[str]] = {
        "technical_skills": [],
        "frameworks": [],
        "tools": [],
        "soft_skills": [],
        "languages": [],
        "certifications": [],
    }
    for kw in keywords:
        category = kw.keyword_type
        if category in result:
            result[category].append(kw.keyword)
        else:
            result.setdefault(category, []).append(kw.keyword)
    return result


# ------------------------------------------------------------------
# Saved jobs
# ------------------------------------------------------------------

def save_job(
    db: Session,
    user_id: uuid.UUID,
    body: SaveJobRequest,
) -> SavedJob:
    """Save a job to the user's collection. If already saved, return the existing row."""
    existing = (
        db.query(SavedJob)
        .filter(
            SavedJob.user_id == user_id,
            SavedJob.raw_job_posting_id == body.job_id,
        )
        .first()
    )
    if existing:
        if body.list_name:
            existing.list_name = body.list_name
        if body.notes:
            existing.notes = body.notes
        db.commit()
        db.refresh(existing)
        return existing

    saved = SavedJob(
        user_id=user_id,
        raw_job_posting_id=body.job_id,
        list_name=body.list_name,
        notes=body.notes,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


def list_saved_jobs(
    db: Session,
    user_id: uuid.UUID,
    list_name: str | None = None,
    sort: str = "newest",
) -> list[SavedJob]:
    q = (
        db.query(SavedJob)
        .options(joinedload(SavedJob.job))
        .filter(SavedJob.user_id == user_id)
    )
    if list_name:
        q = q.filter(SavedJob.list_name == list_name)
    if sort == "oldest":
        q = q.order_by(SavedJob.created_at.asc())
    else:
        q = q.order_by(SavedJob.created_at.desc())
    return q.all()


def get_saved_job(
    db: Session,
    saved_job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SavedJob | None:
    return (
        db.query(SavedJob)
        .filter(SavedJob.id == saved_job_id, SavedJob.user_id == user_id)
        .first()
    )


def update_saved_job(
    db: Session,
    saved: SavedJob,
    updates: UpdateSavedJobRequest,
) -> SavedJob:
    if updates.list_name is not None:
        saved.list_name = updates.list_name
    if updates.notes is not None:
        saved.notes = updates.notes
    if updates.starred is not None:
        saved.starred = updates.starred
    db.commit()
    db.refresh(saved)
    return saved


def delete_saved_job(db: Session, saved: SavedJob) -> None:
    db.delete(saved)
    db.commit()


# ------------------------------------------------------------------
# Browser-extension bookmarks
# ------------------------------------------------------------------

def get_raw_job_by_url(db: Session, url: str) -> RawJobPosting | None:
    return db.query(RawJobPosting).filter(RawJobPosting.url == url).first()


def create_raw_job_from_external(db: Session, data: ExternalJobBookmarkRequest) -> RawJobPosting:
    posting = RawJobPosting(
        source=data.source,
        job_id_external=data.url[:255],
        title=data.title,
        company=data.company,
        description=data.description,
        url=data.url,
        is_duplicate=False,
        raw_data={},
    )
    db.add(posting)
    db.commit()
    db.refresh(posting)
    return posting


def get_saved_job_by_raw_id(
    db: Session, user_id: uuid.UUID, raw_job_posting_id: uuid.UUID
) -> SavedJob | None:
    return (
        db.query(SavedJob)
        .filter(
            SavedJob.user_id == user_id,
            SavedJob.raw_job_posting_id == raw_job_posting_id,
        )
        .first()
    )


def update_saved_job_notes(db: Session, saved_job_id: uuid.UUID, notes: str) -> SavedJob | None:
    saved = db.query(SavedJob).filter(SavedJob.id == saved_job_id).first()
    if saved is None:
        return None
    saved.notes = notes
    db.commit()
    db.refresh(saved)
    return saved


def list_saved_job_urls(db: Session, user_id: uuid.UUID) -> list[str]:
    rows = (
        db.query(RawJobPosting.url)
        .join(SavedJob, SavedJob.raw_job_posting_id == RawJobPosting.id)
        .filter(SavedJob.user_id == user_id)
        .all()
    )
    return [r.url for r in rows]


def get_job_matching_score(
    db: Session, user_id: uuid.UUID, raw_job_posting_id: uuid.UUID
) -> JobMatchingScore | None:
    return (
        db.query(JobMatchingScore)
        .filter(
            JobMatchingScore.user_id == user_id,
            JobMatchingScore.raw_job_posting_id == raw_job_posting_id,
        )
        .first()
    )


def upsert_job_matching_score(
    db: Session,
    user_id: uuid.UUID,
    raw_job_posting_id: uuid.UUID,
    scores: dict,
) -> JobMatchingScore:
    existing = get_job_matching_score(db, user_id, raw_job_posting_id)
    if existing:
        existing.overall_score = scores["overall_score"]
        existing.skills_match = scores.get("skills_match")
        existing.experience_match = scores.get("experience_match")
        existing.salary_match = scores.get("salary_match")
        existing.education_match = scores.get("education_match")
        existing.location_match = scores.get("location_match")
        existing.explanation = scores.get("explanation")
        db.commit()
        db.refresh(existing)
        return existing

    record = JobMatchingScore(
        user_id=user_id,
        raw_job_posting_id=raw_job_posting_id,
        overall_score=scores["overall_score"],
        skills_match=scores.get("skills_match"),
        experience_match=scores.get("experience_match"),
        salary_match=scores.get("salary_match"),
        education_match=scores.get("education_match"),
        location_match=scores.get("location_match"),
        explanation=scores.get("explanation"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------

def _compute_skill_gap(
    db: Session,
    user_id: uuid.UUID,
    posting: RawJobPosting,
) -> tuple[list[str], list[str]]:
    """Partition the job's extracted keywords into matched/missing vs the user's CV.

    Reuses the persisted ``extracted_keywords`` for the job (no re-extraction) and
    compares them against the skills extracted from the user's default CV. Mirrors
    the skill comparison in ``matching_service.calculate_match_score``.
    """
    job_keywords = [kw.keyword for kw in posting.keywords]
    if not job_keywords:
        return [], []

    cv = (
        db.query(CV)
        .filter(CV.user_id == user_id, CV.is_default.is_(True))
        .first()
    )
    if not cv or not cv.content:
        return [], []

    extracted = KeywordExtractor().extract_keywords(cv.content)
    cv_skills: set[str] = {
        item["keyword"].lower()
        for items in extracted.values()
        for item in items
    }

    matched = [kw for kw in job_keywords if kw.lower() in cv_skills]
    missing = [kw for kw in job_keywords if kw.lower() not in cv_skills]
    return matched, missing


def _job_to_dict(
    posting: RawJobPosting,
    score: JobMatchingScore | None,
    application: Application | None = None,
    saved_job: SavedJob | None = None,
    include_description: bool = False,
    keywords: list[ExtractedKeyword] | None = None,
    matched_skills: list[str] | None = None,
    missing_skills: list[str] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "job_id": posting.id,
        "title": posting.title,
        "company": posting.company,
        "location": posting.location,
        "salary_min": posting.salary_min,
        "salary_max": posting.salary_max,
        "employment_type": posting.employment_type,
        "remote_allowed": posting.remote_allowed,
        "url": posting.url,
        "source": posting.source,
        "scraped_at": posting.scraped_at,
        "match_score": score.overall_score if score else None,
        "skills_match": score.skills_match if score else None,
        "experience_match": score.experience_match if score else None,
        "salary_match_score": score.salary_match if score else None,
        "education_match": score.education_match if score else None,
        "location_match": score.location_match if score else None,
        "explanation": score.explanation if score else None,
        "keywords": keywords or [],
        "is_saved": saved_job is not None,
        "saved_job_id": saved_job.id if saved_job else None,
        "application_status": application.status if application else None,
        "application_id": application.id if application else None,
    }
    if include_description:
        data["description"] = posting.description
        data["matched_skills"] = matched_skills or []
        data["missing_skills"] = missing_skills or []
    return data
