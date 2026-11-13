import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.fit_assessment import (
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PROCESSING,
    FitAssessment,
)


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    cv_id: uuid.UUID,
    raw_job_posting_id: uuid.UUID,
    job_title: str,
    company: str,
    model: str,
    prompt_version: str,
    rules_version: str,
    input_hash: str,
) -> FitAssessment:
    row = FitAssessment(
        user_id=user_id,
        cv_id=cv_id,
        raw_job_posting_id=raw_job_posting_id,
        job_title=job_title[:255],
        company=company[:255],
        model=model,
        prompt_version=prompt_version,
        rules_version=rules_version,
        input_hash=input_hash,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_by_id(db: Session, assessment_id: uuid.UUID, user_id: uuid.UUID) -> FitAssessment | None:
    return (
        db.query(FitAssessment)
        .filter(FitAssessment.id == assessment_id, FitAssessment.user_id == user_id)
        .first()
    )


def get_latest_for_posting(
    db: Session, user_id: uuid.UUID, raw_job_posting_id: uuid.UUID
) -> FitAssessment | None:
    """The newest assessment of this job that did not fail."""
    return (
        db.query(FitAssessment)
        .filter(
            FitAssessment.user_id == user_id,
            FitAssessment.raw_job_posting_id == raw_job_posting_id,
            FitAssessment.status != STATUS_FAILED,
        )
        .order_by(FitAssessment.created_at.desc())
        .first()
    )


def get_reusable(db: Session, user_id: uuid.UUID, input_hash: str) -> FitAssessment | None:
    """A finished or running assessment of exactly the same CV, ad and versions."""
    return (
        db.query(FitAssessment)
        .filter(
            FitAssessment.user_id == user_id,
            FitAssessment.input_hash == input_hash,
            FitAssessment.status.in_([STATUS_PENDING, STATUS_PROCESSING, STATUS_COMPLETE]),
        )
        .order_by(FitAssessment.created_at.desc())
        .first()
    )


def count_today(db: Session, user_id: uuid.UUID) -> int:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(FitAssessment.id))
        .filter(
            FitAssessment.user_id == user_id,
            FitAssessment.created_at >= today_start,
            FitAssessment.status != STATUS_FAILED,
        )
        .scalar()
        or 0
    )


def set_task_id(db: Session, row: FitAssessment, celery_task_id: str) -> FitAssessment:
    row.celery_task_id = celery_task_id
    db.commit()
    db.refresh(row)
    return row


def set_processing(db: Session, row: FitAssessment) -> FitAssessment:
    row.status = STATUS_PROCESSING
    db.commit()
    db.refresh(row)
    return row


def set_complete(db: Session, row: FitAssessment, result: dict[str, Any]) -> FitAssessment:
    row.status = STATUS_COMPLETE
    row.recommendation = result["recommendation"]
    row.model_recommendation = result.get("model_recommendation")
    row.limited_information = bool(result["limited_information"])
    row.result_json = result
    row.error_message = None
    db.commit()
    db.refresh(row)
    return row


def set_failed(db: Session, row: FitAssessment, error: str) -> FitAssessment:
    row.status = STATUS_FAILED
    row.error_message = error[:2000]
    db.commit()
    db.refresh(row)
    return row
