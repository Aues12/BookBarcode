"""Public API for deterministic, print-ready ISBN-13 barcodes."""

from .barcode import Barcode
from .ean13 import encode_ean13
from .isbn import (
    calculate_check_digit,
    format_display_isbn,
    normalize_isbn,
    validate_display_text,
    validate_isbn13,
)
from .layout import BarcodeLayout, MINIMUM_SIZE_MM, NORMAL_SIZE_MM
from .renderers import render_pdf, render_svg
from .verification import VerificationResult, verify_pdf, verify_svg

__version__ = "0.3.0"

__all__ = [
    "Barcode",
    "BarcodeLayout",
    "MINIMUM_SIZE_MM",
    "NORMAL_SIZE_MM",
    "VerificationResult",
    "calculate_check_digit",
    "encode_ean13",
    "format_display_isbn",
    "normalize_isbn",
    "render_pdf",
    "render_svg",
    "validate_display_text",
    "validate_isbn13",
    "verify_pdf",
    "verify_svg",
]
