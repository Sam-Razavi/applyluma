"""LinkedIn login via "Sign In with LinkedIn using OpenID Connect".

Same shape as auth_google: /login redirects to the consent screen with a
CSRF state; /callback validates state, exchanges the code, reads the OIDC
userinfo endpoint, and upserts the user.
"""
import logging
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.v1.endpoints import oauth_common
from app.core.config import settings
from app.core.dependencies import get_db
from app.crud import user as crud_user

router = APIRouter(prefix="/auth/linkedin", tags=["auth"])
logger = logging.getLogger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


@router.get("/login")
def linkedin_login() -> RedirectResponse:
    """Redirect the user to LinkedIn's consent screen."""
    if not settings.LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="LinkedIn OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    oauth_common.store_state(state)
    params = {
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
    }
    return oauth_common.state_cookie_redirect(f"{LINKEDIN_AUTH_URL}?{urlencode(params)}", state)


@router.get("/callback")
def linkedin_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle LinkedIn's redirect: validate state, exchange code, upsert user, issue tokens."""
    if error or not code:
        logger.warning("linkedin_oauth_callback_error", extra={"error": error})
        return oauth_common.login_failed_redirect()

    cookie_state = request.cookies.get(oauth_common.STATE_COOKIE)
    if not oauth_common.consume_state(state, cookie_state):
        logger.warning("linkedin_oauth_state_mismatch")
        return oauth_common.login_failed_redirect()

    try:
        token_data = _exchange_code_for_tokens(code)
        user_info = _fetch_linkedin_user_info(token_data["access_token"])
    except (httpx.HTTPError, KeyError):
        logger.exception("linkedin_oauth_exchange_failed")
        return oauth_common.login_failed_redirect()

    # OIDC userinfo: `sub` is the stable member id.
    linkedin_id = user_info.get("sub")
    email = user_info.get("email")
    if not linkedin_id or not email:
        logger.warning("linkedin_oauth_missing_profile_fields")
        return oauth_common.login_failed_redirect()

    user = crud_user.upsert_oauth_user(
        db,
        provider="linkedin",
        id_attr="linkedin_id",
        provider_user_id=str(linkedin_id),
        email=str(email),
        full_name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )
    return oauth_common.complete_oauth_login(db, user)


def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.LINKEDIN_CLIENT_ID,
                "client_secret": settings.LINKEDIN_CLIENT_SECRET,
                "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


def _fetch_linkedin_user_info(linkedin_access_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            LINKEDIN_USERINFO_URL,
            headers={"Authorization": f"Bearer {linkedin_access_token}"},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data
