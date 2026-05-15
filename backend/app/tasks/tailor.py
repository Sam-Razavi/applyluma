"""
Celery task: run AI tailoring and store result in tailor_jobs.
"""
import uuid
from typing import Any

from celery import Task

from app.crud import tailor_job as crud_tailor
from app.db.session import SessionLocal
from app.models.cv import CV
from app.models.job_description import JobDescription
from app.models.tailor_job import TailorJob, TailorStatus
from app.services import notification_service
from app.services.tailor_service import tailor_cv
from app.tasks.celery_app import celery_app


def _load_job(db, job_id: str) -> TailorJob | None:
    return db.query(TailorJob).filter(TailorJob.id == uuid.UUID(str(job_id))).first()


class TailorTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        job_id = args[0] if args else kwargs.get("job_id")
        if not job_id:
            return
        db = SessionLocal()
        try:
            job = _load_job(db, str(job_id))
            if job and job.status != TailorStatus.complete:
                crud_tailor.set_failed(db, job, str(exc))
        finally:
            db.close()


@celery_app.task(
    bind=True,
    base=TailorTask,
    name="app.tasks.tailor.run_tailoring",
    max_retries=2,
    default_retry_delay=10,
)
def run_tailoring(self, job_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        job = _load_job(db, job_id)
        if not job:
            return {"error": "job not found"}

        if job.status in {TailorStatus.complete, TailorStatus.failed}:
            return {"error": f"job already {job.status.value}"}

        crud_tailor.set_processing(db, job)

        cv = db.query(CV).filter(CV.id == job.cv_id).first()
        jd = db.query(JobDescription).filter(JobDescription.id == job.job_description_id).first()
        if not cv or not cv.content:
            raise ValueError("CV has no text content")
        if not jd:
            raise ValueError("Job description not found")

        result = tailor_cv(
            cv_content=cv.content,
            jd_description=jd.description,
            jd_keywords=jd.keywords or [],
            intensity=job.intensity,
        )

        crud_tailor.set_complete(
            db,
            job,
            result_json=result,
            language=result.get("language", "en"),
        )
        notification_service.create_notification(
            db,
            user_id=job.user_id,
            type="tailor_complete",
            title="Your tailored CV is ready",
            body="Your AI-tailored CV has finished processing.",
            related_id=job.id,
            related_type="tailor_job",
            send_email=True,
            email=getattr(getattr(job, "user", None), "email", None),
        )

        return {"status": "complete", "job_id": job_id}

    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            job = _load_job(db, job_id)
            if job:
                crud_tailor.set_failed(db, job, str(exc))
            raise
    finally:
        db.close()
