"""
Celery task: run AI cover letter generation and store result.
"""
import uuid
from typing import Any

from celery import Task

from app.crud import cover_letter_job as crud_cl
from app.db.session import SessionLocal
from app.models.cover_letter_job import CoverLetterJob, CoverLetterStatus
from app.models.cv import CV
from app.models.job_description import JobDescription
from app.services import notification_service
from app.services.cover_letter_service import generate_cover_letter
from app.tasks.celery_app import celery_app


def _load_job(db, job_id: str) -> CoverLetterJob | None:
    return db.query(CoverLetterJob).filter(CoverLetterJob.id == uuid.UUID(str(job_id))).first()


class CoverLetterTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        job_id = args[0] if args else kwargs.get("job_id")
        if not job_id:
            return
        db = SessionLocal()
        try:
            job = _load_job(db, str(job_id))
            if job and job.status != CoverLetterStatus.complete:
                crud_cl.set_failed(db, job, str(exc))
        finally:
            db.close()


@celery_app.task(
    bind=True,
    base=CoverLetterTask,
    name="app.tasks.cover_letter.run_cover_letter",
    max_retries=2,
    default_retry_delay=10,
)
def run_cover_letter(self, job_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        job = _load_job(db, job_id)
        if not job:
            return {"error": "job not found"}

        if job.status in {CoverLetterStatus.complete, CoverLetterStatus.failed}:
            return {"error": f"job already {job.status.value}"}

        crud_cl.set_processing(db, job)

        cv = db.query(CV).filter(CV.id == job.cv_id).first()
        jd = db.query(JobDescription).filter(JobDescription.id == job.job_description_id).first()
        # Deterministic precondition failures: retrying cannot fix a missing CV
        # or job description, so mark the job failed immediately instead of
        # burning retries.
        if not cv or not cv.content:
            crud_cl.set_failed(db, job, "CV has no text content")
            return {"error": "CV has no text content"}
        if not jd:
            crud_cl.set_failed(db, job, "Job description not found")
            return {"error": "Job description not found"}

        result = generate_cover_letter(
            cv_content=cv.content,
            jd_description=jd.description,
            jd_company=jd.company_name,
            jd_title=jd.job_title,
            tone=job.tone,
            user_id=job.user_id,
        )

        crud_cl.set_complete(
            db,
            job,
            generated_text=result["cover_letter_text"],
            language=result.get("language", "en"),
            word_count=result.get("word_count", 0),
        )

        notification_service.create_notification(
            db,
            user_id=job.user_id,
            type="cover_letter_complete",
            title="Your cover letter is ready",
            body=f"Your AI-generated cover letter for {jd.job_title} at {jd.company_name} is ready to review.",
            related_id=job.id,
            related_type="cover_letter_job",
            send_email=False,
        )

        return {"status": "complete", "job_id": job_id}

    except Exception as exc:
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            job = _load_job(db, job_id)
            if job:
                crud_cl.set_failed(db, job, str(exc))
            raise
    finally:
        db.close()
