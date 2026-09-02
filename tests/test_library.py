"""Unit and integration tests for the public BookBarcode package API."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

TOOL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_DIR))

from bookbarcode import (  # noqa: E402
    Barcode,
    BarcodeLayout,
    calculate_check_digit,
    encode_ean13,
    normalize_isbn,
    verify_pdf,
    verify_svg,
)

ISBN = "9786253798338"
DISPLAY = "ISBN 978-625-379-833-8"
KNOWN_PATTERN = (
    "101011101100010010000101001001101110010111101010101000100111010010010001"
    "00001010000101001000101"
)


class IsbnTests(unittest.TestCase):
    """Verify normalization, checksum, and canonical EAN module encoding."""

    def test_normalization_and_known_check_digit(self) -> None:
        self.assertEqual(normalize_isbn(f"ISBN-13: {DISPLAY[5:]}"), ISBN)
        self.assertEqual(calculate_check_digit(ISBN[:12]), "8")

    def test_ean_encoding_matches_known_95_module_vector(self) -> None:
        self.assertEqual(encode_ean13(ISBN), KNOWN_PATTERN)
        self.assertEqual(len(KNOWN_PATTERN), 95)

    def test_invalid_checksum_is_rejected_not_corrected(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected 8, received 7"):
            Barcode("9786253798337")


class LayoutTests(unittest.TestCase):
    """Verify KDY presets, margin precedence, and physical constraints."""

    def test_normal_and_minimum_presets(self) -> None:
        normal = BarcodeLayout.from_preset("normal")
        minimum = BarcodeLayout.from_preset("minimum")
        self.assertEqual((normal.width_mm, normal.height_mm), (35.0, 19.0))
        self.assertEqual((minimum.width_mm, minimum.height_mm), (26.0, 14.0))

    def test_individual_margin_overrides_symmetric_margin(self) -> None:
        layout = BarcodeLayout(
            width_mm=38,
            height_mm=20,
            side_margin_mm=3,
            left_margin_mm=3.8,
        )
        self.assertEqual(layout.resolved_left_margin_mm, 3.8)
        self.assertEqual(layout.resolved_right_margin_mm, 3)

    def test_impossible_dimensions_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            BarcodeLayout(width_mm=0)
        with self.assertRaisesRegex(ValueError, "complete barcode width"):
            BarcodeLayout(width_mm=35, left_margin_mm=20, right_margin_mm=15)
        with self.assertRaisesRegex(ValueError, "finite"):
            BarcodeLayout(width_mm=float("nan"))
        with self.assertRaisesRegex(TypeError, "finite number"):
            BarcodeLayout(width_mm=True)

    def test_standard_quiet_zone_minima_are_required(self) -> None:
        """Reject custom margins smaller than the EAN-13 11X/7X minima."""
        with self.assertRaisesRegex(ValueError, "left quiet zone.*11X"):
            BarcodeLayout(width_mm=35, left_margin_mm=3, right_margin_mm=3)
        with self.assertRaisesRegex(ValueError, "right quiet zone.*7X"):
            BarcodeLayout(width_mm=35, left_margin_mm=4, right_margin_mm=2)


class BarcodeRenderingTests(unittest.TestCase):
    """Verify shared geometry, renderers, safe writes, and verification."""

    def test_facade_generates_svg_and_process_black_pdf(self) -> None:
        barcode = Barcode(ISBN)
        svg = barcode.to_svg()
        pdf = barcode.to_pdf()
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.get("width"), "35mm")
        self.assertIn(DISPLAY, svg)
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertIn(b"0 0 0 1 k", pdf)

    def test_custom_layout_is_shared_by_svg_and_pdf(self) -> None:
        layout = BarcodeLayout(
            width_mm=38,
            height_mm=20,
            left_margin_mm=3.8,
            right_margin_mm=2.5,
            bar_height_mm=12.5,
        )
        barcode = Barcode(ISBN, DISPLAY, layout)
        root = ElementTree.fromstring(barcode.to_svg())
        pdf = barcode.to_pdf()
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        first_bar = root.find(".//svg:g[@id='bars']/svg:rect", namespace)
        assert first_bar is not None
        self.assertEqual(root.get("width"), "38mm")
        self.assertEqual(first_bar.get("x"), "3.8")
        self.assertIn(b"/MediaBox [0 0 107.7165 56.6929]", pdf)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.pdf"
            path.write_bytes(pdf)
            self.assertTrue(verify_pdf(path, layout, expected_isbn=ISBN).valid)

    def test_atomic_writers_create_verifiable_artifacts(self) -> None:
        barcode = Barcode(ISBN, DISPLAY)
        with tempfile.TemporaryDirectory() as directory:
            svg_path = barcode.write_svg(Path(directory) / "barcode.svg")
            pdf_path = barcode.write_pdf(Path(directory) / "barcode.pdf")
            self.assertTrue(verify_svg(svg_path, ISBN).valid)
            self.assertTrue(verify_pdf(pdf_path).valid)

    def test_writer_refuses_implicit_overwrite(self) -> None:
        barcode = Barcode(ISBN)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "barcode.svg"
            path.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                barcode.write_svg(path)
            self.assertEqual(path.read_text(encoding="utf-8"), "existing")

    def test_svg_verifier_reports_tampered_modules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "barcode.svg"
            changed = Barcode(ISBN).to_svg().replace(
                'data-module="0"', 'data-module="1"', 1
            )
            path.write_text(changed, encoding="utf-8")
            report = verify_svg(path, ISBN)
            self.assertFalse(report.valid)
            self.assertIn("bar modules do not encode the expected ISBN", report.errors)

    def test_pdf_verifier_reports_tampered_page_size_and_color(self) -> None:
        """Reject page and ink mutations in the serialized PDF artifact."""
        original = Barcode(ISBN).to_pdf()
        mutations = {
            "page size": (
                original.replace(
                    b"/MediaBox [0 0 99.2126 53.8583]",
                    b"/MediaBox [0 0 98.2126 53.8583]",
                    1,
                ),
                "PDF page size does not match the requested layout",
            ),
            "process black": (
                original.replace(b"0 0 0 1 k", b"0 0 0 0 k", 1),
                "PDF ink is not set to C:0 M:0 Y:0 K:100",
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, (content, expected_error) in mutations.items():
                with self.subTest(name=name):
                    path = Path(directory) / f"{name.replace(' ', '-')}.pdf"
                    path.write_bytes(content)
                    report = verify_pdf(path, expected_isbn=ISBN)
                    self.assertFalse(report.valid)
                    self.assertIn(expected_error, report.errors)

    def test_pdf_verifier_reports_tampered_bar_geometry(self) -> None:
        """Reconstruct modules from PDF rectangles and reject a changed bar."""
        original = Barcode(ISBN).to_pdf()
        changed, replacements = re.subn(
            rb"\n(\d+\.\d{4} \d+\.\d{4} )\d+\.\d{4}( \d+\.\d{4} re f)\n",
            rb"\n\g<1>0.0000\g<2>\n",
            original,
            count=1,
        )
        self.assertEqual(replacements, 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered-bar.pdf"
            path.write_bytes(changed)
            report = verify_pdf(path, expected_isbn=ISBN)
            self.assertFalse(report.valid)
            self.assertIn("a PDF bar has no measurable modules", report.errors)
            self.assertIn(
                "PDF bar modules do not encode the required ISBN",
                report.errors,
            )

    def test_pdf_verifier_reports_tampered_human_readable_digits(self) -> None:
        """Reject disagreement among expected ISBN, title, glyphs, and bars."""
        original = Barcode(ISBN).to_pdf()
        prefix, separator, suffix = original.rpartition(b"(8) Tj ET")
        self.assertTrue(separator)
        changed = prefix + b"(7) Tj ET" + suffix
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tampered-text.pdf"
            path.write_bytes(changed)
            report = verify_pdf(path, expected_isbn=ISBN)
            self.assertFalse(report.valid)
            self.assertIn(
                "PDF human-readable digits do not match the expected ISBN",
                report.errors,
            )
            self.assertIn(
                "PDF title digits do not match the human-readable ISBN",
                report.errors,
            )

    def test_pdf_verifier_checks_the_callers_expected_isbn(self) -> None:
        """Require serialized text and bars to match an explicitly expected ISBN."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "barcode.pdf"
            path.write_bytes(Barcode(ISBN).to_pdf())
            report = verify_pdf(path, expected_isbn="9786059681131")
            self.assertFalse(report.valid)
            self.assertIn(
                "PDF human-readable digits do not match the expected ISBN",
                report.errors,
            )
            self.assertIn(
                "PDF bar modules do not encode the required ISBN",
                report.errors,
            )


if __name__ == "__main__":
    unittest.main()
