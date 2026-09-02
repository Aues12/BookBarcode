"""Independent structural and barcode verification for BookBarcode PDF files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..ean13 import GUARD_MODULES, SYMBOL_MODULES, encode_ean13
from ..isbn import validate_isbn13
from ..layout import LayoutSpec, ResolvedBarcodeLayout, resolve_layout
from .result import VerificationResult


POINTS_PER_INCH = 72.0
MM_PER_INCH = 25.4
POINT_TOLERANCE = 0.001
NUMBER_PATTERN = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
RECTANGLE_PATTERN = re.compile(
    rf"^(?P<x>{NUMBER_PATTERN}) (?P<y>{NUMBER_PATTERN}) "
    rf"(?P<width>{NUMBER_PATTERN}) (?P<height>{NUMBER_PATTERN}) re f$"
)
TEXT_PATTERN = re.compile(
    rf"^BT /(?P<font>F[12]) (?P<size>{NUMBER_PATTERN}) Tf 1 0 0 1 "
    rf"(?P<x>{NUMBER_PATTERN}) (?P<y>{NUMBER_PATTERN}) Tm "
    r"\((?P<text>(?:\\.|[^\\)])*)\) Tj ET$"
)
MEDIA_BOX_PATTERN = re.compile(
    rf"/MediaBox\s*\[\s*(?P<x0>{NUMBER_PATTERN})\s+"
    rf"(?P<y0>{NUMBER_PATTERN})\s+(?P<x1>{NUMBER_PATTERN})\s+"
    rf"(?P<y1>{NUMBER_PATTERN})\s*\]"
)
CONTENT_STREAM_PATTERN = re.compile(
    rb"4 0 obj\s*<<\s*/Length\s+(?P<length>\d+)\s*>>\s*"
    rb"stream\r?\n(?P<content>.*?)endstream",
    re.DOTALL,
)


@dataclass(frozen=True)
class _PdfRectangle:
    """One filled PDF rectangle expressed in PostScript points."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class _PdfText:
    """One text-showing command extracted from the PDF content stream."""

    font: str
    size: float
    x: float
    y: float
    text: str


def verify_pdf(
    path: str | Path,
    layout: LayoutSpec | ResolvedBarcodeLayout | None = None,
    *,
    expected_isbn: str | None = None,
) -> VerificationResult:
    """Verify PDF structure, ink, ISBN text, EAN modules, and physical geometry.

    ``expected_isbn`` is optional for compatibility with earlier callers. When
    omitted, the verifier validates the ISBN extracted from the thirteen
    human-readable PDF glyphs and checks the bars against it. When supplied, it
    additionally requires both text and bars to encode that ISBN.
    """
    source = Path(path)
    resolved_layout = resolve_layout(layout)
    normalized_expected = (
        None if expected_isbn is None else validate_isbn13(expected_isbn)
    )
    try:
        data = source.read_bytes()
    except OSError as exc:
        return VerificationResult((f"unable to read PDF: {exc}",))

    errors: list[str] = []
    if not data.startswith(b"%PDF-1.4") or not data.rstrip().endswith(b"%%EOF"):
        errors.append("PDF framing is invalid")

    document = data.decode("latin-1")
    _verify_page_size(document, resolved_layout, errors)
    content = _extract_content_stream(data, errors)
    if content is None:
        return VerificationResult(tuple(errors))

    try:
        lines = [line.strip() for line in content.decode("ascii").splitlines()]
    except UnicodeDecodeError:
        errors.append("PDF content stream is not ASCII")
        return VerificationResult(tuple(errors))

    rectangles, texts = _parse_content_commands(lines, resolved_layout, errors)
    isbn = _verify_text(texts, resolved_layout, normalized_expected, errors)
    _verify_bars(rectangles, resolved_layout, normalized_expected or isbn, errors)
    return VerificationResult(tuple(errors))


def _verify_page_size(
    document: str,
    layout: ResolvedBarcodeLayout,
    errors: list[str],
) -> None:
    """Compare the serialized MediaBox with independently converted dimensions."""
    match = MEDIA_BOX_PATTERN.search(document)
    if match is None:
        errors.append("PDF page size is missing")
        return
    coordinates = tuple(
        float(match.group(name)) for name in ("x0", "y0", "x1", "y1")
    )
    expected = (
        0.0,
        0.0,
        _mm_to_points(layout.width_mm),
        _mm_to_points(layout.height_mm),
    )
    if any(
        not _points_close(actual, target)
        for actual, target in zip(coordinates, expected)
    ):
        errors.append("PDF page size does not match the requested layout")


