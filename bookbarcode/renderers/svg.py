"""Render ISBN-13 geometry as editable, millimetre-sized SVG."""

from __future__ import annotations

from html import escape

from ..geometry import build_bar_geometry, build_hri_positions
from ..isbn import validate_display_text, validate_isbn13
from ..layout import BarcodeLayout


CMYK_BLACK = "0,0,0,100"
SVG_CMYK_BLACK = "device-cmyk(0% 0% 0% 100%, #000000)"


def render_svg(
    isbn: str,
    display_text: str,
    layout: BarcodeLayout | None = None,
) -> str:
    """Return a complete SVG document for a validated ISBN-13.

    All physical dimensions use millimetres. The SVG includes a black RGB
    fallback plus device-CMYK intent metadata for compatible applications.
    """
    resolved_layout = layout or BarcodeLayout()
    normalized_isbn = validate_isbn13(isbn)
    normalized_display = validate_display_text(display_text, normalized_isbn)
    width = _mm(resolved_layout.width_mm)
    height = _mm(resolved_layout.height_mm)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
            f'width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}" '
            'role="img" aria-labelledby="title desc">'
        ),
        f'  <title id="title">{escape(normalized_display)} barcode</title>',
        (
            f'  <desc id="desc">EAN-13 ISBN {escape(normalized_isbn)}; '
            f'C:0 M:0 Y:0 K:100; module {_mm(resolved_layout.module_width_mm)} mm.</desc>'
        ),
        f'  <style>.ink-black {{ fill: #000000; fill: {SVG_CMYK_BLACK}; }}</style>',
        f'  <rect width="{width}" height="{height}" fill="#ffffff"/>',
        (
            f'  <text id="isbn-title" class="ink-black" data-cmyk="{CMYK_BLACK}" '
            f'x="{_mm(resolved_layout.width_mm / 2)}" '
            f'y="{_mm(resolved_layout.title_baseline_mm)}" text-anchor="middle" '
            'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{_mm(resolved_layout.title_font_size_mm)}">'
            f'{escape(normalized_display)}</text>'
        ),
        (
            f'  <g id="bars" class="ink-black" data-cmyk="{CMYK_BLACK}" '
            'shape-rendering="crispEdges">'
        ),
    ]
    for bar in build_bar_geometry(normalized_isbn, resolved_layout):
        kind = "guard" if bar.is_guard else "data"
        lines.append(
            f'    <rect class="{kind}" data-module="{bar.module_start}" '
            f'x="{_mm(bar.x_mm)}" y="{_mm(resolved_layout.bar_top_mm)}" '
            f'width="{_mm(bar.width_mm)}" height="{_mm(bar.height_mm)}"/>'
        )
    lines.extend(
        [
            "  </g>",
            (
                f'  <g id="human-readable" class="ink-black" data-cmyk="{CMYK_BLACK}" '
                'font-family="OCR-B, OCRB, Arial, Helvetica, sans-serif" '
                f'font-size="{_mm(resolved_layout.hri_font_size_mm)}" text-anchor="middle">'
            ),
        ]
    )
    for glyph in build_hri_positions(normalized_isbn, resolved_layout):
        lines.append(
            f'    <text x="{_mm(glyph.x_mm)}" '
            f'y="{_mm(resolved_layout.hri_baseline_mm)}">{glyph.text}</text>'
        )
    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def format_mm(value: float) -> str:
    """Format a millimetre value without insignificant trailing zeroes."""
    return _mm(value)


def _mm(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")
