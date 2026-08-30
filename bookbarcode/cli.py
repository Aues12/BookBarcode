"""Human-oriented command-line interface for the BookBarcode package."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .barcode import Barcode
from .layout import BarcodeLayout


def create_parser() -> argparse.ArgumentParser:
    """Create the standalone ``bookbarcode`` argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate verified ISBN-13 SVG and process-black CMYK PDF files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("isbn", help="Valid ISBN-13, with or without hyphens")
    parser.add_argument("--display", help="Assigned ISBN hyphenation shown above the bars")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("book-barcode"),
        help="Output base path; suffix is selected from --format",
    )
    parser.add_argument("--format", choices=("svg", "pdf", "both"), default="both")
    parser.add_argument("--preset", choices=("normal", "minimum"), default="normal")
    parser.add_argument("--width-mm", type=float)
    parser.add_argument("--height-mm", type=float)
    parser.add_argument("--bar-height-mm", type=float)
    parser.add_argument("--side-margin-mm", type=float)
    parser.add_argument("--left-margin-mm", type=float)
    parser.add_argument("--right-margin-mm", type=float)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing output only after the new artifact verifies",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the standalone CLI and return a process exit code."""
    parser = create_parser()
    args = parser.parse_args(argv)
    try:
        layout = BarcodeLayout.from_preset(
            args.preset,
            width_mm=args.width_mm,
            height_mm=args.height_mm,
            side_margin_mm=args.side_margin_mm,
            left_margin_mm=args.left_margin_mm,
            right_margin_mm=args.right_margin_mm,
            bar_height_mm=args.bar_height_mm,
        )
        barcode = Barcode(args.isbn, args.display, layout)
        targets: list[Path] = []
        if args.format in {"svg", "both"}:
            targets.append(
                barcode.write_svg(args.output.with_suffix(".svg"), overwrite=args.overwrite)
            )
        if args.format in {"pdf", "both"}:
            targets.append(
                barcode.write_pdf(args.output.with_suffix(".pdf"), overwrite=args.overwrite)
            )
    except (FileExistsError, FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    print("Created and verified:")
    for target in targets:
        print(f"- {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
