"""
Render a CV context into HTML (Jinja2) and PDF (WeasyPrint).

WeasyPrint needs native Pango libraries that are present in the production
Docker image but typically missing on Windows dev machines, so it is imported
lazily; callers use is_available() and fall back to the legacy ReportLab
renderer when it is False.
"""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"

TEMPLATES: dict[str, str] = {
    "nordic": "nordic.html",
    "classic": "classic.html",
}
COVER_TEMPLATES: dict[str, str] = {
    "nordic": "cover_nordic.html",
    "classic": "cover_classic.html",
}
DEFAULT_TEMPLATE = "nordic"


@lru_cache(maxsize=1)
def _jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


@lru_cache(maxsize=1)
def _weasyprint() -> Any:
    try:
        import weasyprint
        return weasyprint
    except Exception as exc:  # pragma: no cover - depends on native libs
        logger.warning("WeasyPrint unavailable, falling back to legacy renderer: %s", exc)
        return None


def is_available() -> bool:
    return _weasyprint() is not None


def render_html(context: dict[str, Any], template_id: str = DEFAULT_TEMPLATE) -> str:
    template_file = TEMPLATES.get(template_id) or TEMPLATES[DEFAULT_TEMPLATE]
    return _jinja_env().get_template(template_file).render(**context)


def _render_document(context: dict[str, Any], template_id: str) -> Any:
    weasyprint = _weasyprint()
    if weasyprint is None:
        raise RuntimeError("WeasyPrint is not available in this environment")
    html = render_html(context, template_id)
    return weasyprint.HTML(string=html, base_url=str(_TEMPLATE_DIR)).render()


def count_pages(context: dict[str, Any], template_id: str = DEFAULT_TEMPLATE) -> int:
    return len(_render_document(context, template_id).pages)


def render_pdf(
    context: dict[str, Any], output_path: Path, template_id: str = DEFAULT_TEMPLATE
) -> int:
    """Write the PDF and return its page count."""
    document = _render_document(context, template_id)
    document.write_pdf(str(output_path))
    return len(document.pages)


def render_cover_letter_html(context: dict[str, Any], template_id: str = DEFAULT_TEMPLATE) -> str:
    template_file = COVER_TEMPLATES.get(template_id) or COVER_TEMPLATES[DEFAULT_TEMPLATE]
    return _jinja_env().get_template(template_file).render(**context)


def render_cover_letter_pdf(
    context: dict[str, Any], output_path: Path, template_id: str = DEFAULT_TEMPLATE
) -> int:
    weasyprint = _weasyprint()
    if weasyprint is None:
        raise RuntimeError("WeasyPrint is not available in this environment")
    html = render_cover_letter_html(context, template_id)
    document = weasyprint.HTML(string=html, base_url=str(_TEMPLATE_DIR)).render()
    document.write_pdf(str(output_path))
    return len(document.pages)
