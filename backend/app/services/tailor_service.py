"""
CV tailoring service: calls OpenAI and returns a structured section-by-section diff.
"""
import json
import re

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
        "Rewrite the summary. Add or promote relevant sections. Demote or compress irrelevant ones, "
        "but do not delete projects, experience, or certifications that demonstrate the job's core "
        "required skills."
    ),
    TailorIntensity.aggressive: (
        "Rewrite every bullet for maximum keyword match and quantified impact. "
        "Restructure section order to match job-level norms. Remove sections ONLY if they are "
        "irrelevant to the target role. Never remove projects or experience that demonstrate the "
        "job's core required skills — compress them instead. Always preserve at least the 2–3 most "
        "role-relevant projects and any relevant certifications. Add a tailored summary."
    ),
}

_CONTACT_PRESERVATION_INSTRUCTION = (
    "PRESERVE ALL CONTACT INFORMATION: You MUST keep the candidate's name, email, phone "
    "number, location, LinkedIn, GitHub, portfolio URLs, and any other contact details "
    "EXACTLY as provided in the original CV. Never remove, modify, or omit contact "
    "information under any circumstances. URLs must remain fully visible as plain text "
    '(e.g. "github.com/name"), never hidden behind link text.'
)

_CONTACT_SECTION_TERMS = ("contact", "personal information", "candidate information")
_CONTACT_STOP_HEADINGS = {
    "summary",
    "profile",
    "experience",
    "work experience",
    "employment",
    "skills",
    "technical skills",
    "projects",
    "education",
}
_CONTACT_SIGNAL_RE = re.compile(
    r"@|\+?\d[\d\s().-]{6,}|linkedin|github|portfolio|https?://|www\.",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = _CONTACT_PRESERVATION_INSTRUCTION + """\

You are an expert tech resume writer and career coach. Rewrite the candidate's CV
to maximise interview chances for the specific job description provided, while
remaining truthful and ATS-parseable.

CORE RULES — NON-NEGOTIABLE
- Always include a contact information section as the FIRST section. It must contain the
  candidate's name, email, phone number, location, LinkedIn, GitHub, portfolio URLs, and
  any other contact details exactly as they appear in the source CV.
- PDF format only, single-column layout, reverse chronological, TWO PAGES MAXIMUM
  (one page is acceptable for sparse CVs).
- Active verbs, quantified bullets, and measurable impact wherever the source CV supports it.
- NEVER fabricate numbers, companies, titles, dates, credentials, employers, technologies,
  or courses.
- Mirror terminology from the job description, but only where it is truthfully supported by
  the candidate's experience.
- Use standard, ATS-recognised section headings (e.g. "Summary", "Skills", "Experience",
  "Projects", "Education", "Certifications"). Never use creative headings like "My Journey"
  or "The Toolkit".
- No self-rated skill bars, no skill-level graphics, no "References available on request",
  no photos, no icons, no tables, no multi-column layout.
- Dates: "June 2021 - July 2022" format, applied consistently. Drop the month for dates
  older than four years.
- Bold only titles, companies, and dates.
- Preserve the candidate's language and spelling conventions. The detected language is
  {detected_language}. Return the same language as the source CV unless the job description
  clearly requires a different language.

TITLE INTEGRITY
- Never alter a job title as it appeared at the employer. You may append a truthful
  parenthetical focus (e.g. "Fullstack Developer Intern (data-focused work)") but the
  actual title must remain unchanged. Do not relabel a role to match the target job.

CAREER-LEVEL SECTION ORDERING
- New graduate or junior: Summary, Skills, Projects, Experience, Education, Certifications
  - If the junior has at least one internship or professional role, Projects and Experience
    precede Education.
  - If the junior has no professional experience at all, Education (with relevant coursework)
    may move above Experience.
- Mid-level engineer: Summary, Skills, Experience, Projects, Education, Certifications
- Senior or staff engineer: Summary, Technical Leadership, Experience, Skills, Education
- Tech lead: Summary, Leadership Impact, Experience, Architecture, Skills, Education
- Engineering manager: Summary, Leadership Scope, Experience, People/Delivery Impact,
  Skills, Education
- Career changer or career break: Summary, Relevant Experience, Projects,
  Earlier Experience, Education

CONTENT-PRESERVATION RULES
- For junior CVs, the Projects section is REQUIRED and must appear in the order above.
  Never remove it.
- Never remove projects or experience that demonstrate the job's core required skills,
  even to save space — compress them instead. Always preserve the 2–3 most role-relevant
  projects.
- Preserve each project's tech-stack line and any GitHub / live-demo URLs (same protection
  class as contact info).
- Preserve a Certifications section when the source contains 2 or more certifications
  relevant to the role. Place it after Education.

SKILLS SECTION
- Reorder skills to lead with those matching the job description; do not merely truncate.
- Remove outdated or irrelevant technologies that do not apply to the target role.
- Keep concrete technologies close to the achievements that demonstrate them.

RELEVANT COURSEWORK
- Only populate a "Relevant Coursework" line if the source CV EXPLICITLY lists named courses
  or modules under a degree. Never invent, infer, or generalise course names from a degree
  title, thesis topic, or skills list.
- When present, attach coursework to the specific degree it belongs to (as a sub-line of
  that Education entry), NOT as a standalone top-level section.
- Select only courses relevant to the job description; mirror the JD's terminology only
  where the course genuinely matches. Cap at 4–6 courses, comma-separated, on a single line.
- If no named courses exist in the source, omit the line entirely. Do not output an empty
  heading.

LENGTH ENFORCEMENT
- Target two pages; one page is acceptable for sparse CVs.
- If content exceeds two pages, compress in this order: (1) trim each bullet to a single
  line, (2) reduce older or less-relevant roles to one line, (3) drop the least-relevant
  project, (4) shorten the summary.
- Never drop contact info, the most relevant project, or the most recent role to fit.
- Provide your best page estimate in meta.estimated_pages.

INTENSITY INSTRUCTION
{intensity_instruction}

SPECIAL CASES
- If there is a career break, frame it neutrally and only if the CV already mentions it.
- For technical leads, surface architecture, mentoring, delivery risk, and cross-team
  influence.
- For engineering managers, surface team size, hiring, performance, planning, and delivery
  outcomes.
- For highly technical IC roles, keep concrete technologies close to the relevant
  achievements.

OUTPUT REQUIREMENTS
- Split the CV into logical sections.
- The first section MUST be contact_information, with original and tailored values identical
  unless the source CV has no contact details.
- Include each section's original text verbatim in the "original" field. The "original" field
  is for diffing and preview ONLY and MUST NOT be rendered into the final PDF. The rendered
  PDF is built EXCLUSIVELY from "tailored" values. Never render both.
- Include a tailored rewrite for each accepted section in "tailored".
- Include "changes" as the "Changes made" explanation: what changed and why.
- If a section should be removed for the target role, return an empty "tailored" value and
  explain why in "changes". (This never applies to contact info, the required Projects
  section for juniors, or relevant certifications.)

Return ONLY a valid JSON object with this structure:
{{
  "language": "<ISO 639-1 code of the CV language, e.g. en, sv, de>",
  "sections": [
    {{
      "section_id": "<snake_case unique id, e.g. summary, experience_0, skills, education_0>",
      "section_name": "<human-readable, ATS-standard section heading>",
      "original": "<verbatim original text for this section>",
      "tailored": "<rewritten text for this section>",
      "entries": [
        {{
          "institution": "<for education entries only>",
          "degree": "<for education entries only>",
          "dates": "<for education entries only>",
          "relevant_coursework": ["<only if named courses exist in source>"]
        }}
      ],
      "changes": ["<what changed and why>", "..."]
    }}
  ],
  "meta": {{
    "keywords_added": ["<keyword added>"],
    "keywords_already_present": ["<keyword already in CV>"],
    "intensity_applied": "<light|medium|aggressive>",
    "estimated_pages": "<1|2>"
  }}
}}

Note: the "entries" array is only required for Education sections that carry per-degree
coursework; omit it for all other sections.
"""


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def _extract_contact_information(cv_content: str) -> str:
    collected: list[str] = []
    has_contact_signal = False

    for line in cv_content.splitlines():
        stripped = line.strip()
        if not stripped:
            if collected:
                break
            continue

        normalized = stripped.rstrip(":").lower()
        if collected and normalized in _CONTACT_STOP_HEADINGS:
            break

        collected.append(stripped)
        has_contact_signal = has_contact_signal or bool(_CONTACT_SIGNAL_RE.search(stripped))

    if not has_contact_signal:
        return ""
    return "\n".join(collected).strip()


def _is_contact_section(section: dict) -> bool:
    section_id = str(section.get("section_id") or "").replace("_", " ").lower()
    section_name = str(section.get("section_name") or "").lower()
    return any(term in section_id or term in section_name for term in _CONTACT_SECTION_TERMS)


def _preserve_contact_section(result: dict, cv_content: str) -> dict:
    sections = result.get("sections")
    if not isinstance(sections, list):
        result["sections"] = []
        sections = result["sections"]

    contact_text = _extract_contact_information(cv_content)
    for section in sections:
        if isinstance(section, dict) and _is_contact_section(section):
            original = contact_text or str(section.get("original") or "")
            section["section_id"] = section.get("section_id") or "contact_information"
            section["section_name"] = section.get("section_name") or "Contact Information"
            section["original"] = original
            section["tailored"] = original
            changes = section.get("changes")
            section["changes"] = changes if isinstance(changes, list) else []
            return result

    if contact_text:
        sections.insert(
            0,
            {
                "section_id": "contact_information",
                "section_name": "Contact Information",
                "original": contact_text,
                "tailored": contact_text,
                "changes": ["Preserved contact information exactly as provided."],
            },
        )
    return result


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
            max_tokens=16384,
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

    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ValueError("AI response was truncated (token limit reached)")
    raw = choice.message.content or ""
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI returned non-JSON: {exc}") from exc
    result["language"] = result.get("language") or detected_language
    return _preserve_contact_section(result, cv_content)
