"""Shared password complexity rules for register / change / reset flows.

Kept deliberately simple: length, at least one letter and one digit, and a
small blocklist of the most common leaked passwords. The frontend mirrors
these rules for instant feedback, but this module is authoritative.
"""

COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "password1",
        "password12",
        "password123",
        "passw0rd",
        "p@ssw0rd",
        "12345678",
        "123456789",
        "1234567890",
        "1q2w3e4r",
        "1qaz2wsx",
        "qwerty123",
        "qwertyuiop",
        "asdf1234",
        "abc12345",
        "abcd1234",
        "iloveyou1",
        "admin123",
        "admin1234",
        "welcome1",
        "welcome123",
        "letmein1",
        "sunshine1",
        "princess1",
        "football1",
        "baseball1",
        "superman1",
        "monkey123",
        "dragon123",
        "shadow123",
        "master123",
        "trustno1",
        "whatever1",
        "summer2024",
        "summer2025",
        "changeme1",
    }
)


def validate_password_strength(password: str) -> str:
    """Validate password complexity; raise ValueError with a user-facing message."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isalpha() for c in password):
        raise ValueError("Password must contain at least one letter")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must contain at least one number")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("This password is too common — choose something less guessable")
    return password
