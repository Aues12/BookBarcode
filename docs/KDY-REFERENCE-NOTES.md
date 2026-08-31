# KDY Barcode Size and Colour Reference Notes

This text-based working note is derived from the one-page visual content of
\`KDY Barkod Klavuzu.PDF\` in the BookBarcode source workspace. The PDF is an A4
document created with Adobe InDesign on 1 December 2020.

This note does not replace the official KDY document. Confirm current publisher
requirements and printer requirements before production.

## Minimum size

Minimum barcode size:

\`\`\`text
26 x 14 mm
\`\`\`

| Use | Barcode | Outer box |
|---|---:|---:|
| Light background, no border | 26 x 14 mm | None |
| Light background, bordered | 26 x 14 mm | 30 x 18 mm |
| Background design, in a white box | 26 x 14 mm | 30 x 18 mm |

For a background design, place the barcode in a white box with 2 mm clearance
on every side.

## Normal size

Normal barcode size:

\`\`\`text
35 x 19 mm
\`\`\`

| Use | Barcode | Outer box |
|---|---:|---:|
| Light background, no border | 35 x 19 mm | None |
| Light background, bordered | 35 x 19 mm | 39 x 23 mm |
| Background design, in a white box | 35 x 19 mm | 39 x 23 mm |

The outer-box size preserves a 2 mm protection area on every side of the
barcode.

## Colour

The guide accepts this black:

\`\`\`text
C:0 M:0 Y:0 K:100
\`\`\`

An unacceptable rich-black example:

\`\`\`text
C:100 M:100 Y:100 K:100
\`\`\`

The BookBarcode PDF renderer uses the direct \`0 0 0 1 k\` process-black command
for barcode bars and text.

## Packaging and redistribution decision

The source PDF does not state redistribution terms, so the binary file is not
copied into the Python package or agent-tools repository. This Markdown note
records the size and colour decisions used by the implementation in an
auditable form. If the PDF owner or publisher confirms redistribution
permission, the original document may be added separately under
\`docs/references/\`; whether it should be included in the package manifest
requires a separate review.
