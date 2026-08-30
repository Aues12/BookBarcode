"""End-to-end tests for the standalone package CLI."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parents[1]
ISBN = "9786253798338"


class BookBarcodeCliTests(unittest.TestCase):
    """Verify that ``python -m bookbarcode.cli`` writes both artifacts."""

    def test_cli_generates_default_svg_and_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "book"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "bookbarcode.cli",
                    ISBN,
                    "--output",
                    str(output),
                ],
                cwd=TOOL_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(output.with_suffix(".svg").is_file())
            self.assertTrue(output.with_suffix(".pdf").is_file())


if __name__ == "__main__":
    unittest.main()
