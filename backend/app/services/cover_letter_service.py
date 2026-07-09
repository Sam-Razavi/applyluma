"""
Cover letter generation service: calls OpenAI and returns a polished cover letter.
"""
import re
import uuid

from langdetect import LangDetectException, detect
from openai import AuthenticationError, OpenAI, RateLimitError

from app.core.config import settings
from app.models.cover_letter_job import CoverLetterTone
from app.services import ai_usage

_TONE_INSTRUCTIONS: dict[CoverLetterTone, str] = {
    CoverLetterTone.formal: (
        "Write in a professional, formal tone. Use traditional salutation ('Dear Hiring Manager' or "
        "the person's name if provided). Structured paragraphs, precise language, 300–350 words."
    ),
    CoverLetterTone.friendly: (
        "Write in a warm but professional tone. Slightly conversational without being casual. "
        "Show genuine enthusiasm for the role and company. 300–350 words."
    ),
    CoverLetterTone.concise: (
        "Write a tight, direct cover letter. No filler phrases, no lengthy introductions. "
        "Get to the point fast. 200–250 words maximum."
    ),
}

_CONTACT_SIGNAL_RE = re.compile(
    r"@|\+?\d[\d\s().-]{6,}|linkedin|github|portfolio|https?://|www\.",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = """\
You are an expert career coach and cover letter writer. Write a compelling cover letter
that will capture the hiring manager's attention and increase the candidate's interview chances.

Core rules — non-negotiable:
- Lead with the single most relevant experience or achievement that matches the job
- Mirror terminology and priorities from the job description
- Include quantified metrics and concrete examples from the CV wherever available
- Never fabricate companies, dates, achievements, credentials, or technologies
- Do not use clichés ("I am passionate about", "results-driven", "team player")
- Use the detected CV language: {detected_language}
- Address the company by name if available; address the hiring manager by name only if provided

Tone instruction:
{tone_instruction}

Structure (adapt as needed for the tone):
1. Opening — hook sentence that immediately signals fit for the specific role
2. Body paragraph(s) — 1–2 paragraphs connecting the candidate's strongest relevant experience to the JD
3. Closing — brief expression of interest, clear call to action, professional sign-off

Return ONLY a valid JSON object with this structure:
{{
  "language": "<ISO 639-1 code, e.g. en, sv, de>",
  "cover_letter_text": "<the complete cover letter as a single string with \\n for line breaks>",
  "word_count": <integer>,
  "tone_applied": "<formal|friendly|concise>"
}}
"""


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def _extract_contact_block(cv_content: str) -> str:
    """Return the first few lines of the CV that contain contact signals."""
    lines = cv_content.splitlines()
    contact_lines: list[str] = []
    for line in lines[:20]:
        stripped = line.strip()
        if not stripped:
            if contact_lines:
                break
            continue
        if _CONTACT_SIGNAL_RE.search(stripped) or (not contact_lines and stripped):
            contact_lines.append(stripped)
        elif contact_lines and len(contact_lines) >= 2:
            break
    return "\n".join(contact_lines)


def generate_cover_letter(
    cv_content: str,
    jd_description: str,
    jd_company: str,
    jd_title: str,
    tone: CoverLetterTone,
    user_id: uuid.UUID | None = None,
) -> dict:
    language = _detect_language(cv_content)
    contact_block = _extract_contact_block(cv_content)

    system_prompt = _SYSTEM_PROMPT.format(
        detected_language=language,
        tone_instruction=_TONE_INSTRUCTIONS[tone],
    )

    user_message = (
        f"Company: {jd_company}\n"
        f"Job Title: {jd_title}\n\n"
        f"Job Description:\n{jd_description}\n\n"
        f"Candidate CV:\n{cv_content}"
    )
    if contact_block:
        user_message += f"\n\nCandidate Contact Information (preserve exactly):\n{contact_block}"

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0)
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2048,
            temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except AuthenticationError as exc:
        raise RuntimeError("AI service authentication failed; check OPENAI_API_KEY") from exc
    except RateLimitError as exc:
        raise RuntimeError("AI service rate limit exceeded, please try again later") from exc

    ai_usage.record_ai_usage(
        purpose="cover_letter", model="gpt-4o", usage=getattr(response, "usage", None), user_id=user_id
    )

    raw = response.choices[0].message.content or ""
    import json
    result = json.loads(raw)

    # Ensure required fields are present
    cover_letter_text = result.get("cover_letter_text", "")
    word_count = result.get("word_count") or len(cover_letter_text.split())
    detected_language = result.get("language", language)

    return {
        "language": detected_language,
        "cover_letter_text": cover_letter_text,
        "word_count": int(word_count),
        "tone_applied": result.get("tone_applied", tone.value),
    }