def _extract_content_stream(data: bytes, errors: list[str]) -> bytes | None:
    """Return object 4's uncompressed stream and validate its declared length."""
    match = CONTENT_STREAM_PATTERN.search(data)
    if match is None:
        errors.append("PDF content stream is missing or malformed")
        return None
    content = match.group("content")
    declared_length = int(match.group("length"))
    if declared_length != len(content):
        errors.append("PDF content stream length is incorrect")
    return content


def _parse_content_commands(
    lines: list[str],
    layout: ResolvedBarcodeLayout,
    errors: list[str],
) -> tuple[list[_PdfRectangle], list[_PdfText]]:
    """Parse the deliberately narrow command language emitted by BookBarcode."""
    page_width = _mm_to_points(layout.width_mm)
    page_height = _mm_to_points(layout.height_mm)
    if lines[:2] != ["q", "0 0 0 0 k"]:
        errors.append("PDF background graphics state or white fill is invalid")

    background = RECTANGLE_PATTERN.fullmatch(lines[2]) if len(lines) > 2 else None
    if background is None:
        errors.append("PDF white background rectangle is missing or malformed")
    else:
        values = tuple(
            float(background.group(name))
            for name in ("x", "y", "width", "height")
        )
        expected_background = (0.0, 0.0, page_width, page_height)
        if any(
            not _points_close(actual, expected)
            for actual, expected in zip(values, expected_background)
        ):
            errors.append("PDF white background does not match the page")

    if len(lines) < 5 or lines[3] != "Q":
        errors.append("PDF background graphics state is not restored")
    if len(lines) < 5 or lines[4] != "0 0 0 1 k":
        errors.append("PDF ink is not set to C:0 M:0 Y:0 K:100")
    if lines.count("0 0 0 1 k") != 1:
        errors.append("PDF process-black command count is invalid")

    rectangles: list[_PdfRectangle] = []
    texts: list[_PdfText] = []
    for line in lines[5:]:
        rectangle = RECTANGLE_PATTERN.fullmatch(line)
        if rectangle is not None:
            rectangles.append(
                _PdfRectangle(
                    *(
                        float(rectangle.group(name))
                        for name in ("x", "y", "width", "height")
                    )
                )
            )
            continue
        text = TEXT_PATTERN.fullmatch(line)
        if text is not None:
            texts.append(
                _PdfText(
                    font=text.group("font"),
                    size=float(text.group("size")),
                    x=float(text.group("x")),
                    y=float(text.group("y")),
                    text=_unescape_pdf_text(text.group("text")),
                )
            )
            continue
        if line:
            errors.append(
                "PDF content contains an unsupported or malformed drawing command"
            )
    return rectangles, texts


def _verify_text(
    texts: list[_PdfText],
    layout: ResolvedBarcodeLayout,
    expected_isbn: str | None,
    errors: list[str],
) -> str | None:
    """Verify title and OCR glyph content and geometry, returning a valid ISBN."""
    titles = [text for text in texts if text.font == "F1"]
    glyphs = [text for text in texts if text.font == "F2"]
    if len(titles) != 1:
        errors.append("PDF must contain exactly one ISBN title")
    if len(glyphs) != 13:
        errors.append("PDF must contain exactly thirteen human-readable ISBN digits")

    readable = "".join(glyph.text for glyph in glyphs)
    if any(len(glyph.text) != 1 or not glyph.text.isdigit() for glyph in glyphs):
        errors.append("PDF human-readable ISBN glyphs must each contain one digit")

    parsed_isbn: str | None = None
    if len(readable) == 13 and readable.isdigit():
        try:
            parsed_isbn = validate_isbn13(readable)
        except (TypeError, ValueError):
            errors.append("PDF human-readable digits are not a valid ISBN-13")
    if expected_isbn is not None and readable != expected_isbn:
        errors.append("PDF human-readable digits do not match the expected ISBN")

    if len(titles) == 1:
        title_digits = "".join(
            character for character in titles[0].text if character.isdigit()
        )
        if title_digits != readable:
            errors.append("PDF title digits do not match the human-readable ISBN")
        _verify_title_geometry(titles[0], layout, errors)

    _verify_hri_geometry(glyphs, layout, errors)
    return parsed_isbn


def _verify_title_geometry(
    title: _PdfText,
    layout: ResolvedBarcodeLayout,
    errors: list[str],
) -> None:
    """Check title font size and baseline without using renderer helpers."""
    page_width = _mm_to_points(layout.width_mm)
    page_height = _mm_to_points(layout.height_mm)
    expected_size = _mm_to_points(layout.title_font_size_mm)
    expected_width = len(title.text) * expected_size * 0.52
    expected_x = (page_width - expected_width) / 2
    expected_y = page_height - _mm_to_points(layout.title_baseline_mm)
    if not _points_close(title.size, expected_size):
        errors.append("PDF title font size does not match the requested layout")
    if not _points_close(title.x, expected_x):
        errors.append("PDF title x-position does not match the requested layout")
    if not _points_close(title.y, expected_y):
        errors.append("PDF title baseline does not match the requested layout")


