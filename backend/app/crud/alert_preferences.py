import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alert_preferences import UserAlertPreferences
from app.schemas.alert_preferences import AlertPreferencesUpdate


def get_or_create_for_user(db: Session, user_id: uuid.UUID) -> UserAlertPreferences:
    preferences = (
        db.query(UserAlertPreferences).filter(UserAlertPreferences.user_id == user_id).first()
    )
    if preferences:
        return preferences

    preferences = UserAlertPreferences(user_id=user_id)
    db.add(preferences)
    db.commit()
    db.refresh(preferences)
    return preferences


def update(
    db: Session,
    preferences: UserAlertPreferences,
    body: AlertPreferencesUpdate,
) -> UserAlertPreferences:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(preferences, field, value)
    db.commit()
    db.refresh(preferences)
    return preferences


def due_for_alert(
    db: Session,
    *,
    frequency: str | None = None,
    now: datetime | None = None,
) -> list[UserAlertPreferences]:
    now = now or datetime.now(UTC)
    query = db.query(UserAlertPreferences).filter(UserAlertPreferences.enabled.is_(True))
    if frequency:
        query = query.filter(UserAlertPreferences.frequency == frequency)

    preferences = query.all()
    return [pref for pref in preferences if _is_due(pref, now)]


def _is_due(preferences: UserAlertPreferences, now: datetime) -> bool:
    if preferences.last_sent_at is None:
        return True
    interval = timedelta(days=7 if preferences.frequency == "weekly" else 1)
    return preferences.last_sent_at < now - interval
