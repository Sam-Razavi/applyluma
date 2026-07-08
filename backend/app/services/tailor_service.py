"""
CV tailoring service: calls OpenAI with a strict Structured Outputs schema and
returns typed CV content plus a section-by-section diff derived from it.

The model generates CONTENT ONLY; all layout and styling live in the fixed
HTML/CSS templates under app/services/cv_render/templates/.
"""
import json
import re

from langdetect import LangDetectException, detect
from openai import AuthenticationError, OpenAI, RateLimitError

from app.core.config import settings
from app.models.tailor_job import TailorIntensity
from app.services import cv_render

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
        "Aggressively reword and restructure the candidate's REAL content. Rewrite every bullet "
        "with strong active verbs, leading with the achievements and keywords that ALREADY appear "
        "in the source CV. Quantify impact ONLY where the source CV already states the numbers — "
        "never invent or estimate metrics, percentages, scale, or outcomes. "
        "Restructure section order to match job-level norms. Remove sections ONLY if they are "
        "irrelevant to the target role. Never remove projects or experience that demonstrate the "
        "job's core required skills — compress them instead. Always preserve at least the 2–3 most "
        "role-relevant projects and any relevant certifications. Add a tailored summary drawn "
        "strictly from the candidate's actual background. Aggressive means bolder rewording and "
        "reordering of real material — never adding skills, technologies, facts, or numbers the "
        "candidate did not provide."
    ),
}

_CONTACT_PRESERVATION_INSTRUCTION = (
    "PRESERVE ALL CONTACT INFORMATION: You MUST keep the candidate's name, email, phone "
    "number, location, LinkedIn, GitHub, portfolio URLs, and any other contact details "
    "EXACTLY as provided in the original CV in the header object. Never remove, modify, "
    "or invent contact information under any circumstances. URLs must be written as plain "
    'text (e.g. "github.com/name"), never as link labels.'
)

