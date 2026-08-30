"""Generate the default SVG/PDF BookBarcode artifact pair."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from tool import write_barcode  # noqa: E402


with tempfile.TemporaryDirectory() as directory:
    result = write_barcode(
        "9786253798338",
        Path(directory) / "book-barcode",
        display_text="ISBN 978-625-379-833-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
