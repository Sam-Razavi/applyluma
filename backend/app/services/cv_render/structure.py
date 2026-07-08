"""
Structured CV contract: the OpenAI Structured Outputs schema for tailored CV
content, plus converters from the structured form to the legacy section list
consumed by the diff-review UI and to plain text.
"""
from typing import Any

_CHANGES = {"type": "array", "items": {"type": "string"}}
_STR_ARRAY = {"type": "array", "items": {"type": "string"}}
_NULLABLE_STR = {"type": ["string", "null"]}

CV_RESPONSE_SCHEMA: dict[str, Any] = {
    "name": "tailored_cv",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "language",
            "header",
            "summary",
            "skills",
            "experience",
            "projects",
            "education",
            "certifications",
            "additional_sections",
            "section_order",
            "meta",
        ],
        "properties": {
            "language": {
                "type": "string",
                "description": "ISO 639-1 code of the output language, e.g. en, sv",
            },
            "header": {
                "type": "object",
                "additionalProperties": False,
                "required": ["full_name", "target_headline", "location", "phone", "email", "links"],
                "properties": {
                    "full_name": {"type": "string"},
                    "target_headline": {
                        "type": "string",
                        "description": "Role-targeted headline, e.g. 'Junior Full-Stack Developer | React, TypeScript & Node.js'",
                    },
                    "location": _NULLABLE_STR,
                    "phone": _NULLABLE_STR,
                    "email": _NULLABLE_STR,
                    "links": {
                        "type": "array",
                        "description": "LinkedIn/GitHub/portfolio URLs exactly as in the source CV",
                        "items": {"type": "string"},
                    },
                },
            },
            "summary": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tailored", "original", "changes"],
                "properties": {
                    "tailored": {"type": "string"},
                    "original": {"type": "string"},
                    "changes": _CHANGES,
                },
            },
            "skills": {
                "type": "object",
                "additionalProperties": False,
                "required": ["groups", "original", "changes"],
                "properties": {
                    "groups": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["category", "items"],
                            "properties": {
                                "category": {"type": "string"},
                                "items": _STR_ARRAY,
                            },
                        },
                    },
                    "original": {"type": "string"},
                    "changes": _CHANGES,
                },
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "title", "company", "location", "dates",
                        "bullets", "original", "changes",
                    ],
                    "properties": {
                        "title": {"type": "string"},
                        "company": {"type": "string"},
                        "location": _NULLABLE_STR,
                        "dates": {"type": "string"},
                        "bullets": _STR_ARRAY,
                        "original": {"type": "string"},
                        "changes": _CHANGES,
                    },
                },
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "name", "subtitle", "url", "stack",
                        "bullets", "original", "changes",
                    ],
                    "properties": {
                        "name": {"type": "string"},
                        "subtitle": _NULLABLE_STR,
                        "url": _NULLABLE_STR,
                        "stack": _STR_ARRAY,
                        "bullets": _STR_ARRAY,
                        "original": {"type": "string"},
                        "changes": _CHANGES,
                    },
                },
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "degree", "institution", "dates", "details",
                        "relevant_coursework", "original", "changes",
                    ],
                    "properties": {
                        "degree": {"type": "string"},
                        "institution": {"type": "string"},
                        "dates": {"type": "string"},
                        "details": _NULLABLE_STR,
                        "relevant_coursework": _STR_ARRAY,
                        "original": {"type": "string"},
                        "changes": _CHANGES,
                    },
                },
            },
            "certifications": {
                "type": "object",
                "additionalProperties": False,
                "required": ["items", "original", "changes"],
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "issuer", "date"],
                            "properties": {
                                "name": {"type": "string"},
                                "issuer": _NULLABLE_STR,
                                "date": _NULLABLE_STR,
                            },
                        },
                    },
                    "original": {"type": "string"},
                    "changes": _CHANGES,
                },
            },
            "additional_sections": {
                "type": "array",
                "description": "Source-CV sections that fit no typed section (languages, volunteering, awards, ...)",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["section_name", "tailored", "original", "changes"],
                    "properties": {
                        "section_name": {"type": "string"},
                        "tailored": {"type": "string"},
                        "original": {"type": "string"},
                        "changes": _CHANGES,
                    },
                },
            },
            "section_order": {
                "type": "array",
                "description": "Career-level-appropriate order of the main sections",
                "items": {
                    "type": "string",
                    "enum": [
                        "summary", "skills", "experience",
                        "projects", "education", "certifications",
                    ],
                },
            },
            "meta": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "keywords_added",
                    "keywords_already_present",
                    "intensity_applied",
                    "estimated_pages",
                ],
                "properties": {
                    "keywords_added": _STR_ARRAY,
                    "keywords_already_present": _STR_ARRAY,
                    "intensity_applied": {
                        "type": "string",
                        "enum": ["light", "medium", "aggressive"],
                    },
                    "estimated_pages": {"type": "integer"},
                },
            },
        },
    },
}

GROUP_KEYS = ("summary", "skills", "experience", "projects", "education", "certifications")

_HEADINGS: dict[str, dict[str, str]] = {
    "en": {
        "contact": "Contact Information",
        "summary": "Summary",
        "skills": "Skills",
        "experience": "Experience",
        "projects": "Projects",
        "education": "Education",
        "certifications": "Certifications",
    },
    "sv": {
        "contact": "Kontaktuppgifter",
        "summary": "Sammanfattning",
        "skills": "Kompetenser",
        "experience": "Erfarenhet",
        "projects": "Projekt",
        "education": "Utbildning",
        "certifications": "Certifieringar",
    },
}