_CONTACT_SECTION_TERMS = (
    "contact",
    "personal information",
    "candidate information",
    "personal details",
    "header",
    "kontakt",
    "personuppgifter",
    "kontaktuppgifter",
    "kontaktinformation",
)
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
    "sammanfattning",
    "profil",
    "erfarenhet",
    "arbetslivserfarenhet",
    "anstallning",
    "kompetenser",
    "tekniska kompetenser",
    "fardigheter",
    "projekt",
    "utbildning",
}
_CONTACT_SIGNAL_RE = re.compile(
    r"@|\+?\d[\d\s().-]{6,}|linkedin|github|portfolio|https?://|www\.",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = _CONTACT_PRESERVATION_INSTRUCTION + """\


You are ApplyLuma's CV tailoring engine: an expert tech resume writer and career
coach. From a candidate CV and a job description, produce highly tailored,
truthful, ATS-friendly STRUCTURED CV CONTENT that maximises interview chances.

You generate CONTENT ONLY. A fixed professional template (Nordic design: navy
header, teal accents, clean A4, selectable text) renders your JSON. Do not emit
HTML, CSS, markdown, tables, emojis, or decorative symbols. Never use markdown
formatting such as **bold** inside any string value.

ROLE ANALYSIS — do this silently before writing:
1. Identify the role title, seniority, language, company, and industry.
2. Extract the most important requirements and rank them: essential, preferred,
   nice-to-have, personal qualities.
3. Map each requirement to concrete evidence in the candidate CV.
4. Build the CV around the strongest supported evidence; identify unsupported
   requirements and emphasise adjacent, transferable evidence instead of lying.

LANGUAGE RULE
- The candidate CV language is {cv_language}; the job description language is
  {jd_language}. Write ALL output in the job description's language (Swedish JD
  → fully Swedish CV; English JD → fully English CV). Never mix languages in
  the same document. Keep technology names in their original form.

TRUTH AND ACCURACY — NON-NEGOTIABLE, overrides everything else
- NEVER fabricate numbers, metrics, employers, job titles, dates, credentials,
  degrees, languages, clients, team sizes, user counts, or achievements.
- NEVER ADD any skill, technology, tool, programming language, framework,
  library, platform, or certification that does not EXPLICITLY appear in the
  source CV. If the job description asks for a technology the candidate did not
  list, do NOT add it anywhere. Omission is correct; fabrication is
  disqualifying.
- Mirror terminology from the job description ONLY for skills and experience
  that already exist in the source CV. Synonyms are fine ("JS" → "JavaScript");
  entirely new technologies are not.
- Internships stay labelled as internships; academic work stays academic;
  personal projects stay projects and are never presented as employment.
- Never claim "expert", "senior", "extensive", or years of experience unless
  explicitly supported. Never present an ongoing degree as completed.
- TITLE INTEGRITY: never alter a job title as it appeared at the employer. You
  may append a truthful parenthetical focus, but never relabel a role to match
  the target job.

HEADER
- full_name, location, phone, email, links: copy EXACTLY from the source CV;
  use null for anything not present. Never invent.
- target_headline: role-targeted and evidence-supported, e.g.
  "Junior Full-Stack Developer | React, TypeScript & Node.js". Never more
  senior than the candidate's evidence supports.

SUMMARY (55–85 words)
- Specific to the target role; lead with the strongest relevant tools and
  experience. No first person, no generic motivational phrases, no unsupported
  years of experience, no repetition of the headline.

SKILLS (4–6 groups, 3–8 items each)
- Group by theme (e.g. Languages / Frontend / Backend & APIs / Databases /
  Testing & Quality / Cloud, DevOps & Tools). Category names in the output
  language.
- Every item must appear in the source CV. Lead each group with the items that
  match the job description. Do not dump every technology the candidate ever
  touched — select for relevance.

EXPERIENCE
- Most relevant roles first within truthful reverse-chronological blocks.
- 2–4 bullets per role, each 12–28 words, starting with a strong action verb.
- Include technologies, scope, collaboration, outcomes, and user value where
  the source supports them. No generic filler ("worked on various tasks").
- Dates in "June 2021 - July 2022" style, consistently; drop the month for
  dates older than four years.

PROJECTS
- ALL projects from the source CV must appear — never drop one. Order them by
  relevance to the role. 2–4 bullets each; compress the least relevant instead
  of deleting.
- Preserve each project's tech stack and any GitHub / live-demo URLs exactly
  (same protection class as contact info).

EDUCATION
- ALL education entries from the source must appear, with thesis titles, dates,
  and credits preserved. Mark ongoing degrees clearly ("In progress" /
  "Pågående").
- relevant_coursework: ONLY courses explicitly named in the source CV, capped
  at 4–6, chosen for relevance. Never infer courses from a degree title. Leave
  the array empty if the source names none.

CERTIFICATIONS
- Only certifications present in the source; keep the ones relevant to the
  role. Low-value certificates only when the role is junior and evidence is
  thin.

ADDITIONAL SECTIONS
- Source content that fits no typed section (spoken languages, volunteering,
  awards) goes into additional_sections so it is never silently lost. Drop a
  section entirely only when it is clearly irrelevant to the target role.

SECTION ORDER (career-level norms)
- Junior / new graduate: summary, skills, projects, experience, education,
  certifications (education before experience only if there is no professional
  experience at all).
- Mid-level and above: summary, skills, experience, projects, education,
  certifications.

LENGTH
- Target a maximum of two A4 pages; one page is fine for sparse CVs. Never pad.
- If content is long, compress in this order: trim bullets to one line, reduce
  older roles to fewer bullets, shorten the summary. Never drop projects,
  education entries, or the most recent role.

INTENSITY
The truth rules above ALWAYS override this setting; higher intensity means
bolder rewording and restructuring of REAL content, never more factual licence.
{intensity_instruction}

ORIGINAL FIELDS (for the review diff — required)
- Every "original" field must contain the verbatim source-CV text for that
  part (the matching entry or section). It is shown to the user in a
  before/after diff and never rendered into the final document.
- "changes" lists what changed in that part and why, in the output language.

SILENT QUALITY CHECK before answering: output language matches the job
description; every claim is traceable to the source CV; no invented skills,
numbers, or courses; all projects and education entries present; summary is
55–85 words; bullets start with action verbs; contact details copied exactly.
"""

_COMPRESS_PROMPT = """\
The rendered CV exceeds two A4 pages. Reduce it without losing its strongest \
evidence, and return the SAME JSON schema:
- Keep the professional summary, but shorten it.
- Shorten bullets to one line each; cut the weakest bullet from older or less \
relevant roles.
- Remove skill items not relevant to this job description (never add new ones).
- Keep ALL projects and ALL education entries, but compress the least relevant \
to their strongest 1–2 bullets.
- Do not remove truthful evidence that directly matches an essential job \
requirement. Do not change the language. Do not alter contact details.
"""


def _detect_language(text: str) -> str:
    try:
        return detect(text)
    except LangDetectException:
        return "en"


_CID_RE = re.compile(r"\(cid:\d+\)")

_MAX_CONTACT_LINES = 12


def _extract_contact_information(cv_content: str) -> str:
    cv_content = _CID_RE.sub("", cv_content)

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

        if len(collected) >= _MAX_CONTACT_LINES:
            break

    if not has_contact_signal:
        return ""
    return "\n".join(collected).strip()


def _is_contact_section(section: dict) -> bool:
    section_id = str(section.get("section_id") or "").replace("_", " ").lower()
    section_name = str(section.get("section_name") or "").lower()
    return any(term in section_id or term in section_name for term in _CONTACT_SECTION_TERMS)


_SKILL_TOKEN_RE = re.compile(r"[^a-z0-9+#]+")


def _source_skill_slugs(cv_content: str) -> set[str]:
    """Slugs of every 1–3 consecutive source tokens, to tolerate punctuation
    variants ("Node.js" vs "Node js", "CI/CD" vs "CI CD") without letting a
    fabricated "Java" match inside "JavaScript"."""
    tokens = [t for t in _SKILL_TOKEN_RE.split(cv_content.lower()) if t]
    slugs: set[str] = set()
    for n in (1, 2, 3):
        for i in range(len(tokens) - n + 1):
            slugs.add("".join(tokens[i:i + n]))
    return slugs


def _skill_present_in_source(skill: str, source_lower: str, source_slugs: set[str]) -> bool:
    skill = skill.strip().lower()
    if not skill:
        return False
    pattern = re.compile(r"(?<![a-z])" + re.escape(skill) + r"(?![a-z])", re.IGNORECASE)
    if pattern.search(source_lower):
        return True
    slug = _SKILL_TOKEN_RE.sub("", skill)
    return bool(slug) and slug in source_slugs


def _remove_fabricated_skills(structured: dict, cv_content: str) -> list[str]:
    """Drop skill and stack items that do not appear in the source CV."""
    source_lower = cv_content.lower()
    source_slugs = _source_skill_slugs(cv_content)
    removed: list[str] = []

    skills = structured.get("skills") or {}
    kept_groups = []
    for group in skills.get("groups", []):
        kept_items = []
        for item in group.get("items", []):
            if _skill_present_in_source(item, source_lower, source_slugs):
                kept_items.append(item)
            else:
                removed.append(item)
        if kept_items:
            kept_groups.append({**group, "items": kept_items})
    if skills:
        skills["groups"] = kept_groups

    for project in structured.get("projects") or []:
        kept_stack = []
        for item in project.get("stack", []):
            if _skill_present_in_source(item, source_lower, source_slugs):
                kept_stack.append(item)
            else:
                removed.append(item)
        project["stack"] = kept_stack

    if removed and isinstance(skills.get("changes"), list):
        skills["changes"].append(
            "Removed skills not present in the source CV: " + ", ".join(sorted(set(removed)))
        )
    return removed


_PHONE_STRIP_RE = re.compile(r"[^\d+]")
_LINK_STRIP_RE = re.compile(r"^https?://(www\.)?|/$", re.IGNORECASE)


def _validate_header(structured: dict, cv_content: str) -> None:
    """Drop header contact fields that cannot be found in the source CV."""
    header = structured.get("header")
    if not isinstance(header, dict):
        return
    source_lower = cv_content.lower()

    email = (header.get("email") or "").strip()
    if email and email.lower() not in source_lower:
        header["email"] = None

    phone = (header.get("phone") or "").strip()
    if phone:
        digits = _PHONE_STRIP_RE.sub("", phone).lstrip("+")
        source_digits = _PHONE_STRIP_RE.sub("", cv_content)
        if not digits or digits not in source_digits:
            header["phone"] = None

    kept_links = []
    source_slim = _LINK_STRIP_RE.sub("", source_lower)
    for link in header.get("links") or []:
        slim = _LINK_STRIP_RE.sub("", link.strip().lower())
        if slim and slim in source_slim:
            kept_links.append(link)
    header["links"] = kept_links


def _parse_structured(raw: str) -> dict:
    try:
        structured = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI returned non-JSON: {exc}") from exc
    if not isinstance(structured, dict):
        raise ValueError("OpenAI returned JSON that is not an object")
    return structured


def _call_openai(client: OpenAI, messages: list[dict]) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=16384,
            response_format={"type": "json_schema", "json_schema": cv_render.CV_RESPONSE_SCHEMA},
            messages=messages,
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
    if getattr(choice.message, "refusal", None):
        raise ValueError(f"AI refused the request: {choice.message.refusal}")
    return choice.message.content or ""


def _postprocess(structured: dict, cv_content: str, fallback_language: str) -> dict:
    structured["language"] = structured.get("language") or fallback_language
    _validate_header(structured, cv_content)
    _remove_fabricated_skills(structured, cv_content)
    return structured


def _probe_page_count(structured: dict, contact_text: str) -> int | None:
    if not cv_render.is_available():
        return None
    try:
        context = cv_render.build_render_context(structured, contact_text=contact_text)
        return cv_render.count_pages(context)
    except Exception:
        return None


def tailor_cv(
    cv_content: str,
    jd_description: str,
    jd_keywords: list[str],
    intensity: TailorIntensity,
) -> dict:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured")

    cv_language = _detect_language(cv_content)
    jd_language = _detect_language(jd_description)
    system_prompt = _SYSTEM_PROMPT.format(
        intensity_instruction=_INTENSITY_INSTRUCTIONS[intensity],
        cv_language=cv_language,
        jd_language=jd_language,
    )
    keywords_str = ", ".join(jd_keywords) if jd_keywords else "None extracted"
    user_message = (
        f"Job Description\n{jd_description}\n\n"
        f"Target Keywords\n{keywords_str}\n\n"
        f"Candidate CV\n{cv_content}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0)
    raw = _call_openai(client, messages)
    structured = _postprocess(_parse_structured(raw), cv_content, jd_language)

    contact_text = _extract_contact_information(cv_content)

    # Length enforcement: render a probe PDF; if it exceeds two pages, ask the
    # model once to compress, and keep the compressed version when it is shorter.
    pages = _probe_page_count(structured, contact_text)
    if pages is not None and pages > 2:
        retry_messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": _COMPRESS_PROMPT},
        ]
        try:
            compressed_raw = _call_openai(client, retry_messages)
            compressed = _postprocess(
                _parse_structured(compressed_raw), cv_content, jd_language
            )
            compressed_pages = _probe_page_count(compressed, contact_text)
            if compressed_pages is not None and compressed_pages < pages:
                structured, pages = compressed, compressed_pages
        except ValueError:
            pass  # keep the uncompressed result rather than failing the job

    meta = structured.setdefault("meta", {})
    meta.setdefault("intensity_applied", intensity.value)
    if pages is not None:
        meta["rendered_pages"] = pages

    return {
        "language": structured["language"],
        "sections": cv_render.structured_to_sections(structured, contact_text),
        "structured_cv": structured,
        "meta": meta,
    }
