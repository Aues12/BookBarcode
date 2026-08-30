"""Structural verification for process-black BookBarcode PDF files."""

from __future__ import annotations

from pathlib import Path

from ..layout import BarcodeLayout
from ..renderers.pdf import mm_to_points
from .result import VerificationResult


def verify_pdf(
    path: str | Path,
    layout: BarcodeLayout | None = None,
) -> VerificationResult:
    """Verify PDF framing, physical page size, and process-black command."""
    source = Path(path)
    resolved_layout = layout or BarcodeLayout()
    try:
        data = source.read_bytes()
    except OSError as exc:
        return VerificationResult((f"unable to read PDF: {exc}",))
    errors: list[str] = []
    if not data.startswith(b"%PDF-1.4") or not data.rstrip().endswith(b"%%EOF"):
        errors.append("PDF framing is invalid")
    if b"0 0 0 1 k" not in data:
        errors.append("PDF does not contain the C:0 M:0 Y:0 K:100 command")
    media_box = (
        f"/MediaBox [0 0 {mm_to_points(resolved_layout.width_mm):.4f} "
        f"{mm_to_points(resolved_layout.height_mm):.4f}]"
    ).encode("ascii")
    if media_box not in data:
        errors.append("PDF page size does not match the requested layout")
    return VerificationResult(tuple(errors))
