"""High-level, immutable facade for common BookBarcode workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .io import write_verified_atomically
from .isbn import format_display_isbn, validate_display_text, validate_isbn13
from .layout import BarcodeLayout, LayoutSpec, ResolvedBarcodeLayout, resolve_layout
from .renderers import render_pdf, render_svg
from .verification import verify_pdf, verify_svg


@dataclass(frozen=True)
class Barcode:
    """Represent one validated ISBN-13, its label, and physical layout.

    The object is immutable and performs all semantic validation at creation.
    Rendering methods are side-effect free; ``write_*`` methods make file
    mutation explicit and verify a temporary artifact before replacement.
    """

    isbn: str
    display_text: str | None = None
    layout: LayoutSpec = field(default_factory=BarcodeLayout)
    _resolved_layout: ResolvedBarcodeLayout = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Normalize ISBN and display text while preserving immutability."""
        if not isinstance(self.layout, LayoutSpec):
            raise TypeError("layout must be a LayoutSpec or BarcodeLayout")
        normalized_isbn = validate_isbn13(self.isbn)
        display = (
            format_display_isbn(normalized_isbn)
            if self.display_text is None
            else validate_display_text(self.display_text, normalized_isbn)
        )
        object.__setattr__(self, "isbn", normalized_isbn)
        object.__setattr__(self, "display_text", display)
        object.__setattr__(self, "_resolved_layout", resolve_layout(self.layout))

    @property
    def resolved_layout(self) -> ResolvedBarcodeLayout:
        """Return the complete immutable layout used by geometry and renderers."""
        return self._resolved_layout

    def to_svg(self) -> str:
        """Render the barcode as editable SVG text without writing a file."""
        assert self.display_text is not None
        return render_svg(self.isbn, self.display_text, self.resolved_layout)

    def to_pdf(self) -> bytes:
        """Render the barcode as process-black CMYK PDF bytes."""
        assert self.display_text is not None
        return render_pdf(self.isbn, self.display_text, self.resolved_layout)

    def write_svg(self, path: str | Path, *, overwrite: bool = False) -> Path:
        """Atomically write and verify an SVG artifact."""
        return write_verified_atomically(
            path,
            self.to_svg().encode("utf-8"),
            suffix=".svg",
            verifier=lambda candidate: verify_svg(
                candidate,
                self.isbn,
                self.resolved_layout,
            ),
            overwrite=overwrite,
        )

    def write_pdf(self, path: str | Path, *, overwrite: bool = False) -> Path:
        """Atomically write and verify a process-black PDF artifact."""
        return write_verified_atomically(
            path,
            self.to_pdf(),
            suffix=".pdf",
            verifier=lambda candidate: verify_pdf(
                candidate,
                self.resolved_layout,
                expected_isbn=self.isbn,
            ),
            overwrite=overwrite,
        )
