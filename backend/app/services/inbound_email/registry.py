"""Adapter lookup.

A plain dict rather than dynamic import: the set of vendors is small and known,
and a static mapping keeps ``mypy --strict`` able to check every adapter really
satisfies the Protocol.
"""

from __future__ import annotations

from app.services.inbound_email.base import InboundAdapter
from app.services.inbound_email.generic import GenericAdapter

_ADAPTERS: dict[str, InboundAdapter] = {
    GenericAdapter.name: GenericAdapter(),
}

DEFAULT_ADAPTER = GenericAdapter.name


class UnknownVendorError(ValueError):
    """Raised when configuration names an adapter that does not exist."""


def get_adapter(name: str) -> InboundAdapter:
    """Return the adapter registered under ``name``."""
    try:
        return _ADAPTERS[(name or DEFAULT_ADAPTER).strip().lower()]
    except KeyError as exc:
        known = ", ".join(sorted(_ADAPTERS)) or "(none)"
        raise UnknownVendorError(f"Unknown inbound email vendor {name!r}; known: {known}") from exc


def available_vendors() -> list[str]:
    return sorted(_ADAPTERS)
