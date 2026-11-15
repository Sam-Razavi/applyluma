"""Decide whether a forwarded email is about a job application at all.

People forward their whole inbox, so most of what arrives is newsletters,
receipts and delivery notices. Keeping those would show noise in the inbox,
store private mail that has nothing to do with the product, and let a parcel
notice from a company the user applied to pass as mail about the application.

Pure function, no database: the task calls it after matching and classifying,
and stores nothing for mail it rejects.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.services.inbound_email.classifier import SUGGEST_THRESHOLD, Classification
from app.services.inbound_email.matcher import ATS_DOMAINS, domain_matches

_FOLD = str.maketrans("àáâãäåèéêëìíîïòóôõöøùúûüýÿçñ", "aaaaaaeeeeiiiioooooouuuuyycn")


def _fold(text: str | None) -> str:
    return (text or "").lower().translate(_FOLD)


# Words that mark mail about applying for a job, in English and Swedish
# (diacritics folded). Matched on word starts, so "applic" covers application,
# applications and applicant.
_JOB_WORDS = re.compile(
    r"\b("
    r"applic|applied|applying|candidate|candidacy|interview|recruit|hiring manager|"
    r"talent acquisition|job offer|offer of employment|your cv|your resume|vacancy|"
    r"the position|the role|this position|this role|"
    r"ansokan|ansokning|ansokt|sokt tjansten|kandidat|intervju|rekryter|"
    r"tjansten|rollen som|anstallning|urvalsprocess|ditt cv"
    r")"
)

# A subject that is plainly about one application. Automated confirmations
# ("Thank you for applying", "Tack för din ansökan") carry mailing-list
# headers like any newsletter, and this is what tells the two apart.
_APPLICATION_SUBJECT = re.compile(
    r"\b("
    r"your application|application (received|was sent|sent|submitted|update|status|confirmation)|"
    r"thank you for applying|thanks for applying|thank you for your (application|interest)|"
    r"we(.ve| have) received your application|"
    r"din ansokan|tack for din ansokan|tack for din intresseanmalan|vi har (tagit emot|mottagit) din ansokan|"
    r"ansokan (mottagen|bekraftelse)"
    r")"
)

# Words that mark shop and delivery mail. Checked in the subject only: a job ad
# may well mention "delivery" in its text.
_COMMERCE_WORDS = re.compile(
    r"\b("
    r"order|shipped|shipment|delivery|delivered|tracking|invoice|receipt|refund|payment|"
    r"subscription|"
    r"skickad|skickade|leverans|levererad|bestallning|faktura|kvitto|betalning|paket|"
    r"prenumeration"
    r")"
)

# Senders that only ever send bulk or automated mail.
_BULK_SENDER = re.compile(
    r"(newsletter|news@|digest|marketing|promo|deals|offers@|shipment|order-|orders@|billing|receipts?@)"
)

_BULK_BODY = re.compile(
    r"(unsubscribe|view (this email )?in (your )?browser|manage (your )?preferences|"
    r"avregistrera|avprenumerera|avsluta prenumeration|visa i webblasare)"
)

_BULK_HEADERS = ("list-unsubscribe", "list-id", "x-campaign", "x-mailgun-tag", "feedback-id")


def looks_bulk(
    *, headers: Mapping[str, str], from_address: str | None, snippet: str | None
) -> bool:
    """Whether the mail is a mailing-list or automated send, not a person's message."""
    lowered = {key.lower(): value for key, value in headers.items()}
    if any(name in lowered for name in _BULK_HEADERS):
        return True
    if lowered.get("precedence", "").strip().lower() in {"bulk", "list", "junk"}:
        return True
    if _BULK_SENDER.search((from_address or "").lower()):
        return True
    return bool(_BULK_BODY.search(_fold(snippet)))


def is_job_related(
    *,
    subject: str | None,
    snippet: str | None,
    from_domain: str | None,
    classification: Classification | None,
    matched: bool,
    bulk: bool,
) -> tuple[bool, str]:
    """Return ``(keep, reason)`` for one email."""
    folded_subject = _fold(subject)
    has_job_words = bool(_JOB_WORDS.search(folded_subject) or _JOB_WORDS.search(_fold(snippet)))
    from_ats = any(domain_matches(from_domain or "", ats) for ats in ATS_DOMAINS)

    if classification is not None and classification.confidence >= SUGGEST_THRESHOLD:
        return True, "It reads like a decision on an application."

    if _COMMERCE_WORDS.search(folded_subject) and not _JOB_WORDS.search(folded_subject):
        return False, "The subject is about an order, delivery or payment."

    if bulk:
        # A mailing-list send is kept only when it is tied to something the
        # user applied for: job-alert digests and newsletters mention jobs too.
        if has_job_words and (matched or from_ats):
            return True, "Bulk mail about an application the user tracks."
        if _APPLICATION_SUBJECT.search(folded_subject):
            return True, "An automated message about one application."
        return False, "Newsletter or automated bulk mail."

    if has_job_words:
        return True, "It uses the wording of a job application."
    if matched:
        return True, "A personal message from a company the user applied to."
    if from_ats:
        return True, "Sent through a recruiting system."
    return False, "Nothing in it is about a job application."
