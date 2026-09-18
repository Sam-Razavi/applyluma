"""Work out what a recruiter email is saying about an application.

Pure, like the matcher: no database, no network, no model call. Classification
decides whether a user is asked to move an application's status, so it has to
be cheap to reason about and cheap to test against real phrasings.

Deliberately keyword-based for now. Rejections and interview invitations are
highly formulaic, so patterns cover most real mail without an LLM call, and
starting here means the admin view shows how far that actually gets before
paying for a model. Ambiguous mail returns None rather than guessing — the
follow-up is to send exactly those to an LLM.

Swedish is a first-class case, not an afterthought: the user base is
Sweden-heavy and "Tyvärr gick du inte vidare" is as common as "unfortunately".

Matching is on whole phrases within a sentence, never bare substrings, and the
sentence that triggered the decision is returned as evidence — a suggestion the
user cannot see the basis for is one they cannot sensibly accept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Sentence-ish split. Newlines count: email bodies use them as sentence breaks
# far more freely than prose does.
_SENTENCE_SPLIT = re.compile(r"[.!?\n\r]+")
_WHITESPACE = re.compile(r"\s+")

# Confidence per signal. Below _SUGGEST_THRESHOLD the classification is
# recorded but no suggestion is raised, mirroring how the matcher keeps its
# near-misses visible without acting on them.
SUGGEST_THRESHOLD = 70

_SCORE_DECISIVE = 90
_SCORE_STRONG = 75
_SCORE_WEAK = 50

# Phrases that settle it. Ordered by how unambiguous they are, not alphabetically.
_REJECTION_PHRASES: tuple[str, ...] = (
    # English
    "we regret to inform",
    "not moving forward",
    "not be moving forward",
    "will not be proceeding",
    "decided not to proceed",
    "decided to move forward with other",
    "proceed with other candidates",
    "chosen another candidate",
    "selected another candidate",
    "unsuccessful on this occasion",
    "your application was not successful",
    "not been selected",
    "no longer under consideration",
    # Swedish
    "tyvarr gatt vidare med andra",
    "gatt vidare med andra kandidater",
    "du har inte gatt vidare",
    "inte gatt vidare i processen",
    "valt att ga vidare med andra",
    "inte aktuell for tjansten",
    "vi har beslutat att inte ga vidare",
)

_INTERVIEW_PHRASES: tuple[str, ...] = (
    # English
    "would like to invite you",
    "invite you to an interview",
    "schedule an interview",
    "book a time",
    "set up a call",
    "schedule a call",
    "next step in the process",
    "move forward to an interview",
    "available for a chat",
    # Swedish
    "vill bjuda in dig",
    "boka en tid",
    "kalla dig till intervju",
    "traffas for en intervju",
    "nasta steg i processen",
)

_OFFER_PHRASES: tuple[str, ...] = (
    # English
    "pleased to offer you",
    "offer you the position",
    "offer of employment",
    "we would like to offer",
    # Swedish
    "erbjuda dig tjansten",
    "vi vill erbjuda dig",
)

# Weaker signals: real but not conclusive on their own, so they land below the
# threshold and show up for review instead of prompting the user.
_ACKNOWLEDGED_PHRASES: tuple[str, ...] = (
    "we have received your application",
    "thank you for applying",
    "thanks for applying",
    "your application has been received",
    "tack for din ansokan",
    "vi har mottagit din ansokan",
)

# "Unfortunately" alone is suggestive but not decisive — it also opens
# "unfortunately this role is on hold". Only counted when nothing stronger fired.
_SOFT_REJECTION_PHRASES: tuple[str, ...] = ("unfortunately", "tyvarr")

# classification -> the status a user would move the application to.
STATUS_FOR_KIND: dict[str, str] = {
    "rejection": "rejected",
    "interview": "interview",
    "offer": "offer",
    "acknowledged": "applied",
}

# Swedish diacritics folded so a phrase list written in ASCII still matches
# "Tyvärr" and "ansökan"; ö/ø and å/ä all collapse to their base vowel.
_FOLD = str.maketrans("àáâãäåèéêëìíîïòóôõöøùúûüýÿçñ", "aaaaaaeeeeiiiioooooouuuuyycn")


def _normalize(text: str) -> str:
    return _WHITESPACE.sub(" ", text.lower().translate(_FOLD)).strip()


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


@dataclass(frozen=True)
class Classification:
    """What an email appears to say, and the sentence that says it."""

    kind: str
    suggested_status: str
    confidence: int
    evidence: str

    @property
    def should_suggest(self) -> bool:
        return self.confidence >= SUGGEST_THRESHOLD


def _find(sentences: list[str], phrases: tuple[str, ...]) -> tuple[str, str] | None:
    """Return ``(matched phrase, original sentence)`` for the first hit."""
    for sentence in sentences:
        normalized = _normalize(sentence)
        for phrase in phrases:
            if phrase in normalized:
                return phrase, sentence
    return None


def _truncate(sentence: str, limit: int = 300) -> str:
    sentence = _WHITESPACE.sub(" ", sentence).strip()
    return sentence if len(sentence) <= limit else sentence[: limit - 1] + "…"


def classify(subject: str | None, body: str | None) -> Classification | None:
    """Classify a recruiter email, or None when nothing recognisable is found.

    The subject is searched alongside the body because rejections are often
    decided entirely by a subject line ("Update on your application").
    """
    text_parts = [part for part in (subject or "", body or "") if part.strip()]
    if not text_parts:
        return None
    sentences = _sentences("\n".join(text_parts))
    if not sentences:
        return None

    # Offers and rejections outrank an interview invitation: a message doing
    # both ("we won't proceed for this role, but let's talk about another") is
    # rare, and the terminal outcome is the one worth surfacing.
    for kind, phrases, score in (
        ("offer", _OFFER_PHRASES, _SCORE_DECISIVE),
        ("rejection", _REJECTION_PHRASES, _SCORE_DECISIVE),
        ("interview", _INTERVIEW_PHRASES, _SCORE_STRONG),
    ):
        hit = _find(sentences, phrases)
        if hit:
            return Classification(
                kind=kind,
                suggested_status=STATUS_FOR_KIND[kind],
                confidence=score,
                evidence=_truncate(hit[1]),
            )

    soft = _find(sentences, _SOFT_REJECTION_PHRASES)
    if soft:
        return Classification(
            kind="rejection",
            suggested_status=STATUS_FOR_KIND["rejection"],
            confidence=_SCORE_WEAK,
            evidence=_truncate(soft[1]),
        )

    ack = _find(sentences, _ACKNOWLEDGED_PHRASES)
    if ack:
        return Classification(
            kind="acknowledged",
            suggested_status=STATUS_FOR_KIND["acknowledged"],
            confidence=_SCORE_WEAK,
            evidence=_truncate(ack[1]),
        )

    return None
