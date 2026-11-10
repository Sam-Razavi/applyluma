"""Classifier tests.

Pure function, so these are fixtures and assertions with no DB or HTTP — the
file to edit when tuning phrasings against real mail.

Swedish is covered alongside English throughout: the user base is Sweden-heavy
and a classifier that only reads English would miss most of their rejections.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.inbound_email.classifier import SUGGEST_THRESHOLD, classify


def test_english_rejection_is_confident() -> None:
    result = classify("Update on your application", "Unfortunately we have decided to proceed with other candidates.")
    assert result is not None
    assert result.kind == "rejection"
    assert result.suggested_status == "rejected"
    assert result.should_suggest


def test_swedish_rejection_is_confident() -> None:
    result = classify("Din ansökan", "Tyvärr har du inte gått vidare i processen.")
    assert result is not None
    assert result.kind == "rejection"
    assert result.should_suggest


def test_diacritics_are_folded() -> None:
    """Phrase lists are written in ASCII; real mail is not."""
    with_marks = classify("Ansökan", "Tyvärr har du inte gått vidare.")
    without = classify("Ansokan", "Tyvarr har du inte gatt vidare.")
    assert with_marks is not None and without is not None
    assert with_marks.kind == without.kind == "rejection"


def test_english_interview_invitation() -> None:
    result = classify("Next steps", "We would like to invite you to an interview next week.")
    assert result is not None
    assert result.kind == "interview"
    assert result.suggested_status == "interview"
    assert result.should_suggest


def test_swedish_interview_invitation() -> None:
    result = classify("Intervju", "Vi vill bjuda in dig till en intervju nästa vecka.")
    assert result is not None
    assert result.kind == "interview"
    assert result.should_suggest


def test_offer_outranks_everything() -> None:
    result = classify("Offer", "We are pleased to offer you the position.")
    assert result is not None
    assert result.kind == "offer"
    assert result.suggested_status == "offer"


def test_swedish_offer() -> None:
    result = classify("Erbjudande", "Vi vill erbjuda dig tjänsten som utvecklare.")
    assert result is not None
    assert result.kind == "offer"


def test_rejection_beats_interview_when_both_appear() -> None:
    """A terminal outcome is the one worth surfacing."""
    result = classify(
        "Update",
        "We regret to inform you that we will not proceed. We would like to invite you to apply again later.",
    )
    assert result is not None
    assert result.kind == "rejection"


def test_bare_unfortunately_stays_below_threshold() -> None:
    """'Unfortunately this role is on hold' is not a rejection."""
    result = classify("Update", "Unfortunately this role is on hold for now.")
    assert result is not None
    assert result.kind == "rejection"
    assert result.confidence < SUGGEST_THRESHOLD
    assert not result.should_suggest


def test_acknowledgement_never_prompts() -> None:
    """A receipt is not a status change worth interrupting anyone for."""
    result = classify("Application received", "Thank you for applying. We have received your application.")
    assert result is not None
    assert result.kind == "acknowledged"
    assert not result.should_suggest


def test_swedish_acknowledgement_never_prompts() -> None:
    result = classify("Ansökan mottagen", "Tack för din ansökan! Vi återkommer.")
    assert result is not None
    assert result.kind == "acknowledged"
    assert not result.should_suggest


def test_unrelated_mail_is_not_classified() -> None:
    assert classify("Newsletter", "Here are this week's top tech stories.") is None


def test_empty_input_is_not_classified() -> None:
    assert classify(None, None) is None
    assert classify("", "   ") is None


def test_evidence_is_the_sentence_that_decided_it() -> None:
    """The user has to be able to judge the suggestion, so quote the source."""
    result = classify(
        "Update",
        "Thanks for your time. Unfortunately we have decided to proceed with other candidates. Best wishes.",
    )
    assert result is not None
    assert "proceed with other candidates" in result.evidence.lower()
    assert "best wishes" not in result.evidence.lower()


def test_evidence_is_truncated() -> None:
    result = classify("Update", "We regret to inform you " + "x" * 2000)
    assert result is not None
    assert len(result.evidence) <= 300


def test_subject_alone_can_classify() -> None:
    """Some rejections say it all in the subject line."""
    result = classify("We regret to inform you about your application", None)
    assert result is not None
    assert result.kind == "rejection"


def test_classification_is_deterministic() -> None:
    args = ("Update on your application", "Unfortunately we will not be moving forward.")
    assert classify(*args) == classify(*args)


@pytest.mark.parametrize(
    "body",
    [
        "Unfortunately, we have decided not to move forward with your application.",
        "We won’t be moving forward with your application at this time.",
        "We won't be progressing your application further.",
        "We have decided to pursue other candidates.",
        "We have chosen applicants whose experience more closely matches the role.",
        "The position has been filled.",
        "Your application has been unsuccessful.",
        "Tyvärr har vi valt att inte gå vidare med din ansökan.",
        "Vi har valt en annan kandidat.",
        "Tjänsten är tillsatt.",
    ],
)
def test_common_rejection_wordings_are_confident(body: str) -> None:
    """Real rejections, mostly the "not to move forward" family, which used to
    fall below the suggestion threshold."""
    result = classify("Your application", body)
    assert result is not None
    assert result.kind == "rejection"
    assert result.confidence >= SUGGEST_THRESHOLD


@pytest.mark.parametrize(
    "body",
    [
        "We would like to invite you for an interview next week.",
        "We'd like to invite you to interview for the role.",
        "Kallelse till intervju för tjänsten som utvecklare.",
    ],
)
def test_more_interview_wordings(body: str) -> None:
    result = classify("Next steps", body)
    assert result is not None
    assert result.kind == "interview"
    assert result.confidence >= SUGGEST_THRESHOLD
