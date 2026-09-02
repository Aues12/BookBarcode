"""Physical barcode layout expressed entirely in millimetres."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .ean13 import SYMBOL_MODULES


LEFT_QUIET_MODULES = 11
RIGHT_QUIET_MODULES = 7
GUARD_EXTENSION_MODULES = 5
NORMAL_SIZE_MM = (35.0, 19.0)
MINIMUM_SIZE_MM = (26.0, 14.0)


@dataclass(frozen=True)
class BarcodeLayout:
    """Describe page, margin, and bar dimensions for one barcode.

    Explicit left or right margins override ``side_margin_mm`` independently.
    When no margin is supplied, the standard 11X/7X quiet zones determine the
    margins and module width.
    """

    width_mm: float = NORMAL_SIZE_MM[0]
    height_mm: float = NORMAL_SIZE_MM[1]
    side_margin_mm: float | None = None
    left_margin_mm: float | None = None
    right_margin_mm: float | None = None
    bar_height_mm: float | None = None

    def __post_init__(self) -> None:
        """Reject non-physical dimensions before rendering starts."""
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
        _ = self.module_width_mm
        self._validate_quiet_zones()
        if self.bar_height <= 0:
            raise ValueError("bar height must be greater than zero")
        lowest_bar = self.bar_top_mm + self.bar_height + self.guard_extension_mm
        if lowest_bar >= self.hri_baseline_mm:
            raise ValueError(
                "bars do not fit above the human-readable text; increase height "
                "or reduce bar_height_mm"
            )

    @classmethod
    def from_preset(
        cls,
        preset: str = "normal",
        *,
        width_mm: float | None = None,
        height_mm: float | None = None,
        **kwargs: float | None,
    ) -> "BarcodeLayout":
        """Construct a layout from ``normal`` or ``minimum`` KDY dimensions."""
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
        """Return the caller-supplied left margin before quiet-zone fallback."""
        return self.left_margin_mm if self.left_margin_mm is not None else self.side_margin_mm

    @property
    def effective_right_margin_mm(self) -> float | None:
        """Return the caller-supplied right margin before quiet-zone fallback."""
        return self.right_margin_mm if self.right_margin_mm is not None else self.side_margin_mm

    @property
    def module_width_mm(self) -> float:
        """Calculate the physical width of one EAN module."""
        left = self.effective_left_margin_mm
        right = self.effective_right_margin_mm
        if left is None and right is None:
            return self.width_mm / (
                LEFT_QUIET_MODULES + SYMBOL_MODULES + RIGHT_QUIET_MODULES
            )
        if left is None:
            assert right is not None
            available = self.width_mm - right
            divisor = LEFT_QUIET_MODULES + SYMBOL_MODULES
        elif right is None:
            available = self.width_mm - left
            divisor = SYMBOL_MODULES + RIGHT_QUIET_MODULES
        else:
            available = self.width_mm - left - right
            divisor = SYMBOL_MODULES
        if available <= 0:
            raise ValueError("margins occupy the complete barcode width")
        return available / divisor

    @property
    def resolved_left_margin_mm(self) -> float:
        """Return the final left quiet area in millimetres."""
        explicit = self.effective_left_margin_mm
        return explicit if explicit is not None else LEFT_QUIET_MODULES * self.module_width_mm

    @property
    def resolved_right_margin_mm(self) -> float:
        """Return the final right quiet area in millimetres."""
        explicit = self.effective_right_margin_mm
        return explicit if explicit is not None else RIGHT_QUIET_MODULES * self.module_width_mm

    def _validate_quiet_zones(self) -> None:
        """Require custom margins to preserve the EAN-13 quiet-zone minima."""
        module_width = self.module_width_mm
        minimum_left = LEFT_QUIET_MODULES * module_width
        minimum_right = RIGHT_QUIET_MODULES * module_width
        if self.resolved_left_margin_mm < minimum_left and not math.isclose(
            self.resolved_left_margin_mm, minimum_left, abs_tol=1e-12
        ):
            raise ValueError(
                "left quiet zone must be at least 11 modules (11X); "
                "increase left_margin_mm or reduce the symbol width"
            )
        if self.resolved_right_margin_mm < minimum_right and not math.isclose(
            self.resolved_right_margin_mm, minimum_right, abs_tol=1e-12
        ):
            raise ValueError(
                "right quiet zone must be at least 7 modules (7X); "
                "increase right_margin_mm or reduce the symbol width"
            )

    @property
    def title_baseline_mm(self) -> float:
        """Return the title baseline measured from the top edge."""
        return self.height_mm * 0.14

    @property
    def bar_top_mm(self) -> float:
        """Return the vertical start of bars measured from the top edge."""
        return self.height_mm * 0.19

    @property
    def hri_baseline_mm(self) -> float:
        """Return the baseline for human-readable digits."""
        return self.height_mm * 0.94

    @property
    def bar_height(self) -> float:
        """Return the data-bar height, using a proportional default."""
        return self.bar_height_mm if self.bar_height_mm is not None else self.height_mm * 0.62

    @property
    def guard_extension_mm(self) -> float:
        """Return the extra height applied to guard bars."""
        return GUARD_EXTENSION_MODULES * self.module_width_mm

    @property
    def title_font_size_mm(self) -> float:
        """Return the proportional title font size."""
        return self.height_mm * 0.11

    @property
    def hri_font_size_mm(self) -> float:
        """Return the proportional human-readable digit font size."""
        return self.height_mm * 0.145
