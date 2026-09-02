"""Agent-tools JSON adapter for the reusable :mod:`bookbarcode` package."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

from bookbarcode import Barcode, BarcodeLayout, LayoutSpec, ResolvedBarcodeLayout
from bookbarcode import resolve_layout as library_resolve_layout
from bookbarcode import verify_pdf as library_verify_pdf
from bookbarcode import verify_svg as library_verify_svg
from bookbarcode.io import validate_output_path


OperationHandler = Callable[..., dict[str, Any]]
PROCESS_BLACK = {"space": "CMYK", "c": 0, "m": 0, "y": 0, "k": 100}
OPERATIONS = {
    "generate_svg",
    "write_svg",
    "write_pdf",
    "write_barcode",
    "verify_svg",
    "verify_pdf",
}
LAYOUT_KEYS = {
    "preset",
    "width_mm",
    "height_mm",
    "side_margin_mm",
    "left_margin_mm",
    "right_margin_mm",
    "bar_height_mm",
}


def build_layout(layout: dict[str, Any] | LayoutSpec | None = None) -> LayoutSpec:
    """Translate a JSON-friendly layout object into a validated layout."""
    if layout is None:
        return BarcodeLayout()
    if isinstance(layout, LayoutSpec):
        return layout
    if not isinstance(layout, dict):
        raise TypeError("layout must be an object, LayoutSpec, BarcodeLayout, or null")
    unexpected = set(layout) - LAYOUT_KEYS
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(f"unexpected layout parameter(s): {names}")

    preset = layout.get("preset", "normal")
    numeric: dict[str, float | None] = {}
    for key in LAYOUT_KEYS - {"preset"}:
        value = layout.get(key)
        if value is None:
            numeric[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"layout.{key} must be a finite number or null")
        converted = float(value)
        if not math.isfinite(converted):
            raise ValueError(f"layout.{key} must be finite")
        numeric[key] = converted
    return BarcodeLayout.from_preset(
        preset,
        width_mm=numeric["width_mm"],
        height_mm=numeric["height_mm"],
        side_margin_mm=numeric["side_margin_mm"],
        left_margin_mm=numeric["left_margin_mm"],
        right_margin_mm=numeric["right_margin_mm"],
        bar_height_mm=numeric["bar_height_mm"],
    )


def generate_svg(
    isbn: str,
    display_text: str | None = None,
    layout: dict[str, Any] | LayoutSpec | None = None,
) -> dict[str, Any]:
    """Generate SVG and metadata without writing to the filesystem."""
    barcode = _barcode(isbn, display_text, layout)
    return {
        "isbn": barcode.isbn,
        "display_text": barcode.display_text,
        "svg": barcode.to_svg(),
        "layout": _layout_metadata(barcode.resolved_layout),
        "color": PROCESS_BLACK,
    }


def write_svg(
    isbn: str,
    output_path: str | Path,
    display_text: str | None = None,
    layout: dict[str, Any] | LayoutSpec | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write one verified SVG through the package's atomic writer."""
    barcode = _barcode(isbn, display_text, layout)
    path = barcode.write_svg(output_path, overwrite=overwrite)
    report = library_verify_svg(path, barcode.isbn, barcode.resolved_layout)
    return _artifact_result(barcode, path, "svg", report.to_dict())


