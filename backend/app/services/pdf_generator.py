"""
Generate a clean single-column PDF resume from tailored section content.
"""
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

_BULLET_RE = re.compile(r"^[•‣◦⁃▪●○‐–—·‣−-]\s*")
_WHITESPACE_COLLAPSE_RE = re.compile(r"[ \t]+")
_UNICODE_DASH_RE = re.compile(r"[–—−]")
_CONTACT_SIGNAL_RE = re.compile(
    r"@|\+?\d[\d\s().-]{6,}|linkedin|github|portfolio|https?://|www\.",
    re.IGNORECASE,
)
_CONTACT_NAME_RE = re.compile(r"contact|kontakt|header|personal", re.IGNORECASE)
_ENTRY_HEADER_RE = re.compile(r".+\s-\s.+")
_DATE_LINE_RE = re.compile(
    r"^(januari|februari|mars|april|maj|juni|juli|augusti|september|"
    r"oktober|november|december|january|february|march|april|may|june|"
    r"july|august|september|october|november|december|\d{4})\b",
    re.IGNORECASE,
)


def _normalize_line(line: str) -> str:
    line = _WHITESPACE_COLLAPSE_RE.sub(" ", line).strip()
    line = _UNICODE_DASH_RE.sub("-", line)
    return line


def _render_line(line: str) -> str:
    m = _BULLET_RE.match(line)
    if m:
        rest = _UNICODE_DASH_RE.sub("-", line[m.end():])
        return "- " + escape(rest)
    line = _UNICODE_DASH_RE.sub("-", line)
    return escape(line)


def _is_contact_section(section_name: str) -> bool:
    return bool(_CONTACT_NAME_RE.search(section_name))


def _render_contact_block(content: str, styles: dict) -> list:
    story: list = []
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    if not lines:
        return story

    story.append(Paragraph(escape(lines[0]), styles["name"]))

    idx = 1
    if idx < len(lines) and not _CONTACT_SIGNAL_RE.search(lines[idx]):
        story.append(Paragraph(escape(lines[idx]), styles["title"]))
        idx += 1

    for line in lines[idx:]:
        story.append(Paragraph(escape(line), styles["detail"]))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db")))
    story.append(Spacer(1, 4))
    return story


def generate_cover_letter_pdf(
    text: str, output_path: Path, *, title: str | None = None
) -> None:
    """Render a plain-text cover letter into a clean single-column PDF."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
    )

    base_styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "ApplyLumaCoverHeading",
        parent=base_styles["Heading2"],
        fontSize=13,
        leading=17,
        spaceAfter=10,
        textColor=colors.HexColor("#1e1e2e"),
    )
    body = ParagraphStyle(
        "ApplyLumaCoverBody",
        parent=base_styles["Normal"],
        fontSize=10.5,
        leading=15,
        spaceAfter=10,
    )

    story: list = []
    if title:
        story.append(Paragraph(escape(title.strip()), heading))

    # Split on blank lines into paragraphs; keep intra-paragraph line breaks.
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [_UNICODE_DASH_RE.sub("-", ln.strip()) for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        story.append(Paragraph("<br/>".join(escape(line) for line in lines), body))

    if not story:
        story.append(Paragraph("", body))

    doc.build(story)


def generate_cv_pdf(sections: list[dict], output_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    base_styles = getSampleStyleSheet()

    heading = ParagraphStyle(
        "ApplyLumaHeading",
        parent=base_styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceAfter=3,
        spaceBefore=8,
        textColor=colors.HexColor("#1e1e2e"),
    )
    body = ParagraphStyle(
        "ApplyLumaBody",
        parent=base_styles["Normal"],
        fontSize=9.5,
        leading=13,
        spaceAfter=2,
    )
    bullet = ParagraphStyle(
        "ApplyLumaBullet",
        parent=body,
        leftIndent=14,
        bulletIndent=0,
    )
    subheading = ParagraphStyle(
        "ApplyLumaSubheading",
        parent=body,
        fontName="Helvetica-Bold",
        spaceBefore=6,
        spaceAfter=1,
    )
    date_style = ParagraphStyle(
        "ApplyLumaDate",
        parent=body,
        textColor=colors.HexColor("#4b5563"),
        fontSize=9,
        spaceAfter=2,
    )

    contact_styles = {
        "name": ParagraphStyle(
            "ApplyLumaName",
            parent=base_styles["Title"],
            fontSize=16,
            leading=20,
            spaceAfter=1,
            spaceBefore=0,
            textColor=colors.HexColor("#111827"),
        ),
        "title": ParagraphStyle(
            "ApplyLumaTitle",
            parent=body,
            fontSize=10.5,
            leading=14,
            spaceAfter=2,
            textColor=colors.HexColor("#4b5563"),
        ),
        "detail": ParagraphStyle(
            "ApplyLumaContactDetail",
            parent=body,
            fontSize=9,
            leading=12,
            spaceAfter=1,
            textColor=colors.HexColor("#6b7280"),
        ),
    }

    story: list = []
    last_heading: str | None = None

    for section in sections:
        section_name = (section.get("section_name") or "").strip()
        content = (section.get("content") or "").strip()
        if not content:
            continue

        if _is_contact_section(section_name):
            story.extend(_render_contact_block(content, contact_styles))
            last_heading = section_name
            continue

        if section_name and section_name != last_heading:
            story.append(Paragraph(escape(section_name), heading))
            story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#e5e7eb")))
            last_heading = section_name

        for raw_line in content.splitlines():
            line = _normalize_line(raw_line)
            if not line:
                continue
            is_bullet = bool(_BULLET_RE.match(line))
            if is_bullet:
                text = _render_line(line)
                story.append(Paragraph(text, bullet))
            elif _ENTRY_HEADER_RE.match(line) and not _DATE_LINE_RE.match(line):
                story.append(Paragraph(escape(line), subheading))
            elif _DATE_LINE_RE.match(line):
                story.append(Paragraph(escape(line), date_style))
            else:
                text = _render_line(line)
                story.append(Paragraph(text, body))

        story.append(Spacer(1, 4))

    doc.build(story)
