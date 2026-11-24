"""Excel copies of CSV tables."""

from __future__ import annotations

import csv
import io
from pathlib import Path


def write_xlsx(path: Path, csv_text: str) -> bool:
    """An Excel copy of a CSV table. Excel opens a UTF-8 CSV in the old Windows
    encoding (Swedish letters break) and, in a Swedish locale, expects ";" between
    columns, so the review sheet is easier to fill in as a workbook. Skipped when
    openpyxl is not installed; the CSV is the record either way."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font
    except ImportError:
        return False
    rows = list(csv.reader(io.StringIO(csv_text)))
    book = Workbook()
    sheet = book.active
    sheet.title = path.stem[:31]
    for row in rows:
        sheet.append(row)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    for index, column in enumerate(zip(*rows, strict=False), start=1):
        width = min(max((len(value) for value in column), default=8) + 2, 60)
        letter = sheet.cell(row=1, column=index).column_letter
        sheet.column_dimensions[letter].width = width
        if width == 60:
            for cell in sheet[letter][1:]:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    book.save(path)
    return True