def _verify_hri_geometry(
    glyphs: list[_PdfText],
    layout: ResolvedBarcodeLayout,
    errors: list[str],
) -> None:
    """Check all readable-digit positions using an independent EAN formula."""
    if len(glyphs) != 13:
        return
    page_height = _mm_to_points(layout.height_mm)
    font_size = _mm_to_points(layout.hri_font_size_mm)
    expected_y = page_height - _mm_to_points(layout.hri_baseline_mm)
    start = layout.symbol_left_mm
    module_width = layout.module_width_mm
    expected_x_mm = [max(start / 2, start - 4 * module_width)]
    expected_x_mm.extend(
        start + (6.5 + 7 * index) * module_width for index in range(6)
    )
    expected_x_mm.extend(
        start + (53.5 + 7 * index) * module_width for index in range(6)
    )

    for glyph, x_mm in zip(glyphs, expected_x_mm):
        expected_x = _mm_to_points(x_mm) - font_size * 0.3
        if not _points_close(glyph.size, font_size):
            errors.append("a PDF human-readable digit has an incorrect font size")
        if not _points_close(glyph.x, expected_x):
            errors.append("a PDF human-readable digit has an incorrect x-position")
        if not _points_close(glyph.y, expected_y):
            errors.append("a PDF human-readable digit has an incorrect baseline")


def _verify_bars(
    rectangles: list[_PdfRectangle],
    layout: ResolvedBarcodeLayout,
    isbn: str | None,
    errors: list[str],
) -> None:
    """Reconstruct the 95 EAN modules from serialized rectangle geometry."""
    reconstructed = ["0"] * SYMBOL_MODULES
    module_width = layout.module_width_mm
    symbol_start = layout.symbol_left_mm
    page_height = _mm_to_points(layout.height_mm)
    guard_count = 0

    for rectangle in rectangles:
        x_mm = _points_to_mm(rectangle.x)
        width_mm = _points_to_mm(rectangle.width)
        measured_start = (x_mm - symbol_start) / module_width
        module_start = round(measured_start)
        measured_count = width_mm / module_width
        module_count = round(measured_count)

        if abs(measured_start - module_start) > 0.001:
            errors.append("a PDF bar x-position does not align to an EAN module")
        if module_count < 1:
            errors.append("a PDF bar has no measurable modules")
            continue
        if abs(measured_count - module_count) > 0.001:
            errors.append("a PDF bar width is not an integer number of modules")

        modules = range(module_start, module_start + module_count)
        is_guard = all(module in GUARD_MODULES for module in modules)
        expected_height_mm = layout.data_bar_height_mm
        if is_guard:
            expected_height_mm += layout.guard_extension_mm
            guard_count += 1
        expected_y = page_height - _mm_to_points(
            layout.bar_top_mm + expected_height_mm
        )
        if not _points_close(
            rectangle.height, _mm_to_points(expected_height_mm)
        ):
            errors.append("a PDF bar height does not match its guard/data role")
        if not _points_close(rectangle.y, expected_y):
            errors.append("a PDF bar y-position does not match the requested layout")

        for module in modules:
            if not 0 <= module < SYMBOL_MODULES:
                errors.append("a PDF bar extends outside the 95-module symbol")
            elif reconstructed[module] == "1":
                errors.append("PDF bar modules overlap")
            else:
                reconstructed[module] = "1"

    if isbn is not None and "".join(reconstructed) != encode_ean13(isbn):
        errors.append("PDF bar modules do not encode the required ISBN")
    if guard_count != 6:
        errors.append("the six PDF guard bars are not all present")


def _unescape_pdf_text(value: str) -> str:
    """Decode the PDF literal-string escapes emitted by the renderer."""
    output: list[str] = []
    index = 0
    translations = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
    }
    while index < len(value):
        character = value[index]
        if character != "\\" or index + 1 >= len(value):
            output.append(character)
            index += 1
            continue
        escaped = value[index + 1]
        output.append(translations.get(escaped, escaped))
        index += 2
    return "".join(output)


def _mm_to_points(value: float) -> float:
    """Convert millimetres independently from the PDF renderer."""
    return value * POINTS_PER_INCH / MM_PER_INCH


def _points_to_mm(value: float) -> float:
    """Convert serialized PostScript points back to millimetres."""
    return value * MM_PER_INCH / POINTS_PER_INCH


def _points_close(actual: float, expected: float) -> bool:
    """Allow only the renderer's four-decimal point serialization tolerance."""
    return abs(actual - expected) <= POINT_TOLERANCE
