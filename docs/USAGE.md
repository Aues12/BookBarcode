# BookBarcode User Guide

BookBarcode creates EAN-13 barcodes from valid ISBN-13 values. One core package
powers three interfaces:

- the Python package;
- the human-oriented \`bookbarcode\` command-line program;
- the JSON stdin/stdout adapter for agent tools.

It generates two artifact types:

- **PDF** is the recommended print-delivery format. Bars and text use true
  process black: \`C:0 M:0 Y:0 K:100\`.
- **SVG** is intended for vector editing and preview. It records CMYK intent,
  but PDF remains preferable for final printing because SVG applications can
  manage colour differently.

See the [KDY size and colour reference notes](KDY-REFERENCE-NOTES.md) for the
basis of the bundled presets. The original Turkish guide remains available as
[Turkish documentation](KULLANIM.md).

## Requirements

- Python 3.9 or later
- No runtime third-party Python dependencies

Check the installed Python version:

\`\`\`bash
python3 --version
\`\`\`

## Installation

Change to the BookBarcode repository root:

\`\`\`bash
cd /path/to/BookBarcode
\`\`\`

For development, create and activate a virtual environment, then install the
package in editable mode:

\`\`\`bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
\`\`\`

In Windows PowerShell, activate the environment with:

\`\`\`powershell
.venv\Scripts\Activate.ps1
\`\`\`

After installation:

\`\`\`bash
bookbarcode --help
\`\`\`

You can also run the CLI directly from the repository root without installing:

\`\`\`bash
python3 -m bookbarcode.cli --help
\`\`\`

## Basic CLI usage

Pass the ISBN as the positional argument:

\`\`\`bash
bookbarcode 9786253798338
\`\`\`

By default, BookBarcode creates these verified files in the current directory:

\`\`\`text
book-barcode.svg
book-barcode.pdf
\`\`\`

It validates the ISBN check digit and each generated artifact. An existing
output is never replaced unless \`--overwrite\` is explicitly supplied.

## ISBN display hyphenation

Without \`--display\`, the human-readable heading uses a legible \`3-3-3-3-1\`
fallback:

\`\`\`text
ISBN 978-625-379-833-8
\`\`\`

This does not determine official ISBN registrant ranges. If the assigned
hyphenation is different, pass it explicitly:

\`\`\`bash
bookbarcode 9786059681131 \
  --display "ISBN 978-605-9681-13-1"
\`\`\`

The digits in the heading must match the encoded ISBN exactly; only hyphen
placement may differ.

## KDY layout presets

| Preset | Barcode width | Barcode height |
|---|---:|---:|
| \`normal\` | 35 mm | 19 mm |
| \`minimum\` | 26 mm | 14 mm |

The normal size is the default:

\`\`\`bash
bookbarcode 9786253798338 --preset normal
\`\`\`

Use the minimum size only where necessary:

\`\`\`bash
bookbarcode 9786253798338 --preset minimum
\`\`\`

Reducing a barcode below the minimum size is not recommended for dependable
printing and scanning.

## Custom dimensions and bar height

All dimensions are in millimetres:

\`\`\`bash
bookbarcode 9786253798338 \
  --width-mm 38 \
  --height-mm 20
\`\`\`

Set the data-bar height independently:

\`\`\`bash
bookbarcode 9786253798338 \
  --height-mm 20 \
  --bar-height-mm 12.5
\`\`\`

Guard bars are rendered \`5X\` longer than data bars. A layout is rejected when
bars would intrude into the human-readable digit area.

## Quiet zones

Set the same margin on both sides:

\`\`\`bash
bookbarcode 9786253798338 --side-margin-mm 3
\`\`\`

Or set each side separately:

\`\`\`bash
bookbarcode 9786253798338 \
  --left-margin-mm 3.5 \
  --right-margin-mm 2.5
\`\`\`

\`--left-margin-mm\` and \`--right-margin-mm\` override
\`--side-margin-mm\` for their respective sides. Without custom margins,
BookBarcode computes the EAN-13 defaults: \`11X\` left and \`7X\` right.

## Output format, path, and replacement

The default, \`--format both\`, writes SVG and PDF. To write only one format:

\`\`\`bash
bookbarcode 9786253798338 --format pdf
bookbarcode 9786253798338 --format svg
\`\`\`

Set an output base path with \`--output\` or \`-o\`:

\`\`\`bash
bookbarcode 9786253798338 \
  --output output/book-title/barcode
\`\`\`

The target directory must already exist. With \`--format both\`, this produces:

\`\`\`text
output/book-title/barcode.svg
output/book-title/barcode.pdf
\`\`\`

To replace verified existing files, opt in explicitly:

\`\`\`bash
bookbarcode 9786253798338 --output output/barcode --overwrite
\`\`\`

Each new artifact is written to a temporary sibling, verified, and then
atomically installed at the target.

## CLI reference

| Option | Description |
|---|---|
| \`isbn\` | ISBN-13 to encode |
| \`--display\` | Assigned ISBN heading to display |
| \`-o\`, \`--output\` | Output base path |
| \`--format\` | \`svg\`, \`pdf\`, or \`both\` |
| \`--preset\` | \`normal\` or \`minimum\` |
| \`--width-mm\` | Total width including margins |
| \`--height-mm\` | Total height |
| \`--bar-height-mm\` | Data-bar height |
| \`--side-margin-mm\` | Shared side margin |
| \`--left-margin-mm\` | Left margin |
| \`--right-margin-mm\` | Right margin |
| \`--overwrite\` | Allow verified replacement of existing outputs |
| \`-h\`, \`--help\` | Show help |

## Python API

Generate content without writing files:

\`\`\`python
from bookbarcode import Barcode

barcode = Barcode("9786253798338")
svg_text = barcode.to_svg()
pdf_bytes = barcode.to_pdf()
\`\`\`

Create a custom layout and write verified files:

\`\`\`python
from bookbarcode import Barcode, BarcodeLayout

layout = BarcodeLayout.from_preset(
    "normal",
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
\`\`\`

## Agent-tools JSON interface

From the repository root, generate SVG and PDF:

\`\`\`bash
printf '%s' '{
  "operation": "write_barcode",
  "params": {
    "isbn": "9786253798338",
    "output_base": "/tmp/book-barcode",
    "layout": {"preset": "normal"}
  }
}' | python3 isbn_barcode.py
\`\`\`

Supported operations:

- \`generate_svg\`
- \`write_svg\`
- \`write_pdf\`
- \`write_barcode\`
- \`verify_svg\`
- \`verify_pdf\`

The operation contract is defined in the top-level [SKILL.yaml](../SKILL.yaml).

## End-to-end examples

Print-ready normal-size PDF:

\`\`\`bash
bookbarcode 9786253798338 \
  --format pdf \
  --output output/normal-barcode
\`\`\`

Minimum-size SVG and PDF:

\`\`\`bash
bookbarcode 9786253798338 \
  --preset minimum \
  --format both \
  --output output/minimum-barcode
\`\`\`

Custom size, independent margins, and assigned hyphenation:

\`\`\`bash
bookbarcode 9786059681131 \
  --display "ISBN 978-605-9681-13-1" \
  --width-mm 39 \
  --height-mm 20 \
  --bar-height-mm 12 \
  --left-margin-mm 3.5 \
  --right-margin-mm 2.5 \
  --format pdf \
  --output output/custom-barcode
\`\`\`

## Printing and CMYK

- Send the PDF to the printer.
- Black elements use only \`K:100\` process black.
- Do not use \`C:100 M:100 Y:100 K:100\` rich black.
- Do not scale the barcode non-proportionally.
- Do not rasterize the vector PDF or substitute a screenshot.
- Keep the white quiet zones clear of other graphics.
- Before production, scan a printed sample and run the printer's preflight.

## Common errors

### Invalid check digit

The final ISBN digit is calculated from the first 12 digits. BookBarcode never
silently corrects an invalid ISBN; compare it with the publisher or ISBN record.

### Display heading does not match the ISBN

The digits in \`display_text\` must match the encoded ISBN.

### Margins consume the width

The sum of the left and right margins must be smaller than the total barcode
width.

### Bar height does not fit

Increase the total height or reduce the data-bar height.

### Output directory is missing

BookBarcode does not create target directories. Create the directory first, then
run the command again.

## Tests

From the BookBarcode repository root:

\`\`\`bash
python3 -m unittest discover -s tests -v
\`\`\`

The tests cover ISBN/EAN vectors, physical layouts, SVG/PDF rendering, CMYK
commands, tampered artifact detection, the CLI, and the agent JSON contract.
