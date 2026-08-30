"""Format-independent physical geometry for bars and readable digits."""

from __future__ import annotations

from dataclasses import dataclass

from .ean13 import GUARD_MODULES, encode_ean13, iter_black_runs
from .layout import BarcodeLayout


@dataclass(frozen=True)
class BarGeometry:
    """Physical placement of one consecutive run of black EAN modules."""

    module_start: int
    module_count: int
    x_mm: float
    width_mm: float
    height_mm: float
    is_guard: bool


@dataclass(frozen=True)
class TextGeometry:
    """Horizontal placement of one human-readable ISBN digit."""

    x_mm: float
    text: str


def build_bar_geometry(isbn: str, layout: BarcodeLayout) -> list[BarGeometry]:
    """Convert an ISBN's black module runs into millimetre geometry."""
    module_width = layout.module_width_mm
    symbol_start = layout.resolved_left_margin_mm
    bars: list[BarGeometry] = []
    for run_start, run_width in iter_black_runs(encode_ean13(isbn)):
        modules = range(run_start, run_start + run_width)
        is_guard = all(module in GUARD_MODULES for module in modules)
        height = layout.bar_height
        if is_guard:
            height += layout.guard_extension_mm
        bars.append(
            BarGeometry(
                module_start=run_start,
                module_count=run_width,
                x_mm=symbol_start + run_start * module_width,
                width_mm=run_width * module_width,
                height_mm=height,
                is_guard=is_guard,
            )
        )
    return bars


def build_hri_positions(isbn: str, layout: BarcodeLayout) -> list[TextGeometry]:
    """Position all thirteen human-readable digits below the symbol."""
    start = layout.resolved_left_margin_mm
    module_width = layout.module_width_mm
    positions = [
        TextGeometry(max(start / 2, start - 4 * module_width), isbn[0])
    ]
    positions.extend(
        TextGeometry(start + (6.5 + 7 * index) * module_width, digit)
        for index, digit in enumerate(isbn[1:7])
    )
    positions.extend(
        TextGeometry(start + (53.5 + 7 * index) * module_width, digit)
        for index, digit in enumerate(isbn[7:])
    )
    return positions
