"""Contract tests for the agent-tools JSON adapter."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from tool import build_layout, generate_svg, run, write_barcode  # noqa: E402

ISBN = "9786253798338"


class IsbnBarcodeAdapterTests(unittest.TestCase):
    """Verify strict requests, JSON envelopes, and bundle preflight."""

    def invoke_json_tool(
        self,
        payload: object,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        """Invoke the real stdin/stdout entrypoint and decode its response."""
        completed = subprocess.run(
            [sys.executable, str(TOOL_DIR / "isbn_barcode.py")],
            input=json.dumps(payload),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return completed, json.loads(completed.stdout)

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
        with self.assertRaisesRegex(ValueError, "left quiet zone.*11X"):
            build_layout(
                {"width_mm": 35, "left_margin_mm": 3, "right_margin_mm": 3}
            )

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
        completed, response = self.invoke_json_tool(
            {"operation": "generate_svg", "params": {"isbn": ISBN}}
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(response["success"])
        self.assertEqual(response["meta"], {"operation": "generate_svg"})

    def test_json_entrypoint_exercises_every_file_operation(self) -> None:
        """Run all five file operations through the executable JSON surface."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svg_path = root / "single.svg"
            pdf_path = root / "single.pdf"
            bundle_base = root / "bundle"

            requests = [
                (
                    "write_svg",
                    {
                        "operation": "write_svg",
                        "params": {"isbn": ISBN, "output_path": str(svg_path)},
                    },
                ),
                (
                    "write_pdf",
                    {
                        "operation": "write_pdf",
                        "params": {"isbn": ISBN, "output_path": str(pdf_path)},
                    },
                ),
                (
                    "write_barcode",
                    {
                        "operation": "write_barcode",
                        "params": {
                            "isbn": ISBN,
                            "output_base": str(bundle_base),
                        },
                    },
                ),
                (
                    "verify_svg",
                    {
                        "operation": "verify_svg",
                        "params": {"path": str(svg_path), "isbn": ISBN},
                    },
                ),
                (
                    "verify_pdf",
                    {
                        "operation": "verify_pdf",
                        "params": {"path": str(pdf_path), "isbn": ISBN},
                    },
                ),
            ]
            for operation, request in requests:
                with self.subTest(operation=operation):
                    completed, response = self.invoke_json_tool(request)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertTrue(response["success"], response)
                    self.assertEqual(response["meta"], {"operation": operation})
                    if operation.startswith("verify_"):
                        self.assertTrue(response["result"]["valid"])

            self.assertTrue(svg_path.is_file())
            self.assertTrue(pdf_path.is_file())
            self.assertTrue(bundle_base.with_suffix(".svg").is_file())
            self.assertTrue(bundle_base.with_suffix(".pdf").is_file())

    def test_json_entrypoint_returns_structured_operation_errors(self) -> None:
        """Cover missing, invalid, conflicting, and unsafe request parameters."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "existing.pdf"
            existing.write_bytes(b"existing")
            cases = [
                (
                    "missing parameter",
                    {"operation": "write_svg", "params": {"isbn": ISBN}},
                    "ValueError",
                ),
                (
                    "wrong suffix",
                    {
                        "operation": "write_svg",
                        "params": {
                            "isbn": ISBN,
                            "output_path": str(root / "wrong.pdf"),
                        },
                    },
                    "ValueError",
                ),
                (
                    "existing output",
                    {
                        "operation": "write_pdf",
                        "params": {
                            "isbn": ISBN,
                            "output_path": str(existing),
                        },
                    },
                    "FileExistsError",
                ),
                (
                    "invalid ISBN",
                    {
                        "operation": "generate_svg",
                        "params": {"isbn": "9786253798337"},
                    },
                    "ValueError",
                ),
                (
                    "missing input",
                    {
                        "operation": "verify_svg",
                        "params": {"path": str(root / "missing.svg"), "isbn": ISBN},
                    },
                    "FileNotFoundError",
                ),
            ]
            for name, request, error_type in cases:
                with self.subTest(name=name):
                    completed, response = self.invoke_json_tool(request)
                    self.assertEqual(completed.returncode, 1)
                    self.assertFalse(response["success"])
                    self.assertEqual(response["error"]["type"], error_type)

    def test_json_entrypoint_reports_invalid_artifact_separately(self) -> None:
        """Keep operation success distinct from artifact verification validity."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered.svg"
            path.write_text(
                generate_svg(ISBN)["svg"].replace(
                    'data-module="0"',
                    'data-module="1"',
                    1,
                ),
                encoding="utf-8",
            )
            completed, response = self.invoke_json_tool(
                {
                    "operation": "verify_svg",
                    "params": {"path": str(path), "isbn": ISBN},
                }
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue(response["success"])
            self.assertFalse(response["result"]["valid"])
            self.assertTrue(response["result"]["errors"])

    def test_json_entrypoint_rejects_empty_and_malformed_json(self) -> None:
        """Reserve exit code 2 for failures before a request can be parsed."""
        for name, content in (("empty", ""), ("malformed", "{bad json")):
            with self.subTest(name=name):
                completed = subprocess.run(
                    [sys.executable, str(TOOL_DIR / "isbn_barcode.py")],
                    input=content,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2)
                response = json.loads(completed.stdout)
                self.assertFalse(response["success"])
                self.assertEqual(response["error"]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
