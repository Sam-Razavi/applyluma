import hashlib
import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import (
    get_current_user_id,
    get_current_user_unverified,
    get_db,
    get_redis_client,
)
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.crud import user as crud_user
from app.models.user import User
from app.schemas.token import LoginRequest, LogoutRequest, RefreshRequest, Token, TokenPair
from app.schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserCreate,
    UserPublic,
    UserUpdate,
)
from app.services import email_service

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> UserPublic:
    if crud_user.get_by_email(db, user_in.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = crud_user.create(db, user_in)
    if user.verification_token:
        try:
            email_service.send_welcome_verification_email(
                user.email, user.verification_token, user.full_name or ""
            )
        except Exception:
            logger.error(
                "Failed to send verification email after registration",
                extra={"user_id": str(user.id)},
                exc_info=True,
            )
    return user


@router.get("/verify-email", response_model=UserPublic)
def verify_email(token: str = Query(...), db: Session = Depends(get_db)) -> UserPublic:
    user = crud_user.verify_email(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link")
    return user


@router.post("/resend-verification", status_code=status.HTTP_204_NO_CONTENT)
def resend_verification(
    current_user: User = Depends(get_current_user_unverified),
    db: Session = Depends(get_db),
) -> None:
    if current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")
    token = crud_user.refresh_verification_token(db, current_user)
    try:
        email_service.send_welcome_verification_email(current_user.email, token, current_user.full_name or "")
    except Exception:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to send verification email") from None


@router.post("/login", response_model=TokenPair)
def login(login_in: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    user = crud_user.authenticate(db, login_in.email, login_in.password)
    if not user:
        logger.warning(
            "auth_login_failed",
            extra={"ip": request.client.host if request.client else "unknown"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/token", response_model=Token)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """OAuth2-compatible form login — used by the Swagger UI 'Authorize' button."""
    user = crud_user.authenticate(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return Token(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> Token:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            logger.warning(
                "auth_refresh_wrong_token_type",
                extra={"ip": request.client.host if request.client else "unknown"},
            )
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        logger.warning(
            "auth_refresh_invalid_token",
            extra={"ip": request.client.host if request.client else "unknown"},
        )
        raise credentials_exception from None

    # Check refresh token denylist (fail open: Redis outage must not block token refresh)
    try:
        token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
        r = get_redis_client()
        if r.exists(f"token_denylist:{token_hash}"):
            raise credentials_exception
    except HTTPException:
        raise
    except Exception:
        pass

    user = crud_user.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return Token(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user_unverified)) -> UserPublic:
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user_unverified),
    db: Session = Depends(get_db),
) -> UserPublic:
    return crud_user.update_profile(db, current_user, body)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user_unverified),
    db: Session = Depends(get_db),
) -> None:
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    crud_user.update_password(db, current_user, body.new_password)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: User = Depends(get_current_user_unverified),
    db: Session = Depends(get_db),
) -> None:
    crud_user.delete(db, current_user)


def _revoke_token(raw_token: str) -> None:
    """Store a token's SHA-256 hash in the denylist with TTL = remaining lifetime."""
    try:
        from datetime import UTC, datetime
        payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp = payload.get("exp")
        if exp is not None:
            remaining = math.ceil(exp - datetime.now(UTC).timestamp())
            if remaining > 0:
                token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
                r = get_redis_client()
                r.setex(f"token_denylist:{token_hash}", remaining, "1")
    except Exception:
        pass  # fail silently — tokens are short-lived anyway


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    body: LogoutRequest,
    user_id: str = Depends(get_current_user_id),
) -> None:
    # Revoke the access token from the Authorization header
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        _revoke_token(auth.split(" ", 1)[1])

    # Revoke the refresh token if the client sent it
    if body.refresh_token:
        _revoke_token(body.refresh_token)


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    # Always return 204 to prevent email enumeration
    user = crud_user.get_by_email(db, body.email)
    if user and user.is_active:
        token = crud_user.create_password_reset_token(db, user)
        try:
            email_service.send_password_reset_email(user.email, token)
        except Exception:
            logger.error(
                "Failed to send password reset email",
                extra={"user_id": str(user.id)},
                exc_info=True,
            )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> None:
    user = crud_user.consume_password_reset_token(db, body.token, body.new_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link",
        )
