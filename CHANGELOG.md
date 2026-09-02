# Changelog

All notable changes to BookBarcode are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added a project changelog reconstructed from declared package versions,
  release tags, and commit history.
- Added GitHub Actions CI across Python 3.9-3.13 on Linux, with a gated
  distribution build and metadata check.

## [0.4.0] - 2026-09-02

### Added

- Added the typed `LayoutSpec -> resolve_layout() -> ResolvedBarcodeLayout ->
  BarcodeGeometry` measurement pipeline.
- Added a canonical measurement dependency DAG documenting derivation and
  constraint relationships.
- Added public geometry and resolved-layout types for callers that need an
  explicit, fully resolved representation.
- Added stronger PDF artifact inspection for page dimensions, process-black
  commands, barcode modules, guard bars, human-readable digits, and physical
  geometry.
- Added negative tests for tampered SVG and PDF artifacts.
- Added end-to-end JSON adapter tests for generation, verification, path,
  overwrite, and invalid-input behavior.
- Added `USE_TOOL.md` as the agent operating procedure and expanded
  `SKILL.yaml` as the canonical machine-readable tool contract.
- Added English usage and KDY reference documentation alongside the Turkish
  guides.

### Changed

- Both SVG and PDF renderers now consume the same resolved barcode geometry.
- Layout resolution now rejects non-standard geometry that violates mandatory
  module, quiet-zone, guard-extension, or vertical-layout constraints.
- SVG and PDF verification calculations are more independent from renderer
  implementation helpers.
- README and user guides now explain output selection, custom layouts,
  overwrite policy, assigned ISBN hyphenation, and production preflight.
- Package metadata, licensing, source manifests, and development dependencies
  were prepared for public distribution.

### Safety

- Bundle writes now perform preflight checks before producing either output,
  reducing avoidable partial SVG/PDF bundles.
- Generated artifacts are verified before atomic replacement of their target
  files.

## [0.3.0] - 2026-08-31

### Added

- Introduced the reusable typed `bookbarcode` Python package.
- Added immutable `Barcode` and `BarcodeLayout` public APIs.
- Added ISBN-13 normalization and checksum validation for `978` and `979`
  prefixes.
- Added deterministic 95-module EAN-13 encoding and shared millimetre-based
  geometry.
- Added editable SVG and process-black CMYK PDF renderers.
- Added serialized artifact verification for SVG and PDF outputs.
- Added the `bookbarcode` human CLI and JSON agent-tool entrypoint.
- Added normal 35 x 19 mm and minimum 26 x 14 mm KDY presets.
- Added validated atomic file writes with explicit overwrite protection.
- Added package, CLI, and adapter test suites, type information, examples,
  Turkish documentation, and agent maintenance guidance.

### Changed

- Replaced the original single-file prototype with separated ISBN, EAN,
  layout, geometry, rendering, verification, I/O, CLI, and adapter modules.

## [0.1.0] - 2026-08-25

### Added

- Added the initial standalone ISBN-13/EAN-13 SVG generator prototype.
- Added basic physical barcode sizing, guard bars, quiet zones, visible ISBN
  text, and CMYK intent metadata.

[Unreleased]: https://github.com/Aues12/BookBarcode/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Aues12/BookBarcode/releases/tag/v0.4.0
[0.3.0]: https://github.com/Aues12/BookBarcode/commit/4c047fd04b94878b9d242302b8d7676389ccc0a5
[0.1.0]: https://github.com/Aues12/BookBarcode/commit/2e80d18b6c895f2cc99d724e0a4d97e256daccfc