def write_pdf(
    isbn: str,
    output_path: str | Path,
    display_text: str | None = None,
    layout: dict[str, Any] | LayoutSpec | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write one verified process-black PDF through the package API."""
    barcode = _barcode(isbn, display_text, layout)
    path = barcode.write_pdf(output_path, overwrite=overwrite)
    report = library_verify_pdf(
        path,
        barcode.resolved_layout,
        expected_isbn=barcode.isbn,
    )
    return _artifact_result(barcode, path, "pdf", report.to_dict())


def write_barcode(
    isbn: str,
    output_base: str | Path,
    formats: list[str] | None = None,
    display_text: str | None = None,
    layout: dict[str, Any] | LayoutSpec | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a preflighted SVG/PDF bundle using one validated Barcode."""
    selected = ["svg", "pdf"] if formats is None else formats
    _validate_formats(selected)
    barcode = _barcode(isbn, display_text, layout)
    base = _as_path(output_base)
    targets = {kind: base.with_suffix(f".{kind}") for kind in selected}
    for kind, target in targets.items():
        validate_output_path(target, f".{kind}", overwrite)

    outputs: list[dict[str, Any]] = []
    for kind in selected:
        if kind == "svg":
            path = barcode.write_svg(targets[kind], overwrite=overwrite)
            report = library_verify_svg(path, barcode.isbn, barcode.resolved_layout)
        else:
            path = barcode.write_pdf(targets[kind], overwrite=overwrite)
            report = library_verify_pdf(
                path,
                barcode.resolved_layout,
                expected_isbn=barcode.isbn,
            )
        outputs.append(_artifact_result(barcode, path, kind, report.to_dict()))
    return {"isbn": barcode.isbn, "outputs": outputs}


def verify_svg(
    path: str | Path,
    isbn: str,
    layout: dict[str, Any] | LayoutSpec | None = None,
) -> dict[str, Any]:
    """Return a JSON-friendly SVG verification report."""
    source = _validate_input_path(path, ".svg")
    resolved_layout = build_layout(layout)
    barcode = Barcode(isbn, layout=resolved_layout)
    report = library_verify_svg(source, barcode.isbn, resolved_layout)
    return {
        "path": str(source),
        "isbn": barcode.isbn,
        **report.to_dict(),
        "layout": _layout_metadata(resolved_layout),
    }


def verify_pdf(
    path: str | Path,
    layout: dict[str, Any] | LayoutSpec | None = None,
    *,
    isbn: str | None = None,
) -> dict[str, Any]:
    """Return a JSON-friendly PDF barcode verification report."""
    source = _validate_input_path(path, ".pdf")
    resolved_layout = build_layout(layout)
    report = library_verify_pdf(
        source,
        resolved_layout,
        expected_isbn=isbn,
    )
    result = {
        "path": str(source),
        **report.to_dict(),
        "layout": _layout_metadata(resolved_layout),
    }
    if isbn is not None:
        result["isbn"] = Barcode(isbn, layout=resolved_layout).isbn
    return result


def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """Execute one strict operation and return the standard tool envelope."""
    try:
        operation, params = _parse_request(input_data)
        handlers: dict[str, OperationHandler] = {
            "generate_svg": generate_svg,
            "write_svg": write_svg,
            "write_pdf": write_pdf,
            "write_barcode": write_barcode,
            "verify_svg": verify_svg,
            "verify_pdf": verify_pdf,
        }
        result = handlers[operation](**params)
        return {
            "success": True,
            "message": _success_message(operation, result),
            "result": result,
            "meta": {"operation": operation},
        }
    except Exception as exc:
        return _error_envelope(exc)


def main() -> None:
    """Read one JSON request from stdin and write one JSON response."""
    raw = sys.stdin.read().strip()
    if not raw:
        response = _error_envelope(ValueError("No input received"))
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        response = _error_envelope(ValueError(f"Invalid JSON: {exc.msg}"))
        print(json.dumps(response, ensure_ascii=False, indent=2))
        raise SystemExit(2) from exc
    response = run(payload)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    raise SystemExit(0 if response["success"] else 1)


def _barcode(
    isbn: str,
    display_text: str | None,
    layout: dict[str, Any] | LayoutSpec | None,
) -> Barcode:
    """Build the package facade from adapter-friendly inputs."""
    return Barcode(isbn, display_text, build_layout(layout))


def _layout_metadata(
    layout: LayoutSpec | ResolvedBarcodeLayout,
) -> dict[str, float]:
    """Expose resolved physical measurements for downstream consumers."""
    resolved = library_resolve_layout(layout)
    return {
        "width_mm": resolved.width_mm,
        "height_mm": resolved.height_mm,
        "left_margin_mm": resolved.left_quiet_zone_mm,
        "right_margin_mm": resolved.right_quiet_zone_mm,
        "module_width_mm": resolved.module_width_mm,
        "bar_height_mm": resolved.data_bar_height_mm,
    }


def _artifact_result(
    barcode: Barcode,
    path: Path,
    artifact_format: str,
    verification: dict[str, Any],
) -> dict[str, Any]:
    """Build the common JSON record for a written artifact."""
    return {
        "path": str(path),
        "format": artifact_format,
        "isbn": barcode.isbn,
        "display_text": barcode.display_text,
        "layout": _layout_metadata(barcode.resolved_layout),
        "color": PROCESS_BLACK,
        "verification": verification,
    }


def _validate_formats(formats: Any) -> None:
    """Validate bundle formats before any output is written."""
    if not isinstance(formats, list) or not formats:
        raise TypeError("formats must be a non-empty list")
    if any(not isinstance(item, str) for item in formats):
        raise TypeError("formats entries must be strings")
    if len(formats) != len(set(formats)):
        raise ValueError("formats must not contain duplicates")
    if set(formats) - {"svg", "pdf"}:
        raise ValueError("formats may contain only 'svg' and 'pdf'")


def _validate_input_path(value: str | Path, suffix: str) -> Path:
    """Validate a caller-selected input path without reading it."""
    path = _as_path(value)
    if path.suffix.lower() != suffix:
        raise ValueError(f"input path must end with {suffix}")
    if not path.is_file():
        raise FileNotFoundError(f"input file does not exist: {path}")
    return path


def _as_path(value: str | Path) -> Path:
    """Convert supported path inputs while rejecting ambiguous values."""
    if isinstance(value, Path):
        return value
    if not isinstance(value, str):
        raise TypeError("path must be a string or Path")
    return Path(value)


def _parse_request(input_data: Any) -> tuple[str, dict[str, Any]]:
    """Validate the operation envelope, required fields, and allowed fields."""
    if not isinstance(input_data, dict):
        raise TypeError("input_data must be an object")
    operation = input_data.get("operation")
    if operation not in OPERATIONS:
        raise ValueError(f"unknown operation: {operation}")
    params = input_data.get("params", {})
    if not isinstance(params, dict):
        raise TypeError("params must be an object")
    allowed = {
        "generate_svg": {"isbn", "display_text", "layout"},
        "write_svg": {"isbn", "output_path", "display_text", "layout", "overwrite"},
        "write_pdf": {"isbn", "output_path", "display_text", "layout", "overwrite"},
        "write_barcode": {"isbn", "output_base", "formats", "display_text", "layout", "overwrite"},
        "verify_svg": {"path", "isbn", "layout"},
        "verify_pdf": {"path", "layout", "isbn"},
    }[operation]
    unexpected = set(params) - allowed
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise ValueError(f"unexpected parameter(s) for {operation}: {names}")
    required = {
        "generate_svg": {"isbn"},
        "write_svg": {"isbn", "output_path"},
        "write_pdf": {"isbn", "output_path"},
        "write_barcode": {"isbn", "output_base"},
        "verify_svg": {"path", "isbn"},
        "verify_pdf": {"path"},
    }[operation]
    missing = required - set(params)
    if missing:
        raise ValueError(f"{operation} requires: {', '.join(sorted(missing))}")
    return operation, params


def _success_message(operation: str, result: dict[str, Any]) -> str:
    """Create a concise human-readable summary for the response envelope."""
    if operation == "generate_svg":
        return f"Generated ISBN-13 SVG for {result['isbn']}"
    if operation == "write_barcode":
        return f"Wrote and verified {len(result['outputs'])} barcode artifact(s)"
    if operation.startswith("write_"):
        return f"Wrote and verified barcode artifact at {result['path']}"
    return (
        "Barcode verification passed"
        if result["valid"]
        else "Barcode verification found errors"
    )


def _error_envelope(exc: Exception) -> dict[str, Any]:
    """Convert an exception to the repository's structured error envelope."""
    message = str(exc)
    return {
        "success": False,
        "message": message,
        "error": {"type": exc.__class__.__name__, "message": message},
    }


if __name__ == "__main__":
    main()
