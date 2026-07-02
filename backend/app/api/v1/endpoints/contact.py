from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.schemas.contact import ContactRequest
from app.services import email_service

router = APIRouter(prefix="/contact", tags=["public"])
logger = logging.getLogger(__name__)

# Cloudflare's official always-pass test secret (the config default). When it
# is active there is nothing meaningful to verify, so verification is skipped —
# this keeps local dev and tests offline. Set a real secret in production to
# turn verification on.
_TURNSTILE_TEST_SECRET = "1x0000000000000000000000000000000AA"
_TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def _verify_turnstile(token: str, remote_ip: str | None) -> bool:
    secret = settings.TURNSTILE_SECRET_KEY
    if not secret or secret == _TURNSTILE_TEST_SECRET:
        return True
    if not token:
        return False
    data = {"secret": secret, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        response = httpx.post(_TURNSTILE_VERIFY_URL, data=data, timeout=5.0)
        return bool(response.json().get("success"))
    except Exception:
        # Fail open: a Cloudflare outage must not take down the contact form.
        logger.error("Turnstile verification request failed", exc_info=True)
        return True

_BASE = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:40px 16px">
  <tr><td align="center">
    <table width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">

      <!-- Header -->
      <tr>
        <td style="background:linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%);padding:32px 40px;text-align:center">
          <span style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.5px">ApplyLuma</span>
        </td>
      </tr>

      <!-- Body -->
      <tr><td style="padding:36px 40px 28px">
        {body}
      </td></tr>

      <!-- Footer -->
      <tr>
        <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:20px 40px;text-align:center">
          <p style="margin:0;font-size:12px;color:#9ca3af">
            © 2025 ApplyLuma &nbsp;·&nbsp;
            <a href="https://applyluma.com" style="color:#6b7280;text-decoration:none">applyluma.com</a>
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""


def _wrap(body: str) -> str:
    return _BASE.replace("{body}", body)


def _admin_html(name: str, email: str, subject: str, message: str) -> str:
    def s(t: str) -> str:
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_subject = s(subject).strip() or "No subject"
    safe_message = s(message).replace("\n", "<br>")
    body = f"""
<h2 style="margin:0 0 6px;font-size:20px;font-weight:700;color:#111827">New message from {s(name)}</h2>
<p style="margin:0 0 24px;font-size:14px;color:#6b7280">Submitted via the contact form on applyluma.com</p>

<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:24px">
  <tr style="background:#f9fafb">
    <td style="padding:10px 16px;width:80px;font-size:13px;font-weight:600;color:#374151;border-bottom:1px solid #e5e7eb">From</td>
    <td style="padding:10px 16px;font-size:13px;color:#111827;border-bottom:1px solid #e5e7eb">
      {s(name)} &lt;<a href="mailto:{s(email)}" style="color:#4F46E5;text-decoration:none">{s(email)}</a>&gt;
    </td>
  </tr>
  <tr>
    <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#374151">Subject</td>
    <td style="padding:10px 16px;font-size:13px;color:#111827">{safe_subject}</td>
  </tr>
</table>

<p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#374151;text-transform:uppercase;letter-spacing:.05em">Message</p>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px 20px;font-size:14px;color:#374151;line-height:1.7;white-space:pre-wrap">{safe_message}</div>

<div style="margin-top:28px;text-align:center">
  <a href="mailto:{s(email)}" style="display:inline-block;background:#4F46E5;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:12px 28px;border-radius:8px">
    Reply to {s(name)}
  </a>
</div>
"""
    return _wrap(body)


def _confirmation_html(name: str, subject: str, message: str) -> str:
    def s(t: str) -> str:
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_subject = s(subject).strip() or "No subject"
    safe_message = s(message).replace("\n", "<br>")
    preview = safe_message[:120] + ("…" if len(message) > 120 else "")
    body = f"""
<h2 style="margin:0 0 8px;font-size:20px;font-weight:700;color:#111827">Thanks for reaching out, {s(name)}!</h2>
<p style="margin:0 0 28px;font-size:15px;color:#6b7280;line-height:1.6">
  We received your message and will get back to you within <strong style="color:#374151">24 hours</strong>.
</p>

<div style="background:#f5f3ff;border-left:4px solid #4F46E5;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:28px">
  <p style="margin:0 0 4px;font-size:12px;font-weight:600;color:#7C3AED;text-transform:uppercase;letter-spacing:.06em">Your message</p>
  <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#374151">{safe_subject}</p>
  <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.6">{preview}</p>
</div>

<p style="margin:0 0 28px;font-size:14px;color:#6b7280;line-height:1.6">
  In the meantime, feel free to explore the app or check out our premium features.
</p>

<div style="text-align:center">
  <a href="https://applyluma.com/dashboard" style="display:inline-block;background:#4F46E5;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:12px 28px;border-radius:8px">
    Go to dashboard →
  </a>
</div>

<p style="margin:28px 0 0;font-size:13px;color:#9ca3af;text-align:center">— The ApplyLuma team</p>
"""
    return _wrap(body)


@router.post("", status_code=status.HTTP_200_OK)
def submit_contact(body: ContactRequest, request: Request) -> dict[str, bool]:
    if body.honeypot:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission.")

    remote_ip = request.client.host if request.client else None
    if not _verify_turnstile(body.turnstile_token, remote_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CAPTCHA verification failed. Please try again.",
        )

    subject_line = body.subject.strip() or "No subject"

    email_service.send_email(
        to_email=settings.CONTACT_RECIPIENT_EMAIL,
        subject=f"[ApplyLuma Contact] {subject_line}",
        html_body=_admin_html(body.name, body.email, body.subject, body.message),
    )
    email_service.send_email(
        to_email=body.email,
        subject="We received your message — ApplyLuma",
        html_body=_confirmation_html(body.name, body.subject, body.message),
    )

    return {"ok": True}
