import uuid
from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.tailor_job import TailorIntensity, TailorJob, TailorStatus


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    cv_id: uuid.UUID,
    job_description_id: uuid.UUID,
    intensity: TailorIntensity,
) -> TailorJob:
    job = TailorJob(
        user_id=user_id,
        cv_id=cv_id,
        job_description_id=job_description_id,
        intensity=intensity,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_by_id(db: Session, job_id: uuid.UUID, user_id: uuid.UUID) -> TailorJob | None:
    return (
        db.query(TailorJob)
        .options(joinedload(TailorJob.job_description))
        .filter(TailorJob.id == job_id, TailorJob.user_id == user_id)
        .first()
    )


def list_for_user(db: Session, user_id: uuid.UUID, limit: int = 20) -> list[TailorJob]:
    return (
        db.query(TailorJob)
        .filter(TailorJob.user_id == user_id)
        .order_by(TailorJob.created_at.desc())
        .limit(limit)
        .all()
    )


def count_today(db: Session, user_id: uuid.UUID) -> int:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(TailorJob.id))
        .filter(
            TailorJob.user_id == user_id,
            TailorJob.created_at >= today_start,
            TailorJob.status != TailorStatus.failed,
        )
        .scalar()
        or 0
    )


def set_processing(db: Session, job: TailorJob, celery_task_id: str | None = None) -> TailorJob:
    job.status = TailorStatus.processing
    if celery_task_id:
        job.celery_task_id = celery_task_id
    db.commit()
    db.refresh(job)
    return job


def set_task_id(db: Session, job: TailorJob, celery_task_id: str) -> TailorJob:
    job.celery_task_id = celery_task_id
    db.commit()
    db.refresh(job)
    return job


def set_complete(
    db: Session,
    job: TailorJob,
    *,
    result_json: dict,
    language: str,
) -> TailorJob:
    job.status = TailorStatus.complete
    job.result_json = result_json
    job.language = language
    job.error_message = None
    db.commit()
    db.refresh(job)
    return job


def set_failed(db: Session, job: TailorJob, error: str) -> TailorJob:
    job.status = TailorStatus.failed
    job.error_message = error
    db.commit()
    db.refresh(job)
    return job


def set_output_cv(db: Session, job: TailorJob, output_cv_id: uuid.UUID) -> TailorJob:
    job.output_cv_id = output_cv_id
    db.commit()
    db.refresh(job)
    return job