def headings_for(language: str) -> dict[str, str]:
    return _HEADINGS.get((language or "en").lower()[:2], _HEADINGS["en"])


def _join_nonempty(parts: list[str | None], sep: str) -> str:
    return sep.join(p for p in (part.strip() if part else "" for part in parts) if p)


def skills_text(skills: dict[str, Any]) -> str:
    lines = []
    for group in skills.get("groups", []):
        items = ", ".join(i for i in group.get("items", []) if i)
        if items:
            lines.append(f"{group.get('category', '').strip()}: {items}".lstrip(": "))
    return "\n".join(lines)


def experience_entry_text(entry: dict[str, Any]) -> str:
    lines = [_join_nonempty([entry.get("title"), entry.get("company")], " - ")]
    date_line = _join_nonempty([entry.get("dates"), entry.get("location")], " | ")
    if date_line:
        lines.append(date_line)
    lines.extend(f"• {b}" for b in entry.get("bullets", []) if b)
    return "\n".join(line for line in lines if line)


def project_entry_text(entry: dict[str, Any]) -> str:
    lines = [_join_nonempty([entry.get("name"), entry.get("subtitle")], " - ")]
    if entry.get("url"):
        lines.append(str(entry["url"]))
    lines.extend(f"• {b}" for b in entry.get("bullets", []) if b)
    stack = ", ".join(s for s in entry.get("stack", []) if s)
    if stack:
        lines.append(f"Tech: {stack}")
    return "\n".join(line for line in lines if line)


def education_entry_text(entry: dict[str, Any]) -> str:
    lines = [_join_nonempty([entry.get("degree"), entry.get("institution")], " - ")]
    if entry.get("dates"):
        lines.append(str(entry["dates"]))
    if entry.get("details"):
        lines.append(str(entry["details"]))
    coursework = ", ".join(c for c in entry.get("relevant_coursework", []) if c)
    if coursework:
        lines.append(f"Relevant coursework: {coursework}")
    return "\n".join(line for line in lines if line)


def certification_item_text(item: dict[str, Any]) -> str:
    head = _join_nonempty([item.get("name"), item.get("issuer")], " - ")
    if item.get("date"):
        return f"{head} ({item['date']})"
    return head


def certifications_text(certifications: dict[str, Any]) -> str:
    return "\n".join(
        certification_item_text(item)
        for item in certifications.get("items", [])
        if item.get("name")
    )


def structured_to_sections(structured: dict[str, Any], contact_text: str) -> list[dict[str, Any]]:
    """
    Derive the legacy `sections` list (the diff-review contract) from the
    structured CV, so the existing preview/accept/reject UI keeps working.
    """
    headings = headings_for(structured.get("language", "en"))
    sections: list[dict[str, Any]] = []

    if contact_text:
        sections.append(
            {
                "section_id": "contact_information",
                "section_name": headings["contact"],
                "original": contact_text,
                "tailored": contact_text,
                "changes": ["Preserved contact information exactly as provided."],
            }
        )

    order = structured.get("section_order") or list(GROUP_KEYS)
    for key in GROUP_KEYS:
        if key not in order:
            order.append(key)

    for key in order:
        if key == "summary":
            summary = structured.get("summary") or {}
            if summary.get("tailored") or summary.get("original"):
                sections.append(
                    {
                        "section_id": "summary",
                        "section_name": headings["summary"],
                        "original": summary.get("original", ""),
                        "tailored": summary.get("tailored", ""),
                        "changes": summary.get("changes", []),
                    }
                )
        elif key == "skills":
            skills = structured.get("skills") or {}
            text = skills_text(skills)
            if text or skills.get("original"):
                sections.append(
                    {
                        "section_id": "skills",
                        "section_name": headings["skills"],
                        "original": skills.get("original", ""),
                        "tailored": text,
                        "changes": skills.get("changes", []),
                    }
                )
        elif key == "experience":
            for i, entry in enumerate(structured.get("experience") or []):
                sections.append(
                    {
                        "section_id": f"experience_{i}",
                        "section_name": headings["experience"],
                        "original": entry.get("original", ""),
                        "tailored": experience_entry_text(entry),
                        "changes": entry.get("changes", []),
                    }
                )
        elif key == "projects":
            for i, entry in enumerate(structured.get("projects") or []):
                sections.append(
                    {
                        "section_id": f"project_{i}",
                        "section_name": headings["projects"],
                        "original": entry.get("original", ""),
                        "tailored": project_entry_text(entry),
                        "changes": entry.get("changes", []),
                    }
                )
        elif key == "education":
            for i, entry in enumerate(structured.get("education") or []):
                sections.append(
                    {
                        "section_id": f"education_{i}",
                        "section_name": headings["education"],
                        "original": entry.get("original", ""),
                        "tailored": education_entry_text(entry),
                        "changes": entry.get("changes", []),
                    }
                )
        elif key == "certifications":
            certs = structured.get("certifications") or {}
            text = certifications_text(certs)
            if text or certs.get("original"):
                sections.append(
                    {
                        "section_id": "certifications",
                        "section_name": headings["certifications"],
                        "original": certs.get("original", ""),
                        "tailored": text,
                        "changes": certs.get("changes", []),
                    }
                )

    for i, extra in enumerate(structured.get("additional_sections") or []):
        sections.append(
            {
                "section_id": f"additional_{i}",
                "section_name": extra.get("section_name", "Additional"),
                "original": extra.get("original", ""),
                "tailored": extra.get("tailored", ""),
                "changes": extra.get("changes", []),
            }
        )

    return sections
