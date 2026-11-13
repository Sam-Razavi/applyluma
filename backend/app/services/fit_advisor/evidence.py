"""Check that a quote really appears in the text it claims to come from."""

from __future__ import annotations

import re
import unicodedata

_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "’": "'", "‘": "'", "–": "-", "—": "-"})
_SPACE_RE = re.compile(r"\s+")
_ELLIPSIS_RE = re.compile(r"\s*(?:\.\.\.|…)\s*")
_EDGE_PUNCT = " \t\"'.,;:!?()[]-*•"

# A quote this short ("C", "AI") would match by accident almost anywhere.
MIN_QUOTE_CHARS = 2


def normalise(text: str) -> str:
    """Case, spacing and typographic variants do not make a quote wrong."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    return _SPACE_RE.sub(" ", text).strip().casefold()


def quote_in_source(quote: str, source: str) -> bool:
    """True when every part of the quote appears, in order, in the source.

    A quote may skip text with an ellipsis; each part must still be found.
    """
    haystack = normalise(source)
    parts = [part.strip(_EDGE_PUNCT) for part in _ELLIPSIS_RE.split(normalise(quote))]
    parts = [part for part in parts if part]
    if not parts or sum(len(part) for part in parts) < MIN_QUOTE_CHARS:
        return False

    position = 0
    for part in parts:
        found = haystack.find(part, position)
        if found < 0:
            return False
        position = found + len(part)
    return True
