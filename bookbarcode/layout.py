"""Resolve caller layout intent into complete physical barcode measurements."""

from __future__ import annotations

import math
from dataclasses import dataclass, fields
from typing import TypeVar

from .ean13 import SYMBOL_MODULES


LEFT_QUIET_MODULES = 11
RIGHT_QUIET_MODULES = 7
GUARD_EXTENSION_MODULES = 5
NORMAL_SIZE_MM = (35.0, 19.0)
MINIMUM_SIZE_MM = (26.0, 14.0)

TITLE_BASELINE_HEIGHT_RATIO = 0.14
BAR_TOP_HEIGHT_RATIO = 0.19
HRI_BASELINE_HEIGHT_RATIO = 0.94
DATA_BAR_HEIGHT_RATIO = 0.62
TITLE_FONT_HEIGHT_RATIO = 0.11
HRI_FONT_HEIGHT_RATIO = 0.145


LayoutSpecT = TypeVar("LayoutSpecT", bound="LayoutSpec")


@dataclass(frozen=True)
class LayoutSpec:
    """Describe caller-selected page, margin, and optional bar measurements.

    Values use millimetres. ``None`` means the resolver must select the
    documented standard or proportional fallback. An explicit left or right
    margin overrides ``side_margin_mm`` for that side.
    """

    width_mm: float = NORMAL_SIZE_MM[0]
    height_mm: float = NORMAL_SIZE_MM[1]
    side_margin_mm: float | None = None
    left_margin_mm: float | None = None
    right_margin_mm: float | None = None
    bar_height_mm: float | None = None

    def __post_init__(self) -> None:
        """Reject malformed source values before dependency resolution."""
        values = (
            ("width", self.width_mm),
            ("height", self.height_mm),
            ("side margin", self.side_margin_mm),
            ("left margin", self.left_margin_mm),
            ("right margin", self.right_margin_mm),
            ("bar height", self.bar_height_mm),
        )
        for name, value in values:
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a finite number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        for name, value in (("width", self.width_mm), ("height", self.height_mm)):
            if value <= 0:
                raise ValueError(f"barcode {name} must be greater than zero")
        for name, value in (
            ("side margin", self.side_margin_mm),
            ("left margin", self.left_margin_mm),
            ("right margin", self.right_margin_mm),
            ("bar height", self.bar_height_mm),
        ):
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")

    @classmethod
    def from_preset(
        cls: type[LayoutSpecT],
        preset: str = "normal",
        *,
        width_mm: float | None = None,
        height_mm: float | None = None,
        **kwargs: float | None,
    ) -> LayoutSpecT:
        """Construct a specification from ``normal`` or ``minimum`` KDY size."""
        if preset not in {"normal", "minimum"}:
            raise ValueError("preset must be 'normal' or 'minimum'")
        preset_width, preset_height = (
            NORMAL_SIZE_MM if preset == "normal" else MINIMUM_SIZE_MM
        )
        return cls(
            width_mm=preset_width if width_mm is None else width_mm,
            height_mm=preset_height if height_mm is None else height_mm,
            **kwargs,
        )

    @property
    def effective_left_margin_mm(self) -> float | None:
        """Return the selected left-margin source before standard fallback."""
        return (
            self.left_margin_mm
            if self.left_margin_mm is not None
            else self.side_margin_mm
        )

    @property
    def effective_right_margin_mm(self) -> float | None:
        """Return the selected right-margin source before standard fallback."""
        return (
            self.right_margin_mm
            if self.right_margin_mm is not None
            else self.side_margin_mm
        )

    def resolve(self) -> "ResolvedBarcodeLayout":
        """Resolve all dependencies and validate the resulting measurements."""
        return resolve_layout(self)

    # Compatibility properties keep the established BarcodeLayout API usable
    # while all calculations remain owned by the resolver below.
    @property
    def module_width_mm(self) -> float:
        """Return resolved EAN module width in millimetres."""
        return self.resolve().module_width_mm

    @property
    def resolved_left_margin_mm(self) -> float:
        """Return resolved left quiet-zone width in millimetres."""
        return self.resolve().left_quiet_zone_mm

    @property
    def resolved_right_margin_mm(self) -> float:
        """Return resolved right quiet-zone width in millimetres."""
        return self.resolve().right_quiet_zone_mm

    @property
    def title_baseline_mm(self) -> float:
        """Return resolved title baseline measured from the top edge."""
        return self.resolve().title_baseline_mm

    @property
    def bar_top_mm(self) -> float:
        """Return resolved vertical bar start measured from the top edge."""
        return self.resolve().bar_top_mm

    @property
    def hri_baseline_mm(self) -> float:
        """Return resolved human-readable digit baseline in millimetres."""
        return self.resolve().hri_baseline_mm

    @property
    def bar_height(self) -> float:
        """Return resolved data-bar height in millimetres."""
        return self.resolve().data_bar_height_mm

    @property
    def guard_extension_mm(self) -> float:
        """Return resolved guard-bar extension in millimetres."""
        return self.resolve().guard_extension_mm

    @property
    def title_font_size_mm(self) -> float:
        """Return resolved title font size in millimetres."""
        return self.resolve().title_font_size_mm

    @property
    def hri_font_size_mm(self) -> float:
        """Return resolved human-readable digit font size in millimetres."""
        return self.resolve().hri_font_size_mm


