"""Match a forwarded email to one of the user's tracked applications.

``score_email`` is deliberately pure — no database, no network, no ORM objects.
Matching is the risky part of inbound ingestion, so it has to be testable
against fixtures in isolation.

Known limitation: ``registrable_domain`` takes the last two labels, which is
wrong for multi-part public suffixes (``careers.spotify.co.uk`` reduces to
``co.uk``). Fixing it properly needs the public-suffix list; until a real
``.co.uk`` case shows up in the admin view, the cost of a new dependency isn't
justified. Such a sender simply fails signals A and B and falls through to the
subject-based signals.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import urlsplit

# Applicant tracking systems send on behalf of many employers, so their domain
# says nothing about which company is writing. When mail comes from one of
# these, the sender domain is ignored and the company is looked for in the
# subject and body instead.
ATS_DOMAINS: frozenset[str] = frozenset(
    {
        "greenhouse.io",
        "lever.co",
        "myworkday.com",
        "myworkdayjobs.com",
        "smartrecruiters.com",
        "workable.com",
        "teamtailor.com",
        "varbi.com",
        "recruitee.com",
        "jobvite.com",
        "icims.com",
        "ashbyhq.com",
        "breezy.hr",
        "bamboohr.com",
    }
)

# Hosts that appear in job_url but are never the employer: aggregators and
# ATS-hosted boards. A job_url on one of these says nothing about who sent the
# mail, so the job-URL signal is skipped — otherwise a routine LinkedIn
# notification would match whichever application happened to be saved from a
# LinkedIn link.
_NON_EMPLOYER_HOSTS: frozenset[str] = frozenset(
    {
        "linkedin.com",
        "indeed.com",
        "glassdoor.com",
        "monster.com",
        "ziprecruiter.com",
        "arbetsformedlingen.se",
        "jobbsafari.se",
        "themuse.com",
        "remotive.com",
        "remoteok.com",
        "adzuna.com",
    }
)

# Stripped from a company name before comparing it against a domain label:
# "Spotify AB" registers spotify.com, not spotifyab.com.
_LEGAL_SUFFIXES: frozenset[str] = frozenset(
    {"ab", "inc", "llc", "ltd", "limited", "gmbh", "oy", "as", "asa", "bv", "nv", "plc", "corp", "co"}
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Confidence at or above which the match is recorded on the row. Below it the
# email is stored unmatched with the best guess preserved in the reason: an
# unmatched row is a useful signal, a wrong match is corruption.
MATCH_THRESHOLD = 70

# Two candidates scoring within this margin are treated as ambiguous — most
# often the same company appearing twice in the user's pipeline.
_AMBIGUITY_MARGIN = 10

_SCORE_JOB_URL_DOMAIN = 90
_SCORE_COMPANY_DOMAIN = 80
# An ATS naming the company in the subject ("Your application to Klarna") is
# strong evidence and scores above the threshold; finding it only in the body
# is weaker and lands as a review candidate instead.
_SCORE_ATS_SUBJECT = 75
_SCORE_ATS_BODY = 55
# A company named in the subject by an unrecognized sender is suggestive but
# not conclusive, so it deliberately stays below the threshold for review.
_SCORE_SUBJECT_COMPANY = 60


@dataclass(frozen=True)
class MatchCandidate:
    """One of the user's applications, reduced to the fields matching needs."""

    application_id: uuid.UUID
    company_name: str
    job_url: str | None = None


@dataclass(frozen=True)
class MatchResult:
    application_id: uuid.UUID | None
    confidence: int
    method: str
    reason: str


def normalize_domain(value: str) -> str:
    """Lowercase a hostname or email domain and drop a leading ``www.``."""
    host = value.strip().lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    return host


def registrable_domain(host: str) -> str:
    """Approximate the registrable domain as the last two labels."""
    host = normalize_domain(host)
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def domain_matches(host: str, candidate: str) -> bool:
    """True when ``host`` is ``candidate`` or a subdomain of it.

    Suffix-safe: ``evil-spotify.com`` must not match ``spotify.com``. Mirrors
    the comparison in ``app/services/url_scraper.py``.
    """
    host = normalize_domain(host)
    candidate = normalize_domain(candidate)
    if not host or not candidate:
        return False
    return host == candidate or host.endswith("." + candidate)


def host_from_url(url: str | None) -> str:
    if not url:
        return ""
    raw = url.strip()
    if not raw:
        return ""
    if "//" not in raw:
        raw = "//" + raw
    try:
        return normalize_domain(urlsplit(raw).hostname or "")
    except ValueError:
        return ""


def normalize_company(name: str) -> str:
    """Reduce a company name to comparable alphanumerics, minus legal suffixes."""
    tokens = [t for t in _NON_ALNUM.split(name.strip().lower()) if t]
    while len(tokens) > 1 and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return "".join(tokens)


