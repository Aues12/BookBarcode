"""ISBN-13 normalization, display formatting, and checksum validation."""

from __future__ import annotations

import re


_ISBN_LABEL = re.compile(r"^\s*ISBN(?:-13)?\s*:?\s*", re.IGNORECASE)


def normalize_isbn(value: str) -> str:
    """Return only the digits from a labeled, spaced, or hyphenated ISBN.

    The function removes an optional ``ISBN`` or ``ISBN-13`` prefix plus
    whitespace and hyphens. It does not validate length or checksum.
    """
    if not isinstance(value, str):
        raise TypeError("isbn must be a string")
    without_label = _ISBN_LABEL.sub("", value)
    return re.sub(r"[-\s]", "", without_label)


def calculate_check_digit(first_twelve_digits: str) -> str:
    """Calculate the EAN-13 check digit for exactly twelve decimal digits."""
    if not isinstance(first_twelve_digits, str):
        raise TypeError("first_twelve_digits must be a string")
    if len(first_twelve_digits) != 12 or not first_twelve_digits.isdigit():
        raise ValueError("check-digit input must contain exactly 12 digits")
    weighted_sum = sum(
        int(digit) * (1 if index % 2 == 0 else 3)
        for index, digit in enumerate(first_twelve_digits)
    )
    return str((-weighted_sum) % 10)


def validate_isbn13(value: str) -> str:
    """Normalize and validate an ISBN-13 without silently correcting it."""
    isbn = normalize_isbn(value)
    if len(isbn) != 13 or not isbn.isdigit():
        raise ValueError("ISBN-13 must contain exactly 13 digits")
    if not isbn.startswith(("978", "979")):
        raise ValueError("ISBN-13 must start with 978 or 979")
    expected = calculate_check_digit(isbn[:12])
    if isbn[-1] != expected:
        raise ValueError(
            f"invalid ISBN-13 check digit: expected {expected}, received {isbn[-1]}"
        )
    return isbn


def validate_display_text(display_text: str, isbn: str) -> str:
    """Validate that a visible ISBN label represents the encoded ISBN."""
    if not isinstance(display_text, str):
        raise TypeError("display_text must be a string")
    normalized_isbn = validate_isbn13(isbn)
    stripped = display_text.strip()
    if not re.match(r"^ISBN(?:-13)?\s", stripped, flags=re.IGNORECASE):
        raise ValueError("display_text must start with 'ISBN ' or 'ISBN-13 '")
    if normalize_isbn(stripped) != normalized_isbn:
        raise ValueError("display_text digits must match the encoded ISBN")
    return stripped


def format_display_isbn(isbn: str) -> str:
    """Format a valid ISBN using the library's readable 3-3-3-3-1 grouping.

    This grouping is a presentation fallback, not an inference of official
    registrant ranges. Callers may pass assigned hyphenation explicitly.
    """
    normalized = validate_isbn13(isbn)
    return (
        f"ISBN {normalized[:3]}-{normalized[3:6]}-{normalized[6:9]}-"
        f"{normalized[9:12]}-{normalized[12]}"
    )
