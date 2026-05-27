from pathlib import Path

import pdfplumber
from docx import Document


def parse_pdf(file_path: Path) -> str:
    with pdfplumber.open(file_path) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages).strip()


def parse_docx(file_path: Path) -> str:
    doc = Document(str(file_path))
    parts: list[str] = []

    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())

    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    return "\n".join(parts).strip()


def parse_cv(file_path: Path, extension: str) -> str:
    """Parse a CV file and return its text content.

    Args:
        file_path: Path to the stored file.
        extension: Normalised extension, either '.pdf' or '.docx'.

    Raises:
        ValueError: If the extension is not supported.
        Exception: Propagates parsing errors to the caller for HTTP handling.
    """
    if extension == ".pdf":
        return parse_pdf(file_path)
    if extension == ".docx":
        return parse_docx(file_path)
    raise ValueError(f"Unsupported extension: {extension}")
