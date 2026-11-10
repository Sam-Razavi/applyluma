import logging
import secrets
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

_RESET_TOKEN_TTL_HOURS = 1

logger = logging.getLogger(__name__)


def get_by_email(db: Session, email: str) -> User | None:
    # Case-insensitive: phone keyboards capitalise the first letter of an
    # email field, and "Sam@gmail.com" is the same mailbox as "sam@gmail.com".
    return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


_OAUTH_PROVIDERS = (("google_id", "Google"), ("linkedin_id", "LinkedIn"), ("github_id", "GitHub"))


def oauth_provider_names(user: User) -> list[str]:
    """The sign-in providers linked to *user*, e.g. ["Google"]."""
    return [name for attr, name in _OAUTH_PROVIDERS if getattr(user, attr, None)]


def oauth_only_hint(user: User | None) -> str | None:
    """Why a password login cannot work for an account created through OAuth.

    Such accounts have no password, so the plain "Incorrect email or password"
    sends people round in circles. Registration already answers 409 for a
    known email, so naming the provider reveals nothing new.
    """
    if user is None or user.hashed_password:
        return None
    providers = oauth_provider_names(user)
    if not providers:
        return None
    via = " or ".join(providers)
    return (
        f"This account was created with {via} and has no password. "
        f"Use the {providers[0]} button below to sign in, or choose "
        "\"Forgot password?\" to add a password."
    )


def get_by_verification_token(db: Session, token: str) -> User | None:
    return db.query(User).filter(User.verification_token == token).first()


def get_by_google_id(db: Session, google_id: str) -> User | None:
    return db.query(User).filter(User.google_id == google_id).first()


def get_by_linkedin_id(db: Session, linkedin_id: str) -> User | None:
    return db.query(User).filter(User.linkedin_id == linkedin_id).first()


def get_by_github_id(db: Session, github_id: str) -> User | None:
    return db.query(User).filter(User.github_id == github_id).first()


def upsert_oauth_user(
    db: Session,
    *,
    provider: str,
    id_attr: str,
    provider_user_id: str,
    email: str,
    full_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Resolve an OAuth-authenticated user, creating or linking as needed.

    - If a user with this provider id exists, update the avatar and return it.
    - Else if a user with this email exists, link the provider account to it.
    - Else create a new passwordless, pre-verified user.

    `id_attr` is the User column holding the provider's user id
    (google_id / linkedin_id / github_id).
    """
    # Built per call so the module-level getters resolve dynamically
    # (tests monkeypatch them on this module).
    getters = {
        "google_id": get_by_google_id,
        "linkedin_id": get_by_linkedin_id,
        "github_id": get_by_github_id,
    }
    user = getters[id_attr](db, provider_user_id)
    if user:
        user.avatar_url = avatar_url
        if full_name and not user.full_name:
            user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user

    user = get_by_email(db, email)
    if user:
        setattr(user, id_attr, provider_user_id)
        user.auth_provider = provider
        user.avatar_url = avatar_url
        user.is_verified = True
        if full_name and not user.full_name:
            user.full_name = full_name
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
        auth_provider=provider,
        is_active=True,
        is_verified=True,
        inbox_token=new_inbox_token(),
        **{id_attr: provider_user_id},
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def upsert_google_user(
    db: Session,
    *,
    google_id: str,
    email: str,
    full_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    return upsert_oauth_user(
        db,
        provider="google",
        id_attr="google_id",
        provider_user_id=google_id,
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
    )


def get_by_id(db: Session, user_id: str) -> User | None:
    import uuid as _uuid
    try:
        return db.get(User, _uuid.UUID(user_id))
    except ValueError:
        return None


def new_inbox_token() -> str:
    """Mint the secret half of a user's inbound-email address.

    Hex rather than ``token_urlsafe`` because this ends up in an email
    local-part: hex survives the MTAs and vendors that normalise case, where a
    mixed-case token with ``-``/``_`` can silently fail to resolve.
    """
    return secrets.token_hex(16)


def get_by_inbox_token(db: Session, token: str) -> User | None:
    """Resolve an inbound-address token to its owner.

    Guards the empty string explicitly so a malformed recipient can never match
    the accounts that predate the column.
    """
    cleaned = (token or "").strip().lower()
    if not cleaned:
        return None
    return db.query(User).filter(User.inbox_token == cleaned).first()


def rotate_inbox_token(db: Session, user: User) -> str:
    """Give *user* a new forwarding address; the old one stops working."""
    user.inbox_token = new_inbox_token()
    db.commit()
    db.refresh(user)
    return user.inbox_token


def ensure_inbox_token(db: Session, user: User) -> str:
    """Return the user's inbound token, minting one if they predate the column."""
    if user.inbox_token:
        return user.inbox_token
    user.inbox_token = new_inbox_token()
    db.commit()
    db.refresh(user)
    return user.inbox_token


def create(db: Session, user_in: UserCreate) -> User:
    user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        verification_token=secrets.token_urlsafe(32),
        inbox_token=new_inbox_token(),
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


def record_login(db: Session, user: User) -> None:
    user.last_login_at = datetime.now(UTC)
    user.login_count = (user.login_count or 0) + 1
    db.commit()


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name
    # None means "unchanged" (the Settings dropdown always sends a value),
    # matching the full_name semantics above.
    if data.preferred_template is not None:
        user.preferred_template = data.preferred_template
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
