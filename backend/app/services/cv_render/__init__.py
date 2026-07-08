"""
Structured CV rendering: typed CV content -> HTML template -> PDF.

The model produces structured content only (see structure.CV_RESPONSE_SCHEMA);
all layout and styling live in the fixed HTML/CSS templates in templates/.
"""
from app.services.cv_render.context import build_cover_letter_context, build_render_context
from app.services.cv_render.renderer import (
    COVER_TEMPLATES,
    DEFAULT_TEMPLATE,
    TEMPLATES,
    count_pages,
    is_available,
    render_cover_letter_html,
    render_cover_letter_pdf,
    render_html,
    render_pdf,
)
from app.services.cv_render.structure import (
    CV_RESPONSE_SCHEMA,
    headings_for,
    structured_to_sections,
)

__all__ = [
    "COVER_TEMPLATES",
    "CV_RESPONSE_SCHEMA",
    "DEFAULT_TEMPLATE",
    "TEMPLATES",
    "build_cover_letter_context",
    "build_render_context",
    "count_pages",
    "headings_for",
    "is_available",
    "render_cover_letter_html",
    "render_cover_letter_pdf",
    "render_html",
    "render_pdf",
    "structured_to_sections",
]
