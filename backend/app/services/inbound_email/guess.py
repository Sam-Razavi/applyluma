"""Guess the employer and job title an email is about, to prefill a new
application. Pure function, no model call; the user sees and can edit both
before anything is created, so a wrong guess costs one correction.
"""

from __future__ import annotations

import re

from app.services.inbound_email.matcher import ATS_DOMAINS, domain_matches, registrable_domain

# Mail providers and job boards: the domain says nothing about the employer.
_PERSONAL_DOMAINS = frozenset(
    {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "yahoo.com", "icloud.com",
     "me.com", "proton.me", "protonmail.com", "live.se", "hotmail.se", "telia.com",
     # Job boards that send on an employer's behalf.
     "linkedin.com", "indeed.com", "glassdoor.com", "arbetsformedlingen.se"}
)

# "…for the position of <title> at <company>", in English and Swedish. Each
# pattern names the groups it can fill.
_PATTERNS = [
    re.compile(
        r"(?:application|applying|interest)\s+(?:for|to)\s+(?:the\s+)?(?:position|role)?\s*(?:of|as)?\s*"
        r"(?P<title>.+?)\s+(?:at|with|@)\s+(?P<company>.+)$",
        re.I,
    ),
    re.compile(r"application\s+(?:was\s+|has\s+been\s+)?sent\s+to\s+(?P<company>.+)$", re.I),
    re.compile(
        r"application\s+for\s+(?:the\s+)?(?:(?:position|role)\s+(?:of|as)\s+)?(?P<title>.+)$", re.I
    ),
    re.compile(r"(?:applying|application)\s+(?:to|at|with)\s+(?P<company>[^-–|:]+?)(?:\s*[-–|:]\s*(?P<title>.+))?$", re.I),
    re.compile(
        r"ans[oö]kan\s+(?:till|om|avseende)\s+(?:tj[aä]nsten\s+(?:som\s+)?|rollen\s+(?:som\s+)?)?"
        r"(?P<title>.+?)\s+(?:hos|på|vid)\s+(?P<company>.+)$",
        re.I,
    ),
    re.compile(r"ans[oö]kan\s+(?:till|hos)\s+(?P<company>[^-–|:]+?)(?:\s*[-–|:]\s*(?P<title>.+))?$", re.I),
    re.compile(
        r"(?:application|ans[oö]kan)\s*(?:received|mottagen|confirmation|bekr[aä]ftelse)?\s*[-–|:]\s*(?P<title>.+?)"
        r"(?:\s+(?:at|hos|@)\s+(?P<company>.+))?$",
        re.I,
    ),
    re.compile(r"(?P<title>.+?)\s+(?:at|hos|@)\s+(?P<company>[^-–|:]+)$", re.I),
]

_PREFIX = re.compile(r"^\s*((re|fw|fwd|sv|vb)\s*:\s*)+", re.I)
_TRAILING = re.compile(r"[\s.!,;:–-]+$")


def _tidy(value: str | None) -> str:
    return _TRAILING.sub("", (value or "").strip().strip("\"'“”"))[:255]


def _company_from_domain(from_domain: str) -> str:
    domain = registrable_domain(from_domain or "")
    if not domain or domain in _PERSONAL_DOMAINS:
        return ""
    if any(domain_matches(from_domain, ats) for ats in ATS_DOMAINS):
        return ""
    label = domain.split(".")[0]
    return label.replace("-", " ").title() if len(label) > 3 else label.upper()


def guess_application(*, from_domain: str | None, subject: str | None) -> tuple[str, str]:
    """Return ``(company, job title)``; either may be empty."""
    text = _PREFIX.sub("", subject or "").strip()
    company = title = ""
    for pattern in _PATTERNS:
        found = pattern.search(text)
        if found:
            groups = found.groupdict()
            company, title = _tidy(groups.get("company")), _tidy(groups.get("title"))
            break
    return company or _company_from_domain(from_domain or ""), title