@dataclass(frozen=True)
class BarcodeLayout(LayoutSpec):
    """Backward-compatible eagerly validated layout specification.

    New code may use :class:`LayoutSpec` to keep caller intent distinct from
    :class:`ResolvedBarcodeLayout`. Existing ``BarcodeLayout`` construction
    continues to reject an invalid resolved layout immediately.
    """

    def __post_init__(self) -> None:
        """Validate source values and eagerly resolve all dependencies."""
        super().__post_init__()
        resolve_layout(self)


@dataclass(frozen=True)
class ResolvedBarcodeLayout:
    """Hold one complete, immutable result of the measurement dependency DAG."""

    width_mm: float
    height_mm: float
    module_width_mm: float
    left_quiet_zone_mm: float
    symbol_left_mm: float
    symbol_width_mm: float
    symbol_right_mm: float
    right_quiet_zone_mm: float
    title_baseline_mm: float
    title_font_size_mm: float
    bar_top_mm: float
    data_bar_height_mm: float
    data_bar_bottom_mm: float
    guard_extension_mm: float
    guard_bar_bottom_mm: float
    hri_baseline_mm: float
    hri_font_size_mm: float

    def __post_init__(self) -> None:
        """Reject non-finite or internally inconsistent resolved snapshots."""
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"resolved {item.name} must be a finite number")
            if not math.isfinite(value):
                raise ValueError(f"resolved {item.name} must be finite")
        _validate_resolved_layout(self)

    @property
    def resolved_left_margin_mm(self) -> float:
        """Return the legacy name for the left quiet-zone width."""
        return self.left_quiet_zone_mm

    @property
    def resolved_right_margin_mm(self) -> float:
        """Return the legacy name for the right quiet-zone width."""
        return self.right_quiet_zone_mm

    @property
    def bar_height(self) -> float:
        """Return the legacy name for the data-bar height."""
        return self.data_bar_height_mm

    def to_dict(self) -> dict[str, float]:
        """Return every resolved measurement as a JSON-friendly mapping."""
        return {item.name: getattr(self, item.name) for item in fields(self)}


