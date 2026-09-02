"""Public API for deterministic, print-ready ISBN-13 barcodes."""

from .barcode import Barcode
from .ean13 import encode_ean13
from .geometry import BarcodeGeometry, build_barcode_geometry
from .isbn import (
    calculate_check_digit,
    format_display_isbn,
    normalize_isbn,
    validate_display_text,
    validate_isbn13,
)
from .layout import (
    BarcodeLayout,
    LayoutSpec,
    MINIMUM_SIZE_MM,
    NORMAL_SIZE_MM,
    ResolvedBarcodeLayout,
    resolve_layout,
)
from .renderers import render_pdf, render_svg
from .verification import VerificationResult, verify_pdf, verify_svg

__version__ = "0.4.0"

__all__ = [
    "Barcode",
    "BarcodeGeometry",
    "BarcodeLayout",
    "LayoutSpec",
    "MINIMUM_SIZE_MM",
    "NORMAL_SIZE_MM",
    "ResolvedBarcodeLayout",
    "VerificationResult",
    "calculate_check_digit",
    "build_barcode_geometry",
    "encode_ean13",
    "format_display_isbn",
    "normalize_isbn",
    "render_pdf",
    "render_svg",
    "resolve_layout",
    "validate_display_text",
    "validate_isbn13",
    "verify_pdf",
    "verify_svg",
]
