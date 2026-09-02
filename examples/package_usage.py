"""Use BookBarcode as a normal Python package without the agent adapter."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from bookbarcode import Barcode, BarcodeLayout  # noqa: E402


layout = BarcodeLayout.from_preset("normal", side_margin_mm=3.5)
barcode = Barcode(
    "9786253798338",
    display_text="ISBN 978-625-379-833-8",
    layout=layout,
)

with tempfile.TemporaryDirectory() as directory:
    output_base = Path(directory) / "book-barcode"
    svg_path = barcode.write_svg(output_base.with_suffix(".svg"))
    pdf_path = barcode.write_pdf(output_base.with_suffix(".pdf"))
    print(svg_path)
    print(pdf_path)
