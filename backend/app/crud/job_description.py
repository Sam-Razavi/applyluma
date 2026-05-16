import uuid

from sqlalchemy.orm import Session

from app.models.job import ExtractedKeyword, RawJobPosting
from app.models.job_description import JobDescription
from app.schemas.job_description import JobDescriptionCreate


def get_by_id(db: Session, jd_id: uuid.UUID, user_id: uuid.UUID) -> JobDescription | None:
    return (
        db.query(JobDescription)
        .filter(JobDescription.id == jd_id, JobDescription.user_id == user_id)
        .first()
    )


def list_for_user(db: Session, user_id: uuid.UUID) -> list[JobDescription]:
    return (
        db.query(JobDescription)
        .filter(JobDescription.user_id == user_id)
        .order_by(JobDescription.created_at.desc())
        .all()
    )


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    body: JobDescriptionCreate,
    keywords: list[str],
) -> JobDescription:
    jd = JobDescription(
        user_id=user_id,
        company_name=body.company_name,
        job_title=body.job_title,
        description=body.description,
        url=body.url,
        keywords=keywords,
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return jd


def get_or_create_from_raw_job(
    db: Session,
    *,
    user_id: uuid.UUID,
    raw_job_posting_id: uuid.UUID,
) -> JobDescription | None:
    existing = (
        db.query(JobDescription)
        .filter(
            JobDescription.user_id == user_id,
            JobDescription.source_raw_job_posting_id == raw_job_posting_id,
        )
        .first()
    )
    if existing:
        return existing

    raw_job = db.query(RawJobPosting).filter(RawJobPosting.id == raw_job_posting_id).first()
    if not raw_job:
        return None

    keywords = _keywords_from_raw_job(db, raw_job)
    jd = JobDescription(
        user_id=user_id,
        source_raw_job_posting_id=raw_job.id,
        company_name=raw_job.company,
        job_title=raw_job.title,
        description=raw_job.description,
        url=raw_job.url,
        keywords=keywords,
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)
    return jd


def _keywords_from_raw_job(db: Session, raw_job: RawJobPosting) -> list[str]:
    rows = (
        db.query(ExtractedKeyword.keyword)
        .filter(ExtractedKeyword.raw_job_posting_id == raw_job.id)
        .order_by(ExtractedKeyword.confidence_score.desc())
        .all()
    )
    keywords = [row[0] if isinstance(row, tuple) else row.keyword for row in rows]
    if keywords:
        return list(dict.fromkeys(keywords))

    extracted = raw_job.extracted_skills or {}
    flattened: list[str] = []
    for value in extracted.values():
        if isinstance(value, list):
            flattened.extend(str(item) for item in value if item)
        elif value:
            flattened.append(str(value))
    return list(dict.fromkeys(flattened))


def delete(db: Session, jd: JobDescription) -> None:
    db.delete(jd)
    db.commit()
