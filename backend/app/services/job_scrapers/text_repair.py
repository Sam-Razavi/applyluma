"""Repair text whose UTF-8 bytes were read as Latin-1 before it reached us.

RemoteOK's API returns some titles, company names and descriptions in this
state: an em dash arrives as the three characters U+00E2 U+0080 U+0094 and
shows on the page as "â" followed by two invisible control characters.

A letter such as "Ä" directly followed by a sign such as "°" looks the same
as a damaged character and would be changed too. That pair is rare in English
text, so the repair is applied to RemoteOK only, never to the Swedish sources.
"""

from __future__ import annotations

import re

# A UTF-8 lead byte followed by its continuation bytes, each seen as one
# Latin-1 character. C1 control characters (U+0080 to U+009F) never occur in
# real text, so a run that also decodes as valid UTF-8 is a damaged character.
_DAMAGED = re.compile("[Â-ô][\u0080-¿]{1,3}")


def _repair(match: re.Match[str]) -> str:
    run = match.group(0)
    try:
        return run.encode("latin-1").decode("utf-8")
    except UnicodeDecodeError:
        return run


def fix_mojibake(text: str | None) -> str:
    """Return `text` with damaged characters restored; other text is untouched."""
    if not text:
        return text or ""
    return _DAMAGED.sub(_repair, text)
