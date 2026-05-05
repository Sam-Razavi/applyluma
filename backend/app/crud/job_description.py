import uuid

from sqlalchemy.orm import Session

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


def delete(db: Session, jd: JobDescription) -> None:
    db.delete(jd)
    db.commit()
