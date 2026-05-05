import json

from openai import AuthenticationError, OpenAI, RateLimitError

from app.core.config import settings

_SYSTEM_PROMPT = """\
You are an expert CV reviewer specializing in ATS optimization and hiring.

Analyze the candidate's CV against the job description and return ONLY a valid JSON object — \
no markdown, no code fences, no prose outside the JSON.

Required structure:
{
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "recommendations": ["...", "..."],
  "full_analysis": "..."
}

Rules:
- strengths: 3-5 items — cite specific CV content that directly matches a JD requirement
- gaps: 3-5 items — name exact skills, tools, or experience the JD requires that are absent \
from the CV
- recommendations: 4-6 items — each must be a concrete CV edit the candidate can make today \
(e.g. "Under your [Role] at [Company], add a bullet quantifying [metric] to address the JD's \
requirement for [skill]") — never generic career advice
- full_analysis: 2-3 sentences covering overall fit and the single most important improvement
- Every item must reference the CV or JD specifically — no generic statements\
"""


def _keyword_match_score(cv_content: str, keywords: list[str]) -> int:
    if not keywords:
        return 0
    cv_lower = cv_content.lower()
    matched = sum(1 for kw in keywords if kw.lower() in cv_lower)
    return round((matched / len(keywords)) * 100)


def analyze_cv_match(
    cv_content: str,
    jd_description: str,
    jd_keywords: list[str],
) -> dict[str, object]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    match_score = _keyword_match_score(cv_content, jd_keywords)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    keywords_str = ", ".join(jd_keywords) if jd_keywords else "None extracted"
    user_message = (
        f"## Job Description\n{jd_description}\n\n"
        f"## Target Keywords\n{keywords_str}\n\n"
        f"## Candidate CV\n{cv_content}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
    except AuthenticationError as exc:
        raise ValueError("AI service authentication failed — check OPENAI_API_KEY") from exc
    except RateLimitError as exc:
        raise ValueError("AI service rate limit exceeded, please try again later") from exc
    except Exception as exc:
        raise ValueError(f"AI API error: {exc}") from exc

    raw = response.choices[0].message.content or ""

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI returned non-JSON response: {exc}") from exc

    return {
        "match_score": match_score,
        "strengths": list(parsed.get("strengths", [])),
        "gaps": list(parsed.get("gaps", [])),
        "recommendations": list(parsed.get("recommendations", [])),
        "full_analysis": str(parsed.get("full_analysis", "")),
    }
