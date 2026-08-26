"""Matcher unit tests.

Pure functions, so these need no database, no HTTP, and no fixtures — which is
the point: matching is the risky part of inbound ingestion and has to be cheap
to iterate on.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.inbound_email.matcher import (
    MATCH_THRESHOLD,
    MatchCandidate,
    contains_company,
    domain_matches,
    normalize_company,
    normalize_domain,
    registrable_domain,
    score_email,
)

SPOTIFY = MatchCandidate(uuid.uuid4(), "Spotify AB", "https://jobs.spotify.com/job/123")
KLARNA = MatchCandidate(uuid.uuid4(), "Klarna", None)


def test_job_url_domain_matches_across_subdomains() -> None:
    result = score_email(
        from_domain="careers.spotify.com", subject="Update", snippet="", candidates=[SPOTIFY]
    )
    assert result.application_id == SPOTIFY.application_id
    assert result.method == "job_url_domain"
    assert result.confidence >= MATCH_THRESHOLD


def test_company_name_matches_sender_domain() -> None:
    result = score_email(from_domain="klarna.com", subject="Hi", snippet="", candidates=[KLARNA])
    assert result.application_id == KLARNA.application_id
    assert result.method == "company_domain"


def test_legal_suffix_is_ignored_when_comparing_company_to_domain() -> None:
    """'Spotify AB' registers spotify.com, not spotifyab.com."""
    only_spotify = MatchCandidate(uuid.uuid4(), "Spotify AB", None)
    result = score_email(
        from_domain="spotify.com", subject="Hello", snippet="", candidates=[only_spotify]
    )
    assert result.application_id == only_spotify.application_id


def test_ats_sender_matches_company_named_in_subject() -> None:
    """The dominant real-world case: mail from an ATS, employer named in the subject."""
    result = score_email(
        from_domain="greenhouse.io",
        subject="Your application to Klarna",
        snippet="",
        candidates=[SPOTIFY, KLARNA],
    )
    assert result.application_id == KLARNA.application_id
    assert result.method == "ats_subject"
    assert result.confidence >= MATCH_THRESHOLD


def test_ats_sender_with_company_only_in_body_is_left_for_review() -> None:
    result = score_email(
        from_domain="greenhouse.io",
        subject="An update",
        snippet="Thank you for applying to Klarna.",
        candidates=[KLARNA],
    )
    assert result.application_id is None
    assert result.method == "ats_body"
    assert 0 < result.confidence < MATCH_THRESHOLD


def test_ats_sender_never_matches_on_its_own_domain() -> None:
    """greenhouse.io is not an employer; naming nobody must not pick a candidate."""
    result = score_email(
        from_domain="greenhouse.io", subject="An update", snippet="", candidates=[SPOTIFY, KLARNA]
    )
    assert result.application_id is None
    assert result.method == "none"


def test_lookalike_domain_does_not_match() -> None:
    """evil-spotify.com must never be treated as spotify.com."""
    result = score_email(
        from_domain="evil-spotify.com", subject="Hello", snippet="", candidates=[SPOTIFY]
    )
    assert result.application_id is None
    assert result.confidence == 0


def test_aggregator_job_url_does_not_produce_a_match() -> None:
    """A LinkedIn notification must not match whatever was saved from LinkedIn."""
    from_linkedin = MatchCandidate(
        uuid.uuid4(), "Acme", "https://www.linkedin.com/jobs/view/999"
    )
    result = score_email(
        from_domain="linkedin.com", subject="Jobs for you", snippet="", candidates=[from_linkedin]
    )
    assert result.application_id is None


def test_company_match_is_whole_word_not_substring() -> None:
    """The fabricated-skill lesson: 'Java' must not match inside 'JavaScript'."""
    java = MatchCandidate(uuid.uuid4(), "Java", None)
    result = score_email(
        from_domain="unknown.com", subject="JavaScript developer role", snippet="", candidates=[java]
    )
    assert result.application_id is None


def test_subject_only_match_stays_below_threshold() -> None:
    result = score_email(
        from_domain="unknown.com", subject="About the Klarna role", snippet="", candidates=[KLARNA]
    )
    assert result.application_id is None
    assert result.method == "subject_company"
    assert 0 < result.confidence < MATCH_THRESHOLD


def test_ambiguous_candidates_reduce_confidence() -> None:
    """Two applications at the same company must not be guessed between."""
    first = MatchCandidate(uuid.uuid4(), "Klarna", None)
    second = MatchCandidate(uuid.uuid4(), "Klarna", None)
    result = score_email(
        from_domain="klarna.com", subject="Hi", snippet="", candidates=[first, second]
    )
    assert result.application_id is None
    assert "Ambiguous" in result.reason


def test_no_candidates_returns_unmatched() -> None:
    result = score_email(from_domain="klarna.com", subject="Hi", snippet="", candidates=[])
    assert result.application_id is None
    assert result.method == "none"
    assert result.confidence == 0


def test_unmatched_result_still_explains_itself() -> None:
    """An unmatched row is only useful if it says why."""
    result = score_email(
        from_domain="random.example", subject="Newsletter", snippet="", candidates=[KLARNA]
    )
    assert result.application_id is None
    assert result.reason


def test_scoring_is_deterministic() -> None:
    args = {
        "from_domain": "greenhouse.io",
        "subject": "Your application to Klarna",
        "snippet": "",
        "candidates": [SPOTIFY, KLARNA],
    }
    assert score_email(**args) == score_email(**args)  # type: ignore[arg-type]


def test_normalize_domain_strips_www_and_case() -> None:
    assert normalize_domain("WWW.Spotify.com.") == "spotify.com"


def test_registrable_domain_reduces_subdomains() -> None:
    assert registrable_domain("careers.mail.spotify.com") == "spotify.com"


def test_domain_matches_is_suffix_safe() -> None:
    assert domain_matches("careers.spotify.com", "spotify.com")
    assert not domain_matches("evil-spotify.com", "spotify.com")


def test_normalize_company_strips_legal_suffix() -> None:
    assert normalize_company("Spotify AB") == "spotify"
    assert normalize_company("Acme Inc.") == "acme"


def test_normalize_company_keeps_single_token_names() -> None:
    """A one-word name that happens to be a legal suffix must survive."""
    assert normalize_company("Co") == "co"


def test_contains_company_spans_adjacent_words() -> None:
    assert contains_company("Welcome to H&M Group", "H&M Group")
    assert not contains_company("Welcome to Klarnaco", "Klarna")
