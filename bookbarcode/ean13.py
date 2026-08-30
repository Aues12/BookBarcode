"""EAN-13 parity tables and deterministic module encoding."""

from __future__ import annotations

from .isbn import validate_isbn13


SYMBOL_MODULES = 95
GUARD_MODULES = frozenset((0, 2, 46, 48, 92, 94))
LEFT_PATTERNS = (
    "LLLLLL",
    "LLGLGG",
    "LLGGLG",
    "LLGGGL",
    "LGLLGG",
    "LGGLLG",
    "LGGGLL",
    "LGLGLG",
    "LGLGGL",
    "LGGLGL",
)
L_CODES = (
    "0001101",
    "0011001",
    "0010011",
    "0111101",
    "0100011",
    "0110001",
    "0101111",
    "0111011",
    "0110111",
    "0001011",
)
R_CODES = tuple(
    "".join("1" if bit == "0" else "0" for bit in code) for code in L_CODES
)
G_CODES = tuple(code[::-1] for code in R_CODES)


def encode_ean13(isbn: str) -> str:
    """Encode a valid ISBN-13 as the canonical 95-module EAN-13 pattern."""
    normalized = validate_isbn13(isbn)
    parity = LEFT_PATTERNS[int(normalized[0])]
    left = "".join(
        (L_CODES if encoding == "L" else G_CODES)[int(digit)]
        for digit, encoding in zip(normalized[1:7], parity)
    )
    right = "".join(R_CODES[int(digit)] for digit in normalized[7:])
    pattern = f"101{left}01010{right}101"
    if len(pattern) != SYMBOL_MODULES:
        raise AssertionError("EAN-13 pattern must contain 95 modules")
    return pattern


def iter_black_runs(pattern: str) -> list[tuple[int, int]]:
    """Group consecutive black modules into ``(start, width)`` runs."""
    if len(pattern) != SYMBOL_MODULES or set(pattern) - {"0", "1"}:
        raise ValueError("EAN-13 pattern must contain exactly 95 binary modules")
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, bit in enumerate(pattern + "0"):
        if bit == "1" and start is None:
            start = index
        elif bit == "0" and start is not None:
            runs.append((start, index - start))
            start = None
    return runs
