from app.core.config import settings

EMAIL_TEMPLATES = {
    "verify_email": {
        "subject": "Verify your ApplyLuma email",
        "body": "<p>Thanks for signing up! Click the link below to verify your email address.</p>",
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
    template = EMAIL_TEMPLATES.get(type)
    if not template:
        return title, f"<p>{body}</p>"
    return template["subject"], f"{template['body']}<p>{body}</p>"


def send_verification_email(to_email: str, token: str) -> None:
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    verify_url = f"{frontend_url}/verify-email?token={token}"
    subject = "Verify your ApplyLuma email"
    html_body = (
        "<p>Thanks for signing up for ApplyLuma!</p>"
        f'<p><a href="{verify_url}" style="background:#6366f1;color:#fff;padding:10px 20px;'
        f'border-radius:8px;text-decoration:none;font-weight:bold;">Verify my email</a></p>'
        f'<p>Or copy this link: {verify_url}</p>'
        "<p>This link expires in 24 hours.</p>"
    )
    send_email(to_email, subject, html_body)


def send_email(to_email: str, subject: str, html_body: str) -> None:
    if not settings.SENDGRID_API_KEY:
        return

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        html_content=html_body,
    )
    SendGridAPIClient(settings.SENDGRID_API_KEY).send(message)
