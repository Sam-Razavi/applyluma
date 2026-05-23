import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.cover_letter_job import CoverLetterJob, CoverLetterStatus, CoverLetterTone


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    cv_id: uuid.UUID,
    job_description_id: uuid.UUID,
    tone: CoverLetterTone,
) -> CoverLetterJob:
    job = CoverLetterJob(
        user_id=user_id,
        cv_id=cv_id,
        job_description_id=job_description_id,
        tone=tone,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_by_id(db: Session, job_id: uuid.UUID, user_id: uuid.UUID) -> CoverLetterJob | None:
    return (
        db.query(CoverLetterJob)
        .options(joinedload(CoverLetterJob.job_description))
        .filter(CoverLetterJob.id == job_id, CoverLetterJob.user_id == user_id)
        .first()
    )


def list_for_user(db: Session, user_id: uuid.UUID, limit: int = 20) -> list[CoverLetterJob]:
    return (
        db.query(CoverLetterJob)
        .filter(CoverLetterJob.user_id == user_id)
        .order_by(CoverLetterJob.created_at.desc())
        .limit(limit)
        .all()
    )


def count_today(db: Session, user_id: uuid.UUID) -> int:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(CoverLetterJob.id))
        .filter(
            CoverLetterJob.user_id == user_id,
            CoverLetterJob.created_at >= today_start,
            CoverLetterJob.status != CoverLetterStatus.failed,
        )
        .scalar()
        or 0
    )


def set_processing(db: Session, job: CoverLetterJob, celery_task_id: str | None = None) -> CoverLetterJob:
    job.status = CoverLetterStatus.processing
    if celery_task_id:
        job.celery_task_id = celery_task_id
    db.commit()
    db.refresh(job)
    return job


def set_task_id(db: Session, job: CoverLetterJob, celery_task_id: str) -> CoverLetterJob:
    job.celery_task_id = celery_task_id
    db.commit()
    db.refresh(job)
    return job


def set_complete(
    db: Session,
    job: CoverLetterJob,
    *,
    generated_text: str,
    language: str,
    word_count: int,
) -> CoverLetterJob:
    job.status = CoverLetterStatus.complete
    job.generated_text = generated_text
    job.language = language
    job.word_count = word_count
    job.error_message = None
    db.commit()
    db.refresh(job)
    return job


def set_failed(db: Session, job: CoverLetterJob, error: str) -> CoverLetterJob:
    job.status = CoverLetterStatus.failed
    job.error_message = error
    db.commit()
    db.refresh(job)
    return job


def save(db: Session, job: CoverLetterJob, *, saved_text: str, title: str | None) -> CoverLetterJob:
    job.saved_text = saved_text
    job.is_saved = True
    if title:
        job.title = title
    db.commit()
    db.refresh(job)
    return job


def delete(db: Session, job: CoverLetterJob) -> None:
    db.delete(job)
    db.commit()
