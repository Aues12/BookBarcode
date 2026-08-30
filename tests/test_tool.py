"""Contract tests for the agent-tools JSON adapter."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from tool import build_layout, generate_svg, run, write_barcode  # noqa: E402

ISBN = "9786253798338"


class IsbnBarcodeAdapterTests(unittest.TestCase):
    """Verify strict requests, JSON envelopes, and bundle preflight."""

    def test_generate_svg_returns_resolved_metadata(self) -> None:
        result = generate_svg(ISBN, layout={"preset": "minimum"})
        self.assertEqual(result["isbn"], ISBN)
        self.assertEqual(result["layout"]["width_mm"], 26.0)
        self.assertIn("<svg", result["svg"])

    def test_layout_rejects_unknown_and_nonfinite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "unexpected layout"):
            build_layout({"dpi": 300})
        with self.assertRaisesRegex(ValueError, "finite"):
            build_layout({"width_mm": float("inf")})

    def test_bundle_writes_both_formats(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "barcode"
            result = write_barcode(ISBN, base)
            self.assertEqual(len(result["outputs"]), 2)
            self.assertTrue(base.with_suffix(".svg").is_file())
            self.assertTrue(base.with_suffix(".pdf").is_file())

    def test_bundle_preflight_prevents_partial_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "barcode"
            base.with_suffix(".pdf").write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                write_barcode(ISBN, base)
            self.assertFalse(base.with_suffix(".svg").exists())

    def test_bundle_rejects_empty_or_duplicate_formats(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "barcode"
            with self.assertRaisesRegex(TypeError, "non-empty"):
                write_barcode(ISBN, base, formats=[])
            with self.assertRaisesRegex(ValueError, "duplicates"):
                write_barcode(ISBN, base, formats=["svg", "svg"])

    def test_run_returns_structured_error_for_unknown_parameter(self) -> None:
        response = run(
            {
                "operation": "generate_svg",
                "params": {"isbn": ISBN, "unexpected": True},
            }
        )
        self.assertFalse(response["success"])
        self.assertEqual(response["error"]["type"], "ValueError")

    def test_json_entrypoint_uses_standard_response_envelope(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(TOOL_DIR / "isbn_barcode.py")],
            input=json.dumps({"operation": "generate_svg", "params": {"isbn": ISBN}}),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = json.loads(completed.stdout)
        self.assertTrue(response["success"])
        self.assertEqual(response["meta"]["operation"], "generate_svg")


if __name__ == "__main__":
    unittest.main()
