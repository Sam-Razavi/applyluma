"""Celery task: run one AI-assisted job-fit assessment and store the result."""
import uuid
from typing import Any

from app.crud import fit_assessment as crud_fit
from app.db.session import SessionLocal
from app.models.cv import CV
from app.models.fit_assessment import STATUS_COMPLETE, STATUS_FAILED, FitAssessment
from app.models.job import RawJobPosting
from app.services import fit_advisor
from app.tasks.celery_app import celery_app


def ad_text_for(posting: RawJobPosting) -> str:
    """The ad as the model and the input hash see it."""
    header = "\n".join(part for part in (posting.title, posting.company, posting.location) if part)
    return f"{header}\n\n{posting.description or ''}".strip()


@celery_app.task(name="app.tasks.fit_assessment.run_fit_assessment")
def run_fit_assessment(assessment_id: str) -> dict[str, Any]:
    db = SessionLocal()
    try:
        row = db.query(FitAssessment).filter(FitAssessment.id == uuid.UUID(assessment_id)).first()
        if not row:
            return {"error": "assessment not found"}
        if row.status in {STATUS_COMPLETE, STATUS_FAILED}:
            return {"error": f"assessment already {row.status}"}

        crud_fit.set_processing(db, row)

        cv = db.query(CV).filter(CV.id == row.cv_id).first() if row.cv_id else None
        posting = (
            db.query(RawJobPosting).filter(RawJobPosting.id == row.raw_job_posting_id).first()
            if row.raw_job_posting_id
            else None
        )
        if not cv or not cv.content:
            crud_fit.set_failed(db, row, "The CV has no text content")
            return {"error": "cv missing"}
        if not posting or not posting.description:
            crud_fit.set_failed(db, row, "The job ad is no longer available")
            return {"error": "posting missing"}

        try:
            # No automatic retry: a retry would be a second, different run of
            # the model stored as if it were the first.
            result = fit_advisor.assess(cv.content, ad_text_for(posting), user_id=row.user_id)
        except fit_advisor.FitAdvisorError as exc:
            crud_fit.set_failed(db, row, str(exc))
            return {"error": str(exc)}
        except Exception as exc:
            crud_fit.set_failed(db, row, f"Unexpected error: {exc}")
            raise

        crud_fit.set_complete(db, row, result)
        return {"status": "complete", "assessment_id": assessment_id}
    finally:
        db.close()
