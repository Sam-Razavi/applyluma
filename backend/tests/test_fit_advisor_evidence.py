"""The quote check of the fit advisor (pure)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.fit_advisor.evidence import quote_in_source

CV = """Anna Lindqvist
Kandidatexamen i datavetenskap, Stockholms universitet (2023–2026)

Projekt
Byggde en webbapp i Python och Django   med PostgreSQL.
"Bästa examensarbete" – utmärkelse 2026.
B-körkort."""


def test_exact_quote_is_found() -> None:
    assert quote_in_source("Kandidatexamen i datavetenskap", CV)


def test_case_spacing_line_breaks_and_typographic_marks_do_not_matter() -> None:
    assert quote_in_source("byggde en webbapp i python och django med postgresql", CV)
    assert quote_in_source("Stockholms universitet (2023-2026)", CV)
    assert quote_in_source("“Bästa examensarbete”", CV)
    assert quote_in_source("Projekt Byggde en webbapp", CV)


def test_reworded_or_translated_quote_is_not_found() -> None:
    assert not quote_in_source("Bachelor's degree in computer science", CV)
    assert not quote_in_source("Byggde en webbapp i Java", CV)


def test_swedish_letters_are_not_folded_away() -> None:
    assert not quote_in_source("B-korkort", CV)
    assert quote_in_source("b-körkort", CV)


def test_ellipsis_joins_parts_that_must_each_appear_in_order() -> None:
    assert quote_in_source("Byggde en webbapp ... med PostgreSQL", CV)
    assert quote_in_source("Kandidatexamen … Stockholms universitet", CV)
    assert not quote_in_source("med PostgreSQL ... Byggde en webbapp", CV)
    assert not quote_in_source("Byggde en webbapp ... med MySQL", CV)


def test_empty_or_trivial_quotes_never_count() -> None:
    assert not quote_in_source("", CV)
    assert not quote_in_source("   ", CV)
    assert not quote_in_source("...", CV)
    assert not quote_in_source("a", CV)
