"""
Build the template render context from a structured CV plus the user's
accept/reject/override/order decisions from the diff-review step.

Rejected or overridden sections fall back to "raw" blocks (plain lines and
bullets) so mixed accepted/rejected output still renders in the template.
"""
import re

from app.services.cv_render.structure import GROUP_KEYS, headings_for

_BULLET_RE = re.compile(r"^[•‣◦⁃▪●○‐–—·−*-]\s+")


def _raw_lines(text: str) -> list[dict]:
    lines = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _BULLET_RE.match(line)
        if m:
            lines.append({"bullet": True, "text": line[m.end():].strip()})
        else:
            lines.append({"bullet": False, "text": line})
    return lines


def _decide(section_id: str, accepted_ids: set[str] | None, overrides: dict[str, str]) -> str:
    """Return 'override', 'accepted', or 'rejected' for a section id."""
    if section_id in overrides:
        return "override"
    if accepted_ids is None or section_id in accepted_ids:
        return "accepted"
    return "rejected"


def _entry_blocks(
    entries: list[dict],
    id_prefix: str,
    accepted_ids: set[str] | None,
    overrides: dict[str, str],
) -> list[dict]:
    out = []
    for i, entry in enumerate(entries):
        sid = f"{id_prefix}_{i}"
        decision = _decide(sid, accepted_ids, overrides)
        if decision == "accepted":
            out.append({"kind": "structured", "section_id": sid, **entry})
        elif decision == "override":
            out.append({"kind": "raw", "section_id": sid, "lines": _raw_lines(overrides[sid])})
        else:
            out.append(
                {"kind": "raw", "section_id": sid, "lines": _raw_lines(entry.get("original", ""))}
            )
    return out


def _group_order(structured: dict, section_order: list[str] | None) -> list[str]:
    """
    Resolve the order of top-level groups. `section_order` may be the user's
    per-section-id list from the save request (e.g. ["summary", "experience_0",
    ...]) or the model's group-level list; both collapse to group order here.
    """
    order: list[str] = []

    def add(key: str) -> None:
        if key in GROUP_KEYS and key not in order:
            order.append(key)

    for sid in section_order or []:
        add(re.sub(r"_\d+$", "", sid).replace("project", "projects"))
    for key in structured.get("section_order") or []:
        add(key)
    for key in GROUP_KEYS:
        add(key)
    return order


def build_render_context(
    structured: dict,
    *,
    contact_text: str = "",
    accepted_section_ids: list[str] | None = None,
    section_overrides: dict[str, str] | None = None,
    section_order: list[str] | None = None,
) -> dict:
    accepted_ids = set(accepted_section_ids) if accepted_section_ids is not None else None
    overrides = section_overrides or {}
    language = structured.get("language", "en")
    headings = headings_for(language)

    header = dict(structured.get("header") or {})
    if not header.get("full_name") and contact_text:
        header["full_name"] = contact_text.splitlines()[0].strip()
    contact_bits = [
        bit for bit in (header.get("location"), header.get("phone"), header.get("email"))
        if bit
    ]
    contact_bits.extend(link for link in header.get("links") or [] if link)
    header["contact_bits"] = contact_bits

    blocks: list[dict] = []
    for key in _group_order(structured, section_order):
        if key == "summary":
            summary = structured.get("summary") or {}
            decision = _decide("summary", accepted_ids, overrides)
            if decision == "override":
                text = overrides["summary"]
            elif decision == "accepted":
                text = summary.get("tailored", "")
            else:
                text = summary.get("original", "")
            if text.strip():
                blocks.append({"kind": "summary", "title": headings["summary"], "text": text})
        elif key == "skills":
            skills = structured.get("skills") or {}
            decision = _decide("skills", accepted_ids, overrides)
            if decision == "accepted":
                groups = [
                    g for g in skills.get("groups", [])
                    if g.get("category") or g.get("items")
                ]
                if groups:
                    blocks.append({"kind": "skills", "title": headings["skills"], "groups": groups})
            else:
                text = overrides["skills"] if decision == "override" else skills.get("original", "")
                if text.strip():
                    blocks.append(
                        {"kind": "raw", "title": headings["skills"], "lines": _raw_lines(text)}
                    )
        elif key == "experience":
            entries = _entry_blocks(
                structured.get("experience") or [], "experience", accepted_ids, overrides
            )
            if entries:
                blocks.append(
                    {"kind": "experience", "title": headings["experience"], "entries": entries}
                )
        elif key == "projects":
            entries = _entry_blocks(
                structured.get("projects") or [], "project", accepted_ids, overrides
            )
            if entries:
                blocks.append(
                    {"kind": "projects", "title": headings["projects"], "entries": entries}
                )
        elif key == "education":
            entries = _entry_blocks(
                structured.get("education") or [], "education", accepted_ids, overrides
            )
            if entries:
                blocks.append(
                    {"kind": "education", "title": headings["education"], "entries": entries}
                )
        elif key == "certifications":
            certs = structured.get("certifications") or {}
            decision = _decide("certifications", accepted_ids, overrides)
            if decision == "accepted":
                items = [i for i in certs.get("items", []) if i.get("name")]
                if items:
                    blocks.append(
                        {
                            "kind": "certifications",
                            "title": headings["certifications"],
                            "items": items,
                        }
                    )
            else:
                text = (
                    overrides["certifications"]
                    if decision == "override"
                    else certs.get("original", "")
                )
                if text.strip():
                    blocks.append(
                        {
                            "kind": "raw",
                            "title": headings["certifications"],
                            "lines": _raw_lines(text),
                        }
                    )

    for i, extra in enumerate(structured.get("additional_sections") or []):
        sid = f"additional_{i}"
        decision = _decide(sid, accepted_ids, overrides)
        if decision == "override":
            text = overrides[sid]
        elif decision == "accepted":
            text = extra.get("tailored", "")
        else:
            text = extra.get("original", "")
        if text.strip():
            blocks.append(
                {
                    "kind": "raw",
                    "title": extra.get("section_name", "Additional"),
                    "lines": _raw_lines(text),
                }
            )

    return {
        "language": language,
        "headings": headings,
        "header": header,
        "blocks": blocks,
    }


def build_cover_letter_context(
    text: str,
    *,
    title: str | None = None,
    contact_text: str = "",
    language: str = "en",
) -> dict:
    """
    Context for the cover letter templates: candidate letterhead from the CV's
    contact block, plus the letter body split into paragraphs on blank lines
    (intra-paragraph line breaks preserved).
    """
    contact_lines = [ln.strip() for ln in contact_text.splitlines() if ln.strip()]
    header = {
        "full_name": contact_lines[0] if contact_lines else "",
        "contact_bits": contact_lines[1:],
    }

    paragraphs: list[list[str]] = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if lines:
            paragraphs.append(lines)

    return {
        "language": language,
        "header": header,
        "title": (title or "").strip(),
        "paragraphs": paragraphs,
    }
