"""Render ISBN-13 geometry as editable, millimetre-sized SVG."""

from __future__ import annotations

from html import escape

from ..geometry import build_barcode_geometry
from ..layout import LayoutSpec, ResolvedBarcodeLayout


CMYK_BLACK = "0,0,0,100"
SVG_CMYK_BLACK = "device-cmyk(0% 0% 0% 100%, #000000)"


def render_svg(
    isbn: str,
    display_text: str,
    layout: LayoutSpec | ResolvedBarcodeLayout | None = None,
) -> str:
    """Return a complete SVG document for a validated ISBN-13.

    All physical dimensions use millimetres. The SVG includes a black RGB
    fallback plus device-CMYK intent metadata for compatible applications.
    """
    geometry = build_barcode_geometry(isbn, display_text, layout)
    resolved_layout = geometry.layout
    normalized_isbn = geometry.isbn
    normalized_display = geometry.display_text
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
            f'x="{_mm(geometry.title.x_mm)}" '
            f'y="{_mm(geometry.title.baseline_mm)}" '
            f'text-anchor="{geometry.title.anchor}" '
            'font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{_mm(geometry.title.font_size_mm)}">'
            f'{escape(normalized_display)}</text>'
        ),
        (
            f'  <g id="bars" class="ink-black" data-cmyk="{CMYK_BLACK}" '
            'shape-rendering="crispEdges">'
        ),
    ]
    for bar in geometry.bars:
        kind = "guard" if bar.is_guard else "data"
        lines.append(
            f'    <rect class="{kind}" data-module="{bar.module_start}" '
            f'x="{_mm(bar.x_mm)}" y="{_mm(bar.y_mm)}" '
            f'width="{_mm(bar.width_mm)}" height="{_mm(bar.height_mm)}"/>'
        )
    lines.extend(
        [
            "  </g>",
            (
                f'  <g id="human-readable" class="ink-black" data-cmyk="{CMYK_BLACK}" '
                'font-family="OCR-B, OCRB, Arial, Helvetica, sans-serif" '
                f'font-size="{_mm(geometry.hri_glyphs[0].font_size_mm)}" '
                f'text-anchor="{geometry.hri_glyphs[0].anchor}">'
            ),
        ]
    )
    for glyph in geometry.hri_glyphs:
        lines.append(
            f'    <text x="{_mm(glyph.x_mm)}" '
            f'y="{_mm(glyph.baseline_mm)}">{glyph.text}</text>'
        )
    lines.extend(["  </g>", "</svg>", ""])
    return "\n".join(lines)


def format_mm(value: float) -> str:
    """Format a millimetre value without insignificant trailing zeroes."""
    return _mm(value)


def _mm(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")
