import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db, get_redis_client
from app.core.security import create_access_token, create_refresh_token
from app.crud import user as crud_user

router = APIRouter(prefix="/auth/google", tags=["auth"])
logger = logging.getLogger(__name__)

# Server-side state store. The state cookie can't be relied on alone because the
# OAuth /login and /callback may be served on different hostnames (e.g. the
# frontend hits the API on one domain while Google's redirect_uri points at
# another), so the cookie set on /login isn't present on /callback. Storing the
# state in Redis makes validation independent of cookies/domains.
_STATE_PREFIX = "oauth_state:"


def _store_state(state: str) -> None:
    try:
        get_redis_client().setex(f"{_STATE_PREFIX}{state}", _STATE_TTL_SECONDS, "1")
    except Exception:
        logger.warning("oauth_state_redis_store_failed", exc_info=True)


def _consume_state(state: str | None, cookie_state: str | None) -> bool:
    """Validate the returned state against the cookie OR the Redis store."""
    if not state:
        return False
    if cookie_state and secrets.compare_digest(state, cookie_state):
        return True
    try:
        redis_client = get_redis_client()
        if redis_client.get(f"{_STATE_PREFIX}{state}"):
            redis_client.delete(f"{_STATE_PREFIX}{state}")
            return True
    except Exception:
        logger.warning("oauth_state_redis_check_failed", exc_info=True)
    return False

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

_ACCESS_COOKIE = "access_token"
_REFRESH_COOKIE = "refresh_token"
_CSRF_COOKIE = "csrf_token"
_STATE_COOKIE = "oauth_state"
_STATE_TTL_SECONDS = 600


def _prod() -> bool:
    return settings.ENVIRONMENT == "production"


def _cookie_kwargs(max_age: int) -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": _prod(),
        "samesite": "none" if _prod() else "lax",
        "max_age": max_age,
    }


def _set_auth_cookies(response: RedirectResponse, access_token: str, refresh_token: str) -> None:
    """Mirror the cookie pattern used by the password-login endpoint."""
    response.set_cookie(_ACCESS_COOKIE, access_token, **_cookie_kwargs(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    response.set_cookie(_REFRESH_COOKIE, refresh_token, **_cookie_kwargs(settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400))
    response.set_cookie(
        _CSRF_COOKIE,
        secrets.token_hex(32),
        httponly=False,
        secure=_prod(),
        samesite="none" if _prod() else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _login_failed_redirect() -> RedirectResponse:
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/login?error=oauth_failed",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(_STATE_COOKIE, secure=_prod(), samesite="lax")
    return response


@router.get("/login")
def google_login() -> RedirectResponse:
    """Redirect the user to Google's consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    _store_state(state)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    response = RedirectResponse(
        url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}",
        status_code=status.HTTP_302_FOUND,
    )
    # The OAuth callback is a cross-site, top-level GET redirect from Google.
    # SameSite=Lax cookies ARE sent on top-level navigations and are not subject
    # to third-party-cookie blocking; SameSite=None would be dropped by browsers
    # (Safari ITP / Chrome 3PC restrictions), breaking the state check.
    response.set_cookie(
        _STATE_COOKIE,
        state,
        httponly=True,
        secure=_prod(),
        samesite="lax",
        max_age=_STATE_TTL_SECONDS,
    )
    return response


@router.get("/callback")
def google_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle Google's redirect: validate state, exchange code, upsert user, issue tokens."""
    if error or not code:
        logger.warning("google_oauth_callback_error", extra={"error": error})
        return _login_failed_redirect()

    cookie_state = request.cookies.get(_STATE_COOKIE)
    if not _consume_state(state, cookie_state):
        logger.warning("google_oauth_state_mismatch")
        return _login_failed_redirect()

    try:
        token_data = _exchange_code_for_tokens(code)
        user_info = _fetch_google_user_info(token_data["access_token"])
    except (httpx.HTTPError, KeyError):
        logger.exception("google_oauth_exchange_failed")
        return _login_failed_redirect()

    google_id = user_info.get("id")
    email = user_info.get("email")
    if not google_id or not email:
        logger.warning("google_oauth_missing_profile_fields")
        return _login_failed_redirect()

    user = crud_user.upsert_google_user(
        db,
        google_id=str(google_id),
        email=str(email),
        full_name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )
    crud_user.record_login(db, user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}",
        status_code=status.HTTP_302_FOUND,
    )
    _set_auth_cookies(response, access_token, refresh_token)
    response.delete_cookie(_STATE_COOKIE, secure=_prod(), samesite="lax")
    return response


def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


def _fetch_google_user_info(google_access_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data
