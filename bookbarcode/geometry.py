"""Build complete format-independent barcode geometry in millimetres."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .ean13 import GUARD_MODULES, encode_ean13, iter_black_runs
from .isbn import validate_display_text, validate_isbn13
from .layout import LayoutSpec, ResolvedBarcodeLayout, resolve_layout


@dataclass(frozen=True)
class BarGeometry:
    """Place one consecutive run of black EAN modules in millimetres."""

    module_start: int
    module_count: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    is_guard: bool


@dataclass(frozen=True)
class TextGeometry:
    """Place one text element by anchor and baseline in millimetres."""

    text: str
    x_mm: float
    baseline_mm: float
    font_size_mm: float
    anchor: Literal["middle"] = "middle"


@dataclass(frozen=True)
class BarcodeGeometry:
    """Contain every format-independent measurement needed by a renderer."""

    isbn: str
    display_text: str
    layout: ResolvedBarcodeLayout
    title: TextGeometry
    bars: tuple[BarGeometry, ...]
    hri_glyphs: tuple[TextGeometry, ...]


def build_barcode_geometry(
    isbn: str,
    display_text: str,
    layout: LayoutSpec | ResolvedBarcodeLayout | None = None,
) -> BarcodeGeometry:
    """Resolve layout and build complete title, bar, and HRI geometry."""
    normalized_isbn = validate_isbn13(isbn)
    normalized_display = validate_display_text(display_text, normalized_isbn)
    resolved = resolve_layout(layout)
    title = TextGeometry(
        text=normalized_display,
        x_mm=resolved.width_mm / 2,
        baseline_mm=resolved.title_baseline_mm,
        font_size_mm=resolved.title_font_size_mm,
    )
    return BarcodeGeometry(
        isbn=normalized_isbn,
        display_text=normalized_display,
        layout=resolved,
        title=title,
        bars=tuple(_build_bars(normalized_isbn, resolved)),
        hri_glyphs=tuple(_build_hri_glyphs(normalized_isbn, resolved)),
    )


def build_bar_geometry(
    isbn: str,
    layout: LayoutSpec | ResolvedBarcodeLayout,
) -> list[BarGeometry]:
    """Return bar geometry for compatibility with earlier internal callers."""
    normalized_isbn = validate_isbn13(isbn)
    return _build_bars(normalized_isbn, resolve_layout(layout))


def build_hri_positions(
    isbn: str,
    layout: LayoutSpec | ResolvedBarcodeLayout,
) -> list[TextGeometry]:
    """Return complete human-readable digit geometry for one ISBN."""
    normalized_isbn = validate_isbn13(isbn)
    return _build_hri_glyphs(normalized_isbn, resolve_layout(layout))


def _build_bars(
    isbn: str,
    layout: ResolvedBarcodeLayout,
) -> list[BarGeometry]:
    """Convert black module runs into physical rectangles."""
    bars: list[BarGeometry] = []
    for run_start, run_width in iter_black_runs(encode_ean13(isbn)):
        modules = range(run_start, run_start + run_width)
        is_guard = all(module in GUARD_MODULES for module in modules)
        height = layout.data_bar_height_mm
        if is_guard:
            height += layout.guard_extension_mm
        bars.append(
            BarGeometry(
                module_start=run_start,
                module_count=run_width,
                x_mm=layout.symbol_left_mm + run_start * layout.module_width_mm,
                y_mm=layout.bar_top_mm,
                width_mm=run_width * layout.module_width_mm,
                height_mm=height,
                is_guard=is_guard,
            )
        )
    return bars


def _build_hri_glyphs(
    isbn: str,
    layout: ResolvedBarcodeLayout,
) -> list[TextGeometry]:
    """Place all thirteen human-readable ISBN digits from EAN module groups."""
    start = layout.symbol_left_mm
    module_width = layout.module_width_mm
    x_positions = [max(start / 2, start - 4 * module_width)]
    x_positions.extend(start + (6.5 + 7 * index) * module_width for index in range(6))
    x_positions.extend(
        start + (53.5 + 7 * index) * module_width for index in range(6)
    )
    return [
        TextGeometry(
            text=digit,
            x_mm=x_mm,
            baseline_mm=layout.hri_baseline_mm,
            font_size_mm=layout.hri_font_size_mm,
        )
        for x_mm, digit in zip(x_positions, isbn)
    ]
