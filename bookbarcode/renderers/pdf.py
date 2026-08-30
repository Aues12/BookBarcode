"""Render ISBN-13 geometry as a minimal process-black CMYK PDF."""

from __future__ import annotations

from ..geometry import build_bar_geometry, build_hri_positions
from ..isbn import validate_display_text, validate_isbn13
from ..layout import BarcodeLayout


def render_pdf(
    isbn: str,
    display_text: str,
    layout: BarcodeLayout | None = None,
) -> bytes:
    """Return a self-contained PDF using only C:0 M:0 Y:0 K:100 for ink.

    The renderer writes a deliberately small PDF 1.4 object graph directly,
    avoiding a runtime PDF dependency and retaining exact control of color.
    """
    resolved_layout = layout or BarcodeLayout()
    normalized_isbn = validate_isbn13(isbn)
    normalized_display = validate_display_text(display_text, normalized_isbn)
    page_width = mm_to_points(resolved_layout.width_mm)
    page_height = mm_to_points(resolved_layout.height_mm)
    commands = [
        "q",
        "0 0 0 0 k",
        f"0 0 {page_width:.4f} {page_height:.4f} re f",
        "Q",
        "0 0 0 1 k",
    ]

    title_size = mm_to_points(resolved_layout.title_font_size_mm)
    title_width = len(normalized_display) * title_size * 0.52
    title_x = (page_width - title_width) / 2
    title_y = page_height - mm_to_points(resolved_layout.title_baseline_mm)
    commands.append(
        f"BT /F1 {title_size:.4f} Tf 1 0 0 1 {title_x:.4f} {title_y:.4f} "
        f"Tm ({_escape_pdf_text(normalized_display)}) Tj ET"
    )

    for bar in build_bar_geometry(normalized_isbn, resolved_layout):
        y = page_height - mm_to_points(resolved_layout.bar_top_mm + bar.height_mm)
        commands.append(
            f"{mm_to_points(bar.x_mm):.4f} {y:.4f} "
            f"{mm_to_points(bar.width_mm):.4f} {mm_to_points(bar.height_mm):.4f} re f"
        )

    hri_size = mm_to_points(resolved_layout.hri_font_size_mm)
    hri_y = page_height - mm_to_points(resolved_layout.hri_baseline_mm)
    for glyph in build_hri_positions(normalized_isbn, resolved_layout):
        glyph_x = mm_to_points(glyph.x_mm) - hri_size * 0.3
        commands.append(
            f"BT /F2 {hri_size:.4f} Tf 1 0 0 1 {glyph_x:.4f} {hri_y:.4f} "
            f"Tm ({glyph.text}) Tj ET"
        )

    content = ("\n".join(commands) + "\n").encode("ascii")
    objects = _pdf_objects(page_width, page_height, content)
    return _assemble_pdf(objects)


def mm_to_points(value: float) -> float:
    """Convert millimetres to PostScript points."""
    return value * 72.0 / 25.4


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_objects(page_width: float, page_height: float, content: bytes) -> list[bytes]:
    """Build the fixed PDF object graph used by the renderer."""
    return [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width:.4f} "
            f"{page_height:.4f}] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> "
            "/Contents 4 0 R >>"
        ).encode("ascii"),
        (
            b"<< /Length "
            + str(len(content)).encode("ascii")
            + b" >>\nstream\n"
            + content
            + b"endstream"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]


def _assemble_pdf(objects: list[bytes]) -> bytes:
    """Serialize PDF objects, cross-reference offsets, and trailer."""
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
