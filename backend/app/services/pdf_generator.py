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


def generate_cv_pdf(sections: list[dict], output_path: Path) -> None:
    """
    sections: list of {"section_name": str, "content": str}
    """
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "ApplyLumaHeading",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        spaceAfter=4,
        spaceBefore=10,
        textColor=colors.HexColor("#1e1e2e"),
    )
    body = ParagraphStyle(
        "ApplyLumaBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=14,
        spaceAfter=2,
    )
    bullet = ParagraphStyle(
        "ApplyLumaBullet",
        parent=body,
        leftIndent=12,
        bulletIndent=0,
    )

    story: list = []
    last_heading: str | None = None
    for section in sections:
        section_name = (section.get("section_name") or "").strip()
        content = (section.get("content") or "").strip()
        if not content:
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
            text = _render_line(line)
            story.append(Paragraph(text, bullet if is_bullet else body))
        story.append(Spacer(1, 6))

    doc.build(story)
