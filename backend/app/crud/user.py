import logging
import secrets
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

_RESET_TOKEN_TTL_HOURS = 1

logger = logging.getLogger(__name__)


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_by_verification_token(db: Session, token: str) -> User | None:
    return db.query(User).filter(User.verification_token == token).first()


def get_by_google_id(db: Session, google_id: str) -> User | None:
    return db.query(User).filter(User.google_id == google_id).first()


def upsert_google_user(
    db: Session,
    *,
    google_id: str,
    email: str,
    full_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Resolve a Google-authenticated user, creating or linking as needed.

    - If a user with this google_id exists, update the avatar and return it.
    - Else if a user with this email exists, link the Google account to it.
    - Else create a new passwordless, pre-verified Google user.
    """
    user = get_by_google_id(db, google_id)
    if user:
        user.avatar_url = avatar_url
        if full_name and not user.full_name:
            user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user

    user = get_by_email(db, email)
    if user:
        user.google_id = google_id
        user.auth_provider = "google"
        user.avatar_url = avatar_url
        user.is_verified = True
        if full_name and not user.full_name:
            user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        google_id=google_id,
        full_name=full_name,
        avatar_url=avatar_url,
        auth_provider="google",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_by_id(db: Session, user_id: str) -> User | None:
    import uuid as _uuid
    try:
        return db.get(User, _uuid.UUID(user_id))
    except ValueError:
        return None


def create(db: Session, user_in: UserCreate) -> User:
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        verification_token=secrets.token_urlsafe(32),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_email(db: Session, token: str) -> User | None:
    user = get_by_verification_token(db, token)
    if not user:
        return None
    user.is_verified = True
    user.verification_token = None
    db.commit()
    db.refresh(user)
    return user


def refresh_verification_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    db.commit()
    return token


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = get_by_email(db, email)
    # OAuth-only users have no password and cannot authenticate via this path.
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return None
    return user


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name
    db.commit()
    db.refresh(user)
    return user


def update_password(db: Session, user: User, new_password: str) -> User:
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    db.refresh(user)
    return user


def delete(db: Session, user: User) -> None:
    user_id = str(user.id)
    db.delete(user)
    db.commit()
    _remove_user_files(user_id)


def _remove_user_files(user_id: str) -> None:
    """Erase the user's files on disk (GDPR right to erasure).

    Runs after the DB commit — a disk failure must never abort account deletion,
    so errors are logged and swallowed.
    """
    try:
        storage_root = Path(settings.STORAGE_DIR).resolve()
        for subdir in ("cvs", "cover_letters"):
            shutil.rmtree(storage_root / subdir / user_id, ignore_errors=True)
    except Exception:
        logger.warning(
            "Failed to remove files for deleted user",
            extra={"user_id": user_id},
            exc_info=True,
        )


def get_by_password_reset_token(db: Session, token: str) -> User | None:
    return db.query(User).filter(User.password_reset_token == token).first()


def create_password_reset_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires_at = datetime.now(UTC) + timedelta(hours=_RESET_TOKEN_TTL_HOURS)
    db.commit()
    return token


def consume_password_reset_token(db: Session, token: str, new_password: str) -> User | None:
    user = get_by_password_reset_token(db, token)
    if not user:
        return None
    if user.password_reset_expires_at is None:
        return None
    expires = user.password_reset_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return None
    user.hashed_password = get_password_hash(new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.commit()
    db.refresh(user)
    return user