def resolve_layout(
    spec: LayoutSpec | ResolvedBarcodeLayout | None = None,
) -> ResolvedBarcodeLayout:
    """Resolve the measurement DAG in documented topological order.

    Resolution selects margin sources, derives module width and horizontal
    bounds, derives vertical measurements, and finally checks constraints.
    Passing an already resolved layout is an idempotent operation.
    """
    if isinstance(spec, ResolvedBarcodeLayout):
        return spec
    selected = LayoutSpec() if spec is None else spec
    if not isinstance(selected, LayoutSpec):
        raise TypeError("layout must be a LayoutSpec or ResolvedBarcodeLayout")

    # 1. Select the authoritative optional margin sources.
    left_source = selected.effective_left_margin_mm
    right_source = selected.effective_right_margin_mm

    # 2. Resolve X from total width, the 95-module symbol, and margin policy.
    module_width = _resolve_module_width(
        selected.width_mm,
        left_source,
        right_source,
    )

    # 3. Resolve horizontal measurements and symbol bounds.
    left_quiet = (
        LEFT_QUIET_MODULES * module_width
        if left_source is None
        else left_source
    )
    right_quiet = (
        RIGHT_QUIET_MODULES * module_width
        if right_source is None
        else right_source
    )
    symbol_left = left_quiet
    symbol_width = SYMBOL_MODULES * module_width
    symbol_right = symbol_left + symbol_width

    # 4. Resolve vertical measurements from page height or explicit bar height.
    title_baseline = selected.height_mm * TITLE_BASELINE_HEIGHT_RATIO
    title_font_size = selected.height_mm * TITLE_FONT_HEIGHT_RATIO
    bar_top = selected.height_mm * BAR_TOP_HEIGHT_RATIO
    data_bar_height = (
        selected.height_mm * DATA_BAR_HEIGHT_RATIO
        if selected.bar_height_mm is None
        else selected.bar_height_mm
    )
    guard_extension = GUARD_EXTENSION_MODULES * module_width
    data_bar_bottom = bar_top + data_bar_height
    guard_bar_bottom = data_bar_bottom + guard_extension
    hri_baseline = selected.height_mm * HRI_BASELINE_HEIGHT_RATIO
    hri_font_size = selected.height_mm * HRI_FONT_HEIGHT_RATIO

    resolved = ResolvedBarcodeLayout(
        width_mm=selected.width_mm,
        height_mm=selected.height_mm,
        module_width_mm=module_width,
        left_quiet_zone_mm=left_quiet,
        symbol_left_mm=symbol_left,
        symbol_width_mm=symbol_width,
        symbol_right_mm=symbol_right,
        right_quiet_zone_mm=right_quiet,
        title_baseline_mm=title_baseline,
        title_font_size_mm=title_font_size,
        bar_top_mm=bar_top,
        data_bar_height_mm=data_bar_height,
        data_bar_bottom_mm=data_bar_bottom,
        guard_extension_mm=guard_extension,
        guard_bar_bottom_mm=guard_bar_bottom,
        hri_baseline_mm=hri_baseline,
        hri_font_size_mm=hri_font_size,
    )
    return resolved


def _resolve_module_width(
    width_mm: float,
    left_margin_mm: float | None,
    right_margin_mm: float | None,
) -> float:
    """Resolve one EAN module width for every supported margin-source case."""
    if left_margin_mm is None and right_margin_mm is None:
        available = width_mm
        divisor = LEFT_QUIET_MODULES + SYMBOL_MODULES + RIGHT_QUIET_MODULES
    elif left_margin_mm is None:
        assert right_margin_mm is not None
        available = width_mm - right_margin_mm
        divisor = LEFT_QUIET_MODULES + SYMBOL_MODULES
    elif right_margin_mm is None:
        available = width_mm - left_margin_mm
        divisor = SYMBOL_MODULES + RIGHT_QUIET_MODULES
    else:
        available = width_mm - left_margin_mm - right_margin_mm
        divisor = SYMBOL_MODULES
    if available <= 0:
        raise ValueError("margins occupy the complete barcode width")
    return available / divisor


