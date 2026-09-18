import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import application as crud_application
from app.crud import inbound_email as crud_inbound_email
from app.models.user import User
from app.schemas.application import (
    ApplicationContactCreate,
    ApplicationContactPublic,
    ApplicationCreate,
    ApplicationPublic,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
    DuplicateCheckResponse,
    EmailSuggestion,
    EmailSuggestionList,
)
from app.schemas.application_analytics import ApplicationAnalytics
from app.services import notification_service

router = APIRouter(prefix="/applications", tags=["applications"])


def _moved_to_interview(application) -> bool:
    for event in getattr(application, "events", []) or []:
        if (
            getattr(event, "event_type", None) == "status_changed"
            and getattr(event, "new_value", None) == "interview"
            and getattr(event, "old_value", None) != "interview"
        ):
            return True
    return False


@router.post("", response_model=ApplicationPublic, status_code=status.HTTP_201_CREATED)
def create_application(
    body: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationPublic:
    try:
        return crud_application.create_application(db, current_user.id, body)
    except crud_application.RawJobPostingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Raw job posting not found",
        ) from None
    except crud_application.MissingApplicationFieldsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    except crud_application.ForeignReferenceNotOwnedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None


@router.get("/applied-urls")
def get_applied_urls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return URLs of jobs where the user's application is beyond wishlist.

    Used by the extension background worker to show 'Applied ✓' badges.
    """
    urls = crud_application.list_applied_job_urls(db, current_user.id)
    return {"urls": urls}


@router.get("/check-duplicate", response_model=DuplicateCheckResponse)
def check_duplicate_application(
    company: str = Query(min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Report whether the user already has an open application for this company.

    Open means any status except rejected/withdrawn. Used by the add-application
    form to warn before creating a likely duplicate; creation is never blocked.
    """
    existing = crud_application.find_open_duplicate(db, current_user.id, company)
    return {"duplicate": existing is not None, "application": existing}


@router.get("", response_model=list[ApplicationSummary])
def list_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    skip: int = 0,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApplicationSummary]:
    return crud_application.get_applications(db, current_user.id, status_filter, skip, limit)


@router.get("/stats", response_model=dict[str, int])
def get_application_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return crud_application.get_stats(db, current_user.id)


@router.get("/analytics", response_model=ApplicationAnalytics)
def get_application_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationAnalytics:
    return crud_application.get_analytics(db, current_user.id)


def _suggestion_payload(row, company_name: str, job_title: str, current_status: str) -> dict:
    return {
        "id": row.id,
        "application_id": row.matched_application_id,
        "company_name": company_name,
        "job_title": job_title,
        "current_status": current_status,
        "suggested_status": row.suggested_status,
        "classification": row.classification,
        "confidence": row.classification_confidence,
        "evidence": row.evidence,
        "from_address": row.from_address,
        "subject": row.subject,
        "received_at": row.received_at,
    }


@router.get("/email-suggestions", response_model=EmailSuggestionList)
def list_email_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailSuggestionList:
    """Status changes proposed by forwarded email, awaiting the user's decision.

    Nothing here has been applied. Suggestions whose application has since been
    moved to the proposed status by hand are skipped rather than shown as
    no-ops.
    """
    rows = crud_inbound_email.list_pending_suggestions(db, current_user.id)
    items = []
    for row, company_name, job_title in rows:
        application = crud_application.get_application(
            db, row.matched_application_id, current_user.id
        )
        if application is None or application.status == row.suggested_status:
            continue
        items.append(
            EmailSuggestion.model_validate(
                _suggestion_payload(row, company_name, job_title, application.status)
            )
        )
    return EmailSuggestionList(items=items)


@router.post("/email-suggestions/{suggestion_id}/accept", response_model=ApplicationSummary)
def accept_email_suggestion(
    suggestion_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationSummary:
    """Apply a suggested status change.

    Goes through the normal update path so the timeline records it exactly
    like a manual change — an automated edit the user cannot see afterwards
    would be worse than no automation.
    """
    row = crud_inbound_email.get_pending_suggestion(db, suggestion_id, current_user.id)
    if row is None or not row.suggested_status or not row.matched_application_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")

    application = crud_application.update_application(
        db,
        row.matched_application_id,
        current_user.id,
        ApplicationUpdate(status=row.suggested_status),
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    crud_inbound_email.set_suggestion_state(db, row, "accepted")
    return ApplicationSummary.model_validate(application)


@router.post(
    "/email-suggestions/{suggestion_id}/dismiss", status_code=status.HTTP_204_NO_CONTENT
)
def dismiss_email_suggestion(
    suggestion_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    row = crud_inbound_email.get_pending_suggestion(db, suggestion_id, current_user.id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found")
    crud_inbound_email.set_suggestion_state(db, row, "dismissed")


# Declared before /{application_id}: FastAPI matches in order, and a literal
# path segment must win over the UUID path parameter.
@router.get("/{application_id}", response_model=ApplicationPublic)
def get_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationPublic:
    application = crud_application.get_application(db, application_id, current_user.id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.patch("/{application_id}", response_model=ApplicationPublic)
def update_application(
    application_id: uuid.UUID,
    body: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationPublic:
    try:
        application = crud_application.update_application(db, application_id, current_user.id, body)
    except crud_application.ForeignReferenceNotOwnedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if body.status == "interview" and _moved_to_interview(application):
        try:
            notification_service.create_notification(
                db,
                user_id=current_user.id,
                type="interview_reminder",
                title="Interview stage reached",
                body=f"{application.company_name} moved to interview.",
                related_id=application.id,
                related_type="application",
                send_email=True,
                email=getattr(current_user, "email", None),
            )
        except Exception:
            pass
    return application


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = crud_application.delete_application(db, application_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")


@router.post(
    "/{application_id}/contacts",
    response_model=ApplicationContactPublic,
    status_code=status.HTTP_201_CREATED,
)
def add_contact(
    application_id: uuid.UUID,
    body: ApplicationContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationContactPublic:
    contact = crud_application.add_contact(db, application_id, current_user.id, body)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return contact


@router.delete("/{application_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    application_id: uuid.UUID,
    contact_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deleted = crud_application.delete_contact(db, contact_id, application_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
