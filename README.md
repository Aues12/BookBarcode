# BookBarcode

BookBarcode generates deterministic ISBN-13/EAN-13 barcodes for books.
It creates editable SVG files and print-ready PDF files, and checks each
artifact before writing it.

- **PDF** is the recommended final format for printing. It uses true process
  black: `C:0 M:0 Y:0 K:100`.
- **SVG** is useful for vector editing and preview. It includes CMYK intent
  metadata, although colour handling ultimately depends on the SVG application.

The package has no runtime third-party dependencies and supports Python 3.9+.

## Quick start

Install from the repository during development:

```bash
python3 -m pip install -e .
```

Generate both formats with a valid ISBN-13:

```bash
bookbarcode 9786253798338
```

This creates and verifies these files in the current directory:

```text
book-barcode.svg
book-barcode.pdf
```

The command refuses to replace an existing file unless you add `--overwrite`.
It writes a temporary sibling, verifies it, then atomically installs it at the
target path.

You can also run the command from this repository without installing it:

```bash
python3 -m bookbarcode.cli 9786253798338
```

## Common tasks

Create a print-ready PDF at a chosen path:

```bash
bookbarcode 9786253798338 \
  --format pdf \
  --output output/book-barcode
```

Use the smallest bundled layout when space is constrained:

```bash
bookbarcode 9786253798338 \
  --preset minimum \
  --output output/small-book-barcode
```

Use assigned ISBN hyphenation in the visible heading:

```bash
bookbarcode 9786059681131 \
  --display "ISBN 978-605-9681-13-1" \
  --output output/book-barcode
```

Without `--display`, BookBarcode uses a readable `3-3-3-3-1` fallback. This is
not an assertion about official ISBN registrant ranges; provide the assigned
hyphenation when it matters.

## Layout and output

| Preset | Dimensions | Best for |
|---|---:|---|
| `normal` (default) | 35 × 19 mm | Typical book barcodes |
| `minimum` | 26 × 14 mm | Space-constrained covers |

By default, BookBarcode writes both SVG and PDF. Use `--format svg` or
`--format pdf` to select one. `--output` sets the base path, so
`--output output/barcode` produces `output/barcode.svg` and/or
`output/barcode.pdf`; the directory must already exist.

Custom total dimensions, data-bar height, and either shared or independent
side margins are available. The detailed commands and the full option reference
are in the [English user guide](docs/USAGE.md).

## Python API

Generate content without writing files:

```python
from bookbarcode import Barcode

barcode = Barcode("9786253798338")
svg_text = barcode.to_svg()
pdf_bytes = barcode.to_pdf()
```

Write verified artifacts explicitly:

```python
from bookbarcode import Barcode, BarcodeLayout

layout = BarcodeLayout(
    width_mm=38,
    height_mm=20,
    side_margin_mm=3,
    bar_height_mm=12.5,
)
barcode = Barcode(
    "9786253798338",
    display_text="ISBN 978-625-379-833-8",
    layout=layout,
)
barcode.write_svg("book-barcode.svg")
barcode.write_pdf("book-barcode.pdf")
```

## Agent-tools JSON interface

Agent tools can use BookBarcode as a tool by sending a JSON request envelope to
`isbn_barcode.py` over standard input. The adapter translates that request to
the same package API used by Python and the CLI; it does not implement barcode
rules independently.

```bash
printf '%s' '{
  "operation": "write_barcode",
  "params": {
    "isbn": "9786253798338",
    "output_base": "/tmp/book-barcode",
    "layout": {"preset": "normal"}
  }
}' | python3 isbn_barcode.py
```

Supported operations are `generate_svg`, `write_svg`, `write_pdf`,
`write_barcode`, `verify_svg`, and `verify_pdf`. See [SKILL.yaml](SKILL.yaml)
for the machine-readable request and response contract.

## Documentation

- [English user guide](docs/USAGE.md) — installation, complete CLI reference,
  custom layouts, printing guidance, common errors, and examples.
- [Türkçe kullanım kılavuzu](docs/KULLANIM.md)
- [KDY size and colour reference notes](docs/KDY-REFERENCE-NOTES.md)
- [KDY ölçü ve renk referans notları](docs/KDY-REFERANS-NOTLARI.md)

## Quality and printing

BookBarcode verifies the serialized SVG/PDF structure, dimensions, barcode
modules, guard bars, readable digits, and colour intent where applicable.
For production, keep quiet zones clear, do not scale the barcode
non-proportionally or rasterize it, and scan a printed sample after printer
preflight.

Run the test suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

BookBarcode is released under the [MIT License](LICENSE).
