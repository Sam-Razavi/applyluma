import hashlib
import hmac
from collections.abc import Generator

import redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal

# auto_error=False so we can fall back to the httpOnly cookie when no
# Authorization header is present (cookie-based browser clients).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_id(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Prefer the Authorization header; fall back to the httpOnly access_token cookie.
    token = bearer_token or request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    # CSRF guard for cookie-authenticated requests on state-changing methods.
    # Bearer-header clients (API, mobile) are exempt — they can't be CSRF-attacked.
    if not bearer_token and request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
        csrf_cookie = request.cookies.get("csrf_token", "")
        csrf_header = request.headers.get("x-csrf-token", "")
        if not csrf_cookie or not hmac.compare_digest(csrf_cookie, csrf_header):
            raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Reject refresh tokens being used as access tokens
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None

    # Check token denylist (fail open: Redis outage must not lock users out)
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        r = get_redis_client()
        if r.exists(f"token_denylist:{token_hash}"):
            raise credentials_exception
    except HTTPException:
        raise
    except Exception:
        pass

    return user_id


def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_current_user_unverified(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Return the current user without checking email verification.

    Use only for endpoints that must remain accessible to unverified users:
    GET/PATCH/DELETE /auth/me, POST /auth/resend-verification, POST /auth/change-password.
    """
    from app.crud.user import get_by_id  # local import avoids circular at module load

    user = get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    from app.crud.user import get_by_id  # local import avoids circular at module load

    user = get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "EMAIL_NOT_VERIFIED", "message": "Please verify your email address."},
        )
    return user
