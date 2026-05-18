"""CRUD operations for Phase 10A job discovery."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, nullslast
from sqlalchemy.orm import Session, joinedload

from app.models.application import Application
from app.models.job import ExtractedKeyword, JobMatchingScore, RawJobPosting, SavedJob
from app.schemas.job import SaveJobRequest, UpdateSavedJobRequest

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
    page: int = 1,
    limit: int = 20,
    sort: str = "score_desc",
) -> list[dict[str, Any]]:
    """Return a paginated list of jobs with match scores for the user."""
    q = (
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
        results.append(_job_to_dict(posting, score, application, saved_job))
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
    return _job_to_dict(posting, score, application, saved_job, include_description=True)


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
# Private helpers
# ------------------------------------------------------------------

def _job_to_dict(
    posting: RawJobPosting,
    score: JobMatchingScore | None,
    application: Application | None = None,
    saved_job: SavedJob | None = None,
    include_description: bool = False,
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
        "keywords": [],
        "is_saved": saved_job is not None,
        "saved_job_id": saved_job.id if saved_job else None,
        "application_status": application.status if application else None,
        "application_id": application.id if application else None,
    }
    if include_description:
        data["description"] = posting.description
        data["matched_skills"] = []
        data["missing_skills"] = []
    return data
