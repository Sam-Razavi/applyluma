"""Provider-agnostic plumbing shared by the OAuth login endpoints
(auth_google / auth_linkedin / auth_github): CSRF state handling, auth
cookies, and the success/failure redirects back to the frontend.

Provider modules keep their own URLs, scopes, token exchange, and userinfo
parsing — everything here is identical across providers.
"""
import logging
import secrets
from typing import Any

from fastapi import status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_redis_client
from app.core.security import create_access_token, create_refresh_token
from app.crud import user as crud_user
from app.models.user import User

logger = logging.getLogger(__name__)

# Server-side state store. The state cookie can't be relied on alone because the
# OAuth /login and /callback may be served on different hostnames (e.g. the
# frontend hits the API on one domain while the provider's redirect_uri points at
# another), so the cookie set on /login isn't present on /callback. Storing the
# state in Redis makes validation independent of cookies/domains.
STATE_PREFIX = "oauth_state:"

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 600


def prod() -> bool:
    return settings.ENVIRONMENT == "production"


def store_state(state: str) -> None:
    try:
        get_redis_client().setex(f"{STATE_PREFIX}{state}", STATE_TTL_SECONDS, "1")
    except Exception:
        logger.warning("oauth_state_redis_store_failed", exc_info=True)


def consume_state(state: str | None, cookie_state: str | None) -> bool:
    """Validate the returned state against the cookie OR the Redis store."""
    if not state:
        return False
    if cookie_state and secrets.compare_digest(state, cookie_state):
        return True
    try:
        redis_client = get_redis_client()
        if redis_client.get(f"{STATE_PREFIX}{state}"):
            redis_client.delete(f"{STATE_PREFIX}{state}")
            return True
    except Exception:
        logger.warning("oauth_state_redis_check_failed", exc_info=True)
    return False


def cookie_kwargs(max_age: int) -> dict[str, Any]:
    return {
        "httponly": True,
        "secure": prod(),
        "samesite": "none" if prod() else "lax",
        "max_age": max_age,
    }


def set_auth_cookies(response: RedirectResponse, access_token: str, refresh_token: str) -> None:
    """Mirror the cookie pattern used by the password-login endpoint."""
    response.set_cookie(ACCESS_COOKIE, access_token, **cookie_kwargs(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60))
    response.set_cookie(REFRESH_COOKIE, refresh_token, **cookie_kwargs(settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400))
    response.set_cookie(
        CSRF_COOKIE,
        secrets.token_hex(32),
        httponly=False,
        secure=prod(),
        samesite="none" if prod() else "lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def login_failed_redirect() -> RedirectResponse:
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/login?error=oauth_failed",
        status_code=status.HTTP_302_FOUND,
    )
    response.delete_cookie(STATE_COOKIE, secure=prod(), samesite="lax")
    return response


def state_cookie_redirect(url: str, state: str) -> RedirectResponse:
    """302 to the provider's consent screen carrying the state cookie.

    The OAuth callback is a cross-site, top-level GET redirect from the
    provider. SameSite=Lax cookies ARE sent on top-level navigations and are
    not subject to third-party-cookie blocking; SameSite=None would be dropped
    by browsers (Safari ITP / Chrome 3PC restrictions), breaking the state check.
    """
    response = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        STATE_COOKIE,
        state,
        httponly=True,
        secure=prod(),
        samesite="lax",
        max_age=STATE_TTL_SECONDS,
    )
    return response


def complete_oauth_login(db: Session, user: User) -> RedirectResponse:
    """Record the login, mint tokens, and redirect back to the frontend.

    The token is in the URL fragment, not the query string: fragments are
    never sent to the server (not in the redirect's own request line, not
    in Referer headers, not to Vercel/Railway access logs), only read
    client-side by AuthCallback.tsx. usePageTracking also excludes this
    route so the token never reaches PostHog either.
    """
    crud_user.record_login(db, user)
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback#token={access_token}",
        status_code=status.HTTP_302_FOUND,
    )
    set_auth_cookies(response, access_token, refresh_token)
    response.delete_cookie(STATE_COOKIE, secure=prod(), samesite="lax")
    return response
