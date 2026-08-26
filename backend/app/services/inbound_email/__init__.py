"""Inbound email ingestion: vendor adapters and application matching."""

from app.services.inbound_email.base import (
    InboundAdapter,
    InboundParseError,
    NormalizedEmail,
)
from app.services.inbound_email.matcher import (
    MATCH_THRESHOLD,
    MatchCandidate,
    MatchResult,
    normalize_domain,
    score_email,
)
from app.services.inbound_email.registry import (
    UnknownVendorError,
    available_vendors,
    get_adapter,
)

__all__ = [
    "InboundAdapter",
    "InboundParseError",
    "NormalizedEmail",
    "MATCH_THRESHOLD",
    "MatchCandidate",
    "MatchResult",
    "normalize_domain",
    "score_email",
    "UnknownVendorError",
    "available_vendors",
    "get_adapter",
]
