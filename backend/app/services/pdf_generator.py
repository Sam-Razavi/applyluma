"""
Generate a clean single-column PDF resume from tailored section content.
"""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer


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

    story = []
    for section in sections:
        section_name = (section.get("section_name") or "").strip()
        if section_name:
            story.append(Paragraph(escape(section_name), heading))
            story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#e5e7eb")))
        for line in (section.get("content") or "").splitlines():
            line = line.strip()
            if line:
                story.append(Paragraph(escape(line), body))
        story.append(Spacer(1, 6))

    doc.build(story)
