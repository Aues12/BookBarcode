# BookBarcode Project Management Guide

## Mission

BookBarcode is both a reusable Python package and an agent-tools capability.
It generates deterministic ISBN-13/EAN-13 barcodes as editable SVG and
print-ready process-black CMYK PDF artifacts.

The project should remain:

* standards-conscious and deterministic;
* small enough to audit without specialized infrastructure;
* safe for automated file generation;
* usable as a normal Python package, a human CLI, and a JSON agent tool;
* readable by maintainers who did not write the original barcode engine.

## Product Surfaces

Maintain one implementation with three access surfaces:

```text
bookbarcode package
├── Python API       import bookbarcode
├── Human CLI        bookbarcode ...
└── Agent adapter    isbn_barcode.py < request.json
```

The package is the single source of truth. The agent adapter may translate
parameters and responses, but it must not reimplement ISBN, EAN, geometry,
rendering, verification, or file-writing algorithms.

## Documentation Set

Maintain the documentation as distinct, linked surfaces:

* `README.md` — concise package overview and primary entrypoints;
* `docs/KULLANIM.md` — complete Turkish user guide for package, CLI, and tool;
* `docs/KDY-REFERANS-NOTLARI.md` — auditable interpretation of KDY dimensions
  and process-black guidance;
* `SKILL.yaml` — machine-readable operation contract;
* `AGENTS.md` — architecture, maintenance, quality, and release policy.

When CLI syntax, public API, layout behavior, or output policy changes, update
every affected document in the same change. Examples must be executable against
the current implementation; do not preserve obsolete `main.py` commands.

Third-party reference binaries require confirmed redistribution rights before
entering the repository or package archives. Until the KDY source PDF's rights
are confirmed, maintain its relevant technical content as attributed Markdown
notes and treat the original document as the authoritative external reference.

## Architecture and Ownership

```text
bookbarcode/
├── isbn.py              ISBN normalization, checksum, and display labels
├── ean13.py             parity tables and the 95-module symbol
├── layout.py            physical measurements and KDY presets
├── geometry.py          format-independent bars and text positions
├── renderers/           SVG and PDF serialization only
├── verification/        independent artifact inspection
├── io.py                validated atomic file writes
├── barcode.py           high-level immutable facade
└── cli.py               human-oriented command line

tool.py                  agent-tools parameter/response adapter
isbn_barcode.py          JSON stdin/stdout entrypoint
SKILL.yaml               machine-readable tool contract
pyproject.toml           package and console-script metadata
```

Module boundaries are intentional:

* ISBN code must not import renderer or filesystem modules.
* Geometry must be format-independent and measured in millimetres.
* Renderers consume shared geometry; they do not recalculate EAN semantics.
* Verification must inspect serialized artifacts rather than trusting renderers.
* File mutation belongs in `io.py` or explicit `write_*` methods.
* `tool.py` returns JSON-friendly values and the standard repository envelope.

## Public API Contract

The preferred library entrypoint is:

```python
from bookbarcode import Barcode, BarcodeLayout
```

Keep the public API intentionally small. Add a symbol to `bookbarcode.__all__`
only when it is documented, typed, tested, and intended for compatibility
across releases. Internal helpers may change without compatibility promises.

`Barcode` must remain immutable. Rendering methods return values without side
effects; file-writing methods make mutation visible in their names.

## Domain Invariants

Every change must preserve these rules:

* ISBN input is normalized but never silently corrected.
* Only checksum-valid ISBN-13 values with `978` or `979` prefixes are accepted.
* The EAN-13 symbol contains exactly 95 modules.
* Default quiet zones are 11X left and 7X right.
* Guard bars extend by 5X.
* KDY presets remain 35 x 19 mm (`normal`) and 26 x 14 mm (`minimum`).
* PDF ink uses `0 0 0 1 k`, equivalent to C:0 M:0 Y:0 K:100.
* SVG retains a black fallback plus explicit CMYK intent metadata.
* Existing files are never replaced without explicit `overwrite=True`.
* New artifacts are verified before atomic replacement of their target.

Automatic 3-3-3-3-1 hyphenation is a display fallback, not an assertion about
official ISBN registrant ranges. Documentation must tell callers to supply
assigned hyphenation when that distinction matters.

## Code and Docstring Standard