def _validate_resolved_layout(layout: ResolvedBarcodeLayout) -> None:
    """Check graph constraints after every dependent measurement is available."""
    if layout.width_mm <= 0 or layout.height_mm <= 0 or layout.module_width_mm <= 0:
        raise ValueError("resolved page and module dimensions must be greater than zero")
    if not math.isclose(
        layout.symbol_left_mm,
        layout.left_quiet_zone_mm,
        abs_tol=1e-12,
    ):
        raise ValueError("symbol left edge must equal the left quiet-zone width")
    if not math.isclose(
        layout.symbol_width_mm,
        SYMBOL_MODULES * layout.module_width_mm,
        abs_tol=1e-12,
    ):
        raise ValueError("symbol width must contain exactly 95 modules")
    if not math.isclose(
        layout.symbol_right_mm,
        layout.symbol_left_mm + layout.symbol_width_mm,
        abs_tol=1e-12,
    ):
        raise ValueError("symbol right edge does not match its dependencies")
    proportional_measurements = (
        (
            "title baseline",
            layout.title_baseline_mm,
            layout.height_mm * TITLE_BASELINE_HEIGHT_RATIO,
        ),
        (
            "title font size",
            layout.title_font_size_mm,
            layout.height_mm * TITLE_FONT_HEIGHT_RATIO,
        ),
        ("bar top", layout.bar_top_mm, layout.height_mm * BAR_TOP_HEIGHT_RATIO),
        (
            "HRI baseline",
            layout.hri_baseline_mm,
            layout.height_mm * HRI_BASELINE_HEIGHT_RATIO,
        ),
        (
            "HRI font size",
            layout.hri_font_size_mm,
            layout.height_mm * HRI_FONT_HEIGHT_RATIO,
        ),
    )
    for name, actual, expected in proportional_measurements:
        if not math.isclose(actual, expected, abs_tol=1e-12):
            raise ValueError(f"resolved {name} does not match its height dependency")
    minimum_left = LEFT_QUIET_MODULES * layout.module_width_mm
    minimum_right = RIGHT_QUIET_MODULES * layout.module_width_mm
    if layout.left_quiet_zone_mm < minimum_left and not math.isclose(
        layout.left_quiet_zone_mm,
        minimum_left,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "left quiet zone must be at least 11 modules (11X); "
            "increase left_margin_mm or reduce the symbol width"
        )
    if layout.right_quiet_zone_mm < minimum_right and not math.isclose(
        layout.right_quiet_zone_mm,
        minimum_right,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "right quiet zone must be at least 7 modules (7X); "
            "increase right_margin_mm or reduce the symbol width"
        )
    if layout.data_bar_height_mm <= 0:
        raise ValueError("bar height must be greater than zero")
    if not math.isclose(
        layout.data_bar_bottom_mm,
        layout.bar_top_mm + layout.data_bar_height_mm,
        abs_tol=1e-12,
    ):
        raise ValueError("data-bar bottom does not match its dependencies")
    if not math.isclose(
        layout.guard_extension_mm,
        GUARD_EXTENSION_MODULES * layout.module_width_mm,
        abs_tol=1e-12,
    ):
        raise ValueError("guard extension must equal 5X")
    if not math.isclose(
        layout.guard_bar_bottom_mm,
        layout.data_bar_bottom_mm + layout.guard_extension_mm,
        abs_tol=1e-12,
    ):
        raise ValueError("guard-bar bottom does not match its dependencies")
    if layout.guard_bar_bottom_mm >= layout.hri_baseline_mm:
        raise ValueError(
            "bars do not fit above the human-readable text; increase height "
            "or reduce bar_height_mm"
        )
    expected_width = (
        layout.left_quiet_zone_mm
        + layout.symbol_width_mm
        + layout.right_quiet_zone_mm
    )
    if not math.isclose(expected_width, layout.width_mm, abs_tol=1e-12):
        raise ValueError("resolved horizontal measurements do not fill the page width")
