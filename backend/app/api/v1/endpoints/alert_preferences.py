from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.crud import alert_preferences as crud_alert_preferences
from app.models.user import User
from app.schemas.alert_preferences import AlertPreferencesPublic, AlertPreferencesUpdate

router = APIRouter(prefix="/me/alert-preferences", tags=["alert-preferences"])


@router.get("", response_model=AlertPreferencesPublic)
def get_alert_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertPreferencesPublic:
    return crud_alert_preferences.get_or_create_for_user(db, current_user.id)


@router.patch("", response_model=AlertPreferencesPublic)
def update_alert_preferences(
    body: AlertPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertPreferencesPublic:
    preferences = crud_alert_preferences.get_or_create_for_user(db, current_user.id)
    return crud_alert_preferences.update(db, preferences, body)