Optimize for human comprehension before cleverness.

* Give modules a one-sentence responsibility docstring.
* Give every public class, function, method, and property a useful docstring.
* Document units explicitly (`mm`, points, module counts, or bytes).
* Document side effects, overwrite behavior, and important exceptions.
* Explain why a non-obvious formula or PDF command exists.
* Prefer named dataclasses over positional tuples at subsystem boundaries.
* Prefer descriptive intermediate variables over compressed expressions.
* Keep functions narrow; extract serialization and validation phases clearly.
* Use comments for design rationale, not narration of obvious syntax.
* Keep error messages actionable and stable enough for tests to identify intent.

Docstrings should describe contracts rather than repeat function names. Private
helpers need docstrings when their algorithm, unit convention, or side effect is
not immediately obvious.

## Development Workflow

For each change:

1. Identify the owning module and avoid crossing established boundaries.
2. Add or update a focused test that expresses the intended behavior.
3. Implement the smallest coherent change.
4. Run the package and adapter test suite.
5. Run the repository aggregate tests and metadata checks.
6. Update `README.md`, `SKILL.yaml`, registry metadata, and examples when a
   public operation or parameter changes.
   Update `docs/KULLANIM.md` whenever user-facing package or CLI behavior changes.
7. Build a wheel and source distribution for packaging-related changes.
8. Inspect generated SVG/PDF output when geometry or rendering changes.

Do not copy fixes between the package and adapter. If a change affects barcode
behavior, fix the package and let every surface consume it.

## Testing and Quality Gates

Required local checks:

```bash
python3 -m unittest discover -s tests -v
python3 test_all.py
python3 -m py_compile bookbarcode/*.py
git diff --check
```

Tests should cover:

* known ISBN checksum and 95-module EAN vectors;
* invalid inputs and physical layout boundaries;
* normal, minimum, and custom layouts;
* shared SVG/PDF geometry;
* CMYK PDF commands and page dimensions;
* tampered artifact detection;
* atomic writes and overwrite refusal;
* package facade, human CLI, and agent JSON envelope;
* bundle preflight preventing avoidable partial output.

A renderer change is incomplete until both positive output tests and tampering
or invalid-output tests remain meaningful.

## Dependency Policy

Runtime dependencies require a concrete benefit and an explicit design review.
Consider package size, cold-start time, reproducibility, license compatibility,
and offline agent-tools execution. Development-only tools belong in the `dev`
optional dependency group.

If a barcode library is introduced later, retain independent verification and
known-vector tests; a dependency does not replace validation.

## Version and Release Management

The package version lives in `bookbarcode.__version__`; `pyproject.toml` reads
it dynamically. Follow semantic versioning:

* patch: compatible fixes and documentation;
* minor: backward-compatible operations or layout options;
* major: public Python API, CLI, output, or behavior incompatibilities.

Before publishing:

1. Confirm the distribution name is available on the target package index.
2. Select and add an explicit license; public release is blocked until then.
3. Run the complete quality gates.
4. Build wheel and source distribution from this directory.
5. Inspect archive contents and ensure `py.typed` is included.
6. Run `twine check` on all distributions.
7. Publish to TestPyPI and test installation in a clean environment.
8. Publish the exact tested artifacts to PyPI.
9. Tag the matching commit and record release notes.

Never place credentials or repository-specific absolute paths in package files.

## Planning and Change Control

Classify proposed work before implementation:

* **domain change** — ISBN/EAN rules; requires vectors and standards review;
* **geometry change** — physical output; requires both renderer tests;
* **renderer change** — serialized format; requires verification updates;
* **public API change** — requires docs, examples, compatibility assessment;
* **adapter change** — requires `SKILL.yaml`, registry, and JSON contract review;
* **release change** — requires package build and archive inspection.

Record consequential decisions in commit or pull-request context, including the
problem, chosen approach, rejected alternatives, compatibility impact, and
validation evidence.

## Definition of Done

A change is complete only when:

* ownership and module boundaries remain clear;
* public behavior is typed, documented, and tested;
* files are validated before mutation;
* package and agent surfaces use the same implementation;
* affected tests and repository checks pass;
* metadata and examples match actual behavior;
* release-impacting changes produce valid distributions;
* remaining risks or external validation needs are stated explicitly.
