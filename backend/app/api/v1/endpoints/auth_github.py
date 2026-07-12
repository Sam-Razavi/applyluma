"""GitHub OAuth login.

Same shape as auth_google, with two GitHub quirks: the token endpoint needs
an explicit Accept: application/json header, and the /user profile may have
a null public email — in that case the verified primary address is fetched
from /user/emails (covered by the user:email scope).
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

router = APIRouter(prefix="/auth/github", tags=["auth"])
logger = logging.getLogger(__name__)

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


@router.get("/login")
def github_login() -> RedirectResponse:
    """Redirect the user to GitHub's consent screen."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured",
        )

    state = secrets.token_urlsafe(32)
    oauth_common.store_state(state)
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state,
    }
    return oauth_common.state_cookie_redirect(f"{GITHUB_AUTH_URL}?{urlencode(params)}", state)


@router.get("/callback")
def github_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Handle GitHub's redirect: validate state, exchange code, upsert user, issue tokens."""
    if error or not code:
        logger.warning("github_oauth_callback_error", extra={"error": error})
        return oauth_common.login_failed_redirect()

    cookie_state = request.cookies.get(oauth_common.STATE_COOKIE)
    if not oauth_common.consume_state(state, cookie_state):
        logger.warning("github_oauth_state_mismatch")
        return oauth_common.login_failed_redirect()

    try:
        token_data = _exchange_code_for_tokens(code)
        access_token = token_data["access_token"]
        user_info = _fetch_github_user_info(access_token)
        email = user_info.get("email") or _fetch_github_primary_email(access_token)
    except (httpx.HTTPError, KeyError):
        logger.exception("github_oauth_exchange_failed")
        return oauth_common.login_failed_redirect()

    github_id = user_info.get("id")
    if not github_id or not email:
        # Accounts can't be linked without a verified email address.
        logger.warning("github_oauth_missing_profile_fields")
        return oauth_common.login_failed_redirect()

    user = crud_user.upsert_oauth_user(
        db,
        provider="github",
        id_attr="github_id",
        provider_user_id=str(github_id),
        email=str(email),
        full_name=user_info.get("name") or user_info.get("login"),
        avatar_url=user_info.get("avatar_url"),
    )
    return oauth_common.complete_oauth_login(db, user)


def _exchange_code_for_tokens(code: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "code": code,
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


def _fetch_github_user_info(github_access_token: str) -> dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {github_access_token}"},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data


def _fetch_github_primary_email(github_access_token: str) -> str | None:
    """The public profile email is often null; read the verified primary instead."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            GITHUB_EMAILS_URL,
            headers={"Authorization": f"Bearer {github_access_token}"},
        )
        resp.raise_for_status()
        emails: list[dict[str, Any]] = resp.json()
    for entry in emails:
        if entry.get("primary") and entry.get("verified"):
            return str(entry["email"])
    for entry in emails:
        if entry.get("verified"):
            return str(entry["email"])
    return None