def contains_company(haystack: str, company_name: str) -> bool:
    """Whole-word search for a company name inside free text.

    Token-boundary matching, not substring: the CV tailor's fabricated-skill
    check learned the hard way that "Java" otherwise matches inside
    "JavaScript". Here it stops "Klarna" matching inside "Klarnaco".
    """
    normalized_company = normalize_company(company_name)
    if not normalized_company:
        return False
    tokens = [t for t in _NON_ALNUM.split(haystack.lower()) if t]
    if not tokens:
        return False
    # Compare against joined runs of tokens so a multi-word company name
    # ("H&M Group" -> "hmgroup") still matches adjacent words in the text.
    max_span = min(len(tokens), 4)
    for start in range(len(tokens)):
        for span in range(1, max_span + 1):
            if start + span > len(tokens):
                break
            if "".join(tokens[start : start + span]) == normalized_company:
                return True
    return False


def _score_candidate(
    candidate: MatchCandidate,
    *,
    from_domain: str,
    subject: str,
    snippet: str,
    is_ats: bool,
) -> tuple[int, str, str]:
    """Return ``(score, method, reason)`` for one candidate."""
    company = candidate.company_name

    if not is_ats and from_domain:
        job_host = host_from_url(candidate.job_url)
        # A job_url on an aggregator or ATS board is not the employer's own
        # site, so it proves nothing about who sent the mail.
        job_host_is_employer = bool(job_host) and not any(
            domain_matches(job_host, host) for host in _NON_EMPLOYER_HOSTS | ATS_DOMAINS
        )
        if job_host_is_employer and registrable_domain(from_domain) == registrable_domain(job_host):
            return (
                _SCORE_JOB_URL_DOMAIN,
                "job_url_domain",
                f"Sender domain {from_domain} matches the job URL host {job_host}.",
            )

        normalized_company = normalize_company(company)
        sender_label = registrable_domain(from_domain).split(".")[0]
        if normalized_company and sender_label == normalized_company:
            return (
                _SCORE_COMPANY_DOMAIN,
                "company_domain",
                f"Sender domain {from_domain} matches company name {company!r}.",
            )

    if is_ats:
        if contains_company(subject, company):
            return (
                _SCORE_ATS_SUBJECT,
                "ats_subject",
                f"Applicant tracking sender {from_domain}; company {company!r} named in the subject.",
            )
        if contains_company(snippet, company):
            return (
                _SCORE_ATS_BODY,
                "ats_body",
                f"Applicant tracking sender {from_domain}; company {company!r} found in the body only.",
            )
        return (0, "none", "")

    if contains_company(subject, company):
        return (
            _SCORE_SUBJECT_COMPANY,
            "subject_company",
            f"Company {company!r} appears in the subject line.",
        )

    return (0, "none", "")


def score_email(
    *,
    from_domain: str,
    subject: str,
    snippet: str,
    candidates: Sequence[MatchCandidate],
) -> MatchResult:
    """Pick the application a forwarded email most likely belongs to.

    ``from_domain`` must come from the message's ``From:`` header, never the
    SMTP envelope sender — forwarding rewrites the envelope to the user's own
    address, which would make every message look self-sent.
    """
    if not candidates:
        return MatchResult(None, 0, "none", "No applications to match against.")

    domain = normalize_domain(from_domain)
    is_ats = any(domain_matches(domain, ats) for ats in ATS_DOMAINS)

    scored = [
        (
            _score_candidate(
                candidate, from_domain=domain, subject=subject, snippet=snippet, is_ats=is_ats
            ),
            candidate,
        )
        for candidate in candidates
    ]
    scored = [entry for entry in scored if entry[0][0] > 0]
    if not scored:
        return MatchResult(
            None,
            0,
            "none",
            f"No candidate matched sender {domain or '(unknown)'} or the subject line.",
        )

    scored.sort(key=lambda entry: entry[0][0], reverse=True)
    (score, method, reason), best = scored[0]

    if len(scored) > 1:
        runner_up_score = scored[1][0][0]
        if score - runner_up_score <= _AMBIGUITY_MARGIN:
            halved = score // 2
            runner_up = scored[1][1]
            return MatchResult(
                best.application_id if halved >= MATCH_THRESHOLD else None,
                halved,
                method,
                f"{reason} Ambiguous: {runner_up.company_name!r} scored "
                f"{runner_up_score} against {score}, so confidence was reduced.",
            )

    if score < MATCH_THRESHOLD:
        return MatchResult(
            None,
            score,
            method,
            f"{reason} Below the {MATCH_THRESHOLD} confidence threshold, left unmatched.",
        )

    return MatchResult(best.application_id, score, method, reason)
