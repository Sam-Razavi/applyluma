"""
CV tailoring service: calls OpenAI and returns a structured section-by-section diff.
"""
import json

from langdetect import LangDetectException, detect
from openai import AuthenticationError, OpenAI, RateLimitError

from app.core.config import settings
from app.models.tailor_job import TailorIntensity

_INTENSITY_INSTRUCTIONS: dict[TailorIntensity, str] = {
    TailorIntensity.light: (
        "Make minimal changes. Fix obvious keyword gaps, tighten the summary, and reorder bullets "
        "to lead with the most relevant. Do not change the overall structure or remove sections."
    ),
    TailorIntensity.medium: (
        "Restructure bullet points to emphasise keywords from the job description. "
        "Rewrite the summary. Add or promote relevant sections. Remove or demote irrelevant ones."
    ),
    TailorIntensity.aggressive: (
        "Completely optimise the CV for this specific role. Rewrite every bullet for maximum "
        "keyword match and quantified impact. Remove anything not relevant to the target role. "
        "Restructure section order to match job-level norms. Add a tailored summary."
    ),
}

_SYSTEM_PROMPT = """\
You are an expert tech resume writer and career coach. Rewrite the candidate's CV
to maximise interview chances for the specific job description provided.

Core rules - non-negotiable:
- PDF format only, two pages max, reverse chronological, one-column layout
- Active verbs, quantified bullets, and measurable impact wherever the source CV supports it
- Never fabricate numbers, companies, titles, dates, credentials, employers, or technologies
- Mirror terminology from the job description
- No self-rated skill bars, no "References available on request", no photos
- Dates: "June 2021 - July 2022" format; drop month for dates older than four years old
- Bold only titles, companies, and dates

Career-level section ordering:
- New graduate or junior: Summary, Skills, Projects, Experience, Education
- Mid-level engineer: Summary, Skills, Experience, Projects, Education
- Senior or staff engineer: Summary, Technical Leadership, Experience, Skills, Education
- Tech lead: Summary, Leadership Impact, Experience, Architecture, Skills, Education
- Engineering manager: Summary, Leadership Scope, Experience, People/Delivery Impact,
  Skills, Education
- Career changer or career break: Summary, Relevant Experience, Projects,
  Earlier Experience, Education

Special cases:
- If there is a career break, frame it neutrally and only if the CV already mentions it.
- For technical leads, surface architecture, mentoring, delivery risk, and cross-team influence.
- For engineering managers, surface team size, hiring, performance, planning, and delivery outcomes.
- For highly technical IC roles, keep concrete technologies close to the relevant achievements.
- Preserve the candidate's language and spelling conventions.
  The detected language is {detected_language}.

Intensity instruction:
{intensity_instruction}

Output requirements:
- Split the CV into logical sections.
- Include each section's original text verbatim.
- Include a tailored rewrite for each accepted section.
- Include "changes" as the "Changes made" explanation: what changed and why.
- If a section should be removed for the target role, return an empty "tailored" value
  and explain why in "changes".
- Return the same language as the source CV unless the job description clearly requires
  a different language.

Return ONLY a valid JSON object with this structure:
{{
  "language": "<ISO 639-1 code of the CV language, e.g. en, sv, de>",
  "sections": [
    {{
      "section_id": "<snake_case unique id, e.g. summary, experience_0, skills>",
      "section_name": "<human-readable section heading>",
      "original": "<verbatim original text for this section>",
      "tailored": "<rewritten text for this section>",
      "changes": ["<what changed and why>", "..."]
    }}
  ],
  "meta": {{
    "keywords_added": ["<keyword added>"],
    "keywords_already_present": ["<keyword already in CV>"],
    "intensity_applied": "<light|medium|aggressive>"
  }}
}}
"""


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def tailor_cv(
    cv_content: str,
    jd_description: str,
    jd_keywords: list[str],
    intensity: TailorIntensity,
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    detected_language = _detect_language(cv_content)
    system_prompt = _SYSTEM_PROMPT.format(
        intensity_instruction=_INTENSITY_INSTRUCTIONS[intensity],
        detected_language=detected_language,
    )
    keywords_str = ", ".join(jd_keywords) if jd_keywords else "None extracted"
    user_message = (
        f"Job Description\n{jd_description}\n\n"
        f"Target Keywords\n{keywords_str}\n\n"
        f"Candidate CV\n{cv_content}"
    )

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )
    except AuthenticationError as exc:
        raise ValueError("AI service authentication failed; check OPENAI_API_KEY") from exc
    except RateLimitError as exc:
        raise ValueError("AI service rate limit exceeded, please try again later") from exc
    except Exception as exc:
        raise ValueError(f"AI API error: {exc}") from exc

    raw = response.choices[0].message.content or ""
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI returned non-JSON: {exc}") from exc
    result["language"] = result.get("language") or detected_language
    return result
