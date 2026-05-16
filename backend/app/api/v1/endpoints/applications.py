import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import application as crud_application
from app.models.user import User
from app.schemas.application import (
    ApplicationContactCreate,
    ApplicationContactPublic,
    ApplicationCreate,
    ApplicationPublic,
    ApplicationStatus,
    ApplicationSummary,
    ApplicationUpdate,
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
    application = crud_application.update_application(db, application_id, current_user.id, body)
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
