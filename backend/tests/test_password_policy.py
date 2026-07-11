"""Unit tests for the shared password complexity rules."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.password_policy import COMMON_PASSWORDS, validate_password_strength


def test_accepts_strong_password() -> None:
    assert validate_password_strength("GoodPass1") == "GoodPass1"


def test_accepts_long_passphrase_with_digit() -> None:
    assert validate_password_strength("correct horse battery 9") == "correct horse battery 9"


def test_rejects_short_password() -> None:
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_strength("Abc1234")


def test_rejects_password_without_letter() -> None:
    with pytest.raises(ValueError, match="at least one letter"):
        validate_password_strength("1234567890!")


def test_rejects_password_without_digit() -> None:
    with pytest.raises(ValueError, match="at least one number"):
        validate_password_strength("OnlyLetters!")


@pytest.mark.parametrize("common", ["password1", "Password1", "QWERTY123", "Trustno1"])
def test_rejects_common_passwords_case_insensitive(common: str) -> None:
    with pytest.raises(ValueError, match="too common"):
        validate_password_strength(common)


def test_blocklist_entries_are_lowercase() -> None:
    """The check lowercases input before lookup, so mixed-case entries
    would silently never match."""
    for entry in COMMON_PASSWORDS:
        assert entry == entry.lower()
