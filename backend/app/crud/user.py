import secrets

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_by_verification_token(db: Session, token: str) -> User | None:
    return db.query(User).filter(User.verification_token == token).first()


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
    if not user or not verify_password(password, user.hashed_password):
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
    db.delete(user)
    db.commit()
