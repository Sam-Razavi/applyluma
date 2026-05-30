from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.contact import ContactRequest
from app.services import email_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/contact", tags=["public"])


def _verify_turnstile(token: str) -> bool:
    try:
        payload = urllib.parse.urlencode({
            "secret": settings.TURNSTILE_SECRET_KEY,
            "response": token,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v1/siteverify",
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if not data.get("success"):
                logger.warning("Turnstile verification failed: %s", data.get("error-codes", []))
            return data.get("success", False)
    except urllib.error.HTTPError as exc:
        body = exc.read()
        logger.warning("Turnstile HTTP error %s: %s", exc.code, body)
        return False
    except Exception as exc:
        logger.exception("Turnstile request error: %s", exc)
        return False


def _admin_html(name: str, email: str, subject: str, message: str) -> str:
    safe_name = name.replace("<", "&lt;").replace(">", "&gt;")
    safe_email = email.replace("<", "&lt;").replace(">", "&gt;")
    safe_subject = subject.replace("<", "&lt;").replace(">", "&gt;") or "No subject"
    safe_message = message.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    return f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
  <h2 style="color:#4F46E5">New contact form submission</h2>
  <table style="border-collapse:collapse;width:100%">
    <tr><td style="padding:8px;font-weight:bold;width:80px">Name</td><td style="padding:8px">{safe_name}</td></tr>
    <tr style="background:#f9fafb"><td style="padding:8px;font-weight:bold">Email</td><td style="padding:8px"><a href="mailto:{safe_email}">{safe_email}</a></td></tr>
    <tr><td style="padding:8px;font-weight:bold">Subject</td><td style="padding:8px">{safe_subject}</td></tr>
  </table>
  <div style="margin-top:16px;padding:16px;background:#f9fafb;border-radius:8px;white-space:pre-wrap">{safe_message}</div>
</div>
"""


def _confirmation_html(name: str) -> str:
    safe_name = name.replace("<", "&lt;").replace(">", "&gt;")
    return f"""
<div style="font-family:sans-serif;max-width:600px;margin:0 auto">
  <h2 style="color:#4F46E5">We got your message, {safe_name}!</h2>
  <p>Thanks for reaching out. We typically respond within 24 hours.</p>
  <p style="color:#6b7280;font-size:14px">— The ApplyLuma team</p>
</div>
"""


@router.post("", status_code=status.HTTP_200_OK)
def submit_contact(body: ContactRequest) -> dict[str, bool]:
    if not _verify_turnstile(body.turnstile_token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please try again.",
        )

    subject_line = body.subject.strip() or "No subject"
    admin_subject = f"[ApplyLuma Contact] {subject_line}"

    email_service.send_email(
        to_email=settings.CONTACT_RECIPIENT_EMAIL,
        subject=admin_subject,
        html_body=_admin_html(body.name, body.email, body.subject, body.message),
    )
    email_service.send_email(
        to_email=body.email,
        subject="We received your message — ApplyLuma",
        html_body=_confirmation_html(body.name),
    )

    return {"ok": True}
