from app.core.config import settings


def escape_html(text: str) -> str:
    """Escape user-controlled text before interpolating it into an HTML email
    body. Notification/verification bodies and names ultimately come from
    user-supplied data (full_name, application company/job title, etc.) and
    are otherwise inserted into raw HTML f-strings with no templating engine
    autoescape to fall back on."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


EMAIL_TEMPLATES = {
    "verify_email": {
        "subject": "Verify your ApplyLuma email",
        "body": "<p>Thanks for signing up! Click the link below to verify your email address.</p>",
    },
    "deadline_reminder": {
        "subject": "Application deadline approaching",
        "body": "<p>One of your job applications has a deadline coming up soon.</p>",
    },
    "tailor_complete": {
        "subject": "Your tailored CV is ready",
        "body": "<p>Your AI-tailored CV is ready to review in ApplyLuma.</p>",
    },
    "interview_reminder": {
        "subject": "Interview stage reached",
        "body": "<p>An application moved to interview. Review the details and prepare next steps.</p>",
    },
    "application_stale": {
        "subject": "Application follow-up reminder",
        "body": "<p>An application has been in applied status for more than 7 days.</p>",
    },
    "weekly_summary": {
        "subject": "Your weekly application summary",
        "body": "<p>Your weekly application funnel summary is ready.</p>",
    },
    "high_match_alert": {
        "subject": "New high-match jobs",
        "body": "<p>New jobs match your profile in ApplyLuma.</p>",
    },
}


def template_email(type: str, title: str, body: str) -> tuple[str, str]:
    safe_body = escape_html(body)
    template = EMAIL_TEMPLATES.get(type)
    if not template:
        return title, f"<p>{safe_body}</p>"
    return template["subject"], f"{template['body']}<p>{safe_body}</p>"


def send_welcome_verification_email(to_email: str, token: str, full_name: str = "") -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    verify_url = f"{frontend_url}/verify-email?token={token}"
    safe_name = escape_html(full_name.split()[0]) if full_name.strip() else ""
    greeting = f"Welcome, {safe_name}!" if safe_name else "Welcome to ApplyLuma!"
    subject = "Welcome to ApplyLuma — please verify your email"
    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:40px 16px">
  <tr><td align="center">
    <table width="100%" style="max-width:560px;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">
      <tr>
        <td style="background:linear-gradient(135deg,#4F46E5 0%,#7C3AED 100%);padding:32px 40px;text-align:center">
          <span style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.5px">ApplyLuma</span>
        </td>
      </tr>
      <tr><td style="padding:36px 40px 28px">
        <h2 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#111827">{greeting}</h2>
        <p style="margin:0 0 20px;font-size:15px;color:#6b7280;line-height:1.6">
          You're one step away from your ApplyLuma account. Click the button below to verify your email and get started.
        </p>
        <div style="margin:0 0 24px;background:#f5f3ff;border-radius:10px;padding:20px 24px">
          <p style="margin:0 0 6px;font-size:13px;font-weight:600;color:#7C3AED;text-transform:uppercase;letter-spacing:.06em">With ApplyLuma you can</p>
          <ul style="margin:8px 0 0;padding-left:20px;font-size:14px;color:#374151;line-height:1.8">
            <li>Upload your CV and get AI-powered feedback</li>
            <li>Tailor your CV to any job description in seconds</li>
            <li>Track every application in one place</li>
          </ul>
        </div>
        <div style="text-align:center;margin-bottom:24px">
          <a href="{verify_url}" style="display:inline-block;background:#4F46E5;color:#ffffff;text-decoration:none;font-size:15px;font-weight:600;padding:14px 32px;border-radius:8px">
            Verify my email →
          </a>
        </div>
        <p style="margin:0 0 4px;font-size:12px;color:#9ca3af;text-align:center">
          Or copy this link into your browser:
        </p>
        <p style="margin:0;font-size:11px;color:#9ca3af;text-align:center;word-break:break-all">{verify_url}</p>
        <p style="margin:20px 0 0;font-size:12px;color:#d1d5db;text-align:center">This link expires in 24 hours.</p>
      </td></tr>
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
    send_email(to_email, subject, html_body)


def send_password_reset_email(to_email: str, token: str) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={token}"
    subject = "Reset your ApplyLuma password"
    html_body = (
        "<p>We received a request to reset your ApplyLuma password.</p>"
        f'<p><a href="{reset_url}" style="background:#6366f1;color:#fff;padding:10px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:bold;">Reset my password</a></p>'
        f'<p>Or copy this link: {reset_url}</p>'
        "<p>This link expires in 1 hour. If you did not request a password reset, you can safely ignore this email.</p>"
    )
    send_email(to_email, subject, html_body)


def send_magic_link_email(to_email: str, token: str) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    login_url = f"{frontend_url}/magic-login?token={token}"
    subject = "Your ApplyLuma sign-in link"
    html_body = (
        "<p>Click the button below to sign in to ApplyLuma.</p>"
        f'<p><a href="{login_url}" style="background:#6366f1;color:#fff;padding:10px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:bold;">Sign in to ApplyLuma</a></p>'
        f'<p>Or copy this link: {login_url}</p>'
        "<p>This link expires in 15 minutes and can be used once. "
        "If you did not request it, you can safely ignore this email.</p>"
    )
    send_email(to_email, subject, html_body)


def send_email(to_email: str, subject: str, html_body: str) -> None:
    if not settings.RESEND_API_KEY:
        return

    import resend

    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": settings.RESEND_FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    })
