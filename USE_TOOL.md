# Using BookBarcode as an Agent Tool

This document is the procedural contract for agents and runtimes that invoke
BookBarcode through its JSON adapter. The canonical machine-readable manifest is
[`SKILL.yaml`](SKILL.yaml); this guide explains how to select operations, invoke
the adapter, interpret results, and handle file side effects safely.

## Contract files

The agent layer has three distinct sources of guidance:

- `SKILL.yaml` is the canonical local manifest for interfaces, operations,
  parameters, side effects, and validation commands.
- `USE_TOOL.md` is the operational procedure for callers.
- `AGENTS.md` defines maintenance, architecture, testing, and change policy.

When these files disagree, treat the implementation and tests as evidence of
current behavior, then correct all affected contract documents together. Do not
silently invent parameters or response fields.

## Availability and execution context

The JSON adapter consists of `isbn_barcode.py` and `tool.py`. Run it from a
BookBarcode source checkout, normally from the repository root:

```bash
printf '%s' '{
  "operation": "generate_svg",
  "params": {"isbn": "9786253798338"}
}' | python3 isbn_barcode.py
```

The source distribution contains the adapter files. The wheel installs the
`bookbarcode` Python package and human CLI, but it does not install
`isbn_barcode.py`, `tool.py`, or `SKILL.yaml` as importable top-level modules.
An agent using only the wheel should use the documented Python package API
instead of assuming the JSON entrypoint is installed.

Relative input and output paths are resolved against the invoking process's
current working directory. Use explicit paths when the runtime's working
directory is uncertain.

## Choosing an interface

| Caller | Preferred interface | Entry point |
|---|---|---|
| Agent or language-neutral runtime | JSON on stdin/stdout | `python3 isbn_barcode.py` |
| Python agent integration | Adapter callables or `run()` | `tool.py` |
| Python application | Immutable package facade | `from bookbarcode import Barcode, BarcodeLayout` |
| Human shell user | Human-oriented CLI | `bookbarcode ...` |

The JSON adapter and human CLI are separate interfaces. Do not send JSON to the
`bookbarcode` command, and do not pass CLI flags to `isbn_barcode.py`.

## Request contract

The adapter reads one UTF-8 JSON object from stdin:

```json
{
  "operation": "write_barcode",
  "params": {
    "isbn": "9786253798338",
    "output_base": "/tmp/book-barcode",
    "formats": ["svg", "pdf"]
  }
}
```

- `operation` must name one supported operation.
- `params` must be an object containing only parameters accepted by that
  operation.
- Missing required parameters and unexpected operation parameters are errors.
- A top-level `meta` object may be supplied by a runtime, but the current
  adapter does not preserve or echo caller metadata. Do not rely on metadata
  round-tripping.
- Do not rely on unrecognized top-level fields being accepted; they are not part
  of the stable contract.

## Response contract

The adapter writes exactly one JSON response to stdout.

Successful execution:

```json
{
  "success": true,
  "message": "Wrote and verified 2 barcode artifact(s)",
  "result": {},
  "meta": {"operation": "write_barcode"}
}
```

Failed execution:

```json
{
  "success": false,
  "message": "output file already exists: /tmp/book-barcode.svg",
  "error": {
    "type": "FileExistsError",
    "message": "output file already exists: /tmp/book-barcode.svg"
  }
}
```

`success` reports whether the requested operation executed normally. For
verification operations it does **not** report whether the inspected artifact
is valid. A completed verification of an invalid artifact has this shape:

```json
{
  "success": true,
  "message": "Barcode verification found errors",
  "result": {
    "valid": false,
    "errors": ["bar modules do not encode the expected ISBN"]
  },
  "meta": {"operation": "verify_svg"}
}
```

Agents must check both levels:

1. Check top-level `success` to determine whether the operation ran.
2. For `verify_svg` and `verify_pdf`, also require `result.valid` to be `true`
   before treating the artifact as verified.

## Process exit codes

The executable adapter currently uses:

| Code | Meaning |
|---:|---|
| `0` | The operation executed and a success envelope was returned. |
| `1` | JSON was parsed, but request validation or operation execution failed. |
| `2` | Stdin was empty or did not contain valid JSON. |

Exit code `0` for a verification operation still requires inspecting
`result.valid`. Direct Python calls to `run()` return an envelope and do not exit
the process.

## Choosing an operation

| Goal | Operation | Reads files | Writes files |
|---|---|---:|---:|
| Produce SVG text in the response | `generate_svg` | No | No |
| Create one verified SVG file | `write_svg` | No caller file | One SVG |
| Create one verified PDF file | `write_pdf` | No caller file | One PDF |
| Create a verified SVG/PDF selection | `write_barcode` | No caller file | One or two artifacts |
| Inspect an existing SVG against an ISBN and layout | `verify_svg` | One SVG | No |
| Inspect PDF framing, page size, and process-black command | `verify_pdf` | One PDF | No |

Prefer `generate_svg` when the caller only needs content and has not authorized
filesystem changes. Prefer a `write_*` operation only when file creation is part
of the task. Use verification operations for caller-selected existing files;
they do not repair or replace those files.

## Shared parameters

### ISBN and display text

- `isbn` must normalize to a checksum-valid ISBN-13 beginning with `978` or
  `979`. Invalid values are rejected and never silently corrected.
- `display_text` is optional. Its digits must exactly match the encoded ISBN;
  only punctuation and hyphen placement may differ.
- If `display_text` is omitted, BookBarcode uses a readable `3-3-3-3-1`
  fallback. This fallback does not infer official ISBN registrant ranges.

### Layout object

All dimensions are millimetres. `layout` may contain only these fields:

| Field | Type | Meaning |
|---|---|---|
| `preset` | string | `normal` (default) or `minimum` |
| `width_mm` | finite number or null | Total artifact width |
| `height_mm` | finite number or null | Total artifact height |
| `bar_height_mm` | finite number or null | Data-bar height |
| `side_margin_mm` | finite number or null | Shared left/right margin |
| `left_margin_mm` | finite number or null | Independent left margin |
| `right_margin_mm` | finite number or null | Independent right margin |

`normal` starts from 35 x 19 mm and `minimum` from 26 x 14 mm. Explicit width,
height, bar-height, and margin fields override their preset values. An explicit
left or right margin overrides `side_margin_mm` for that side. Boolean and
non-finite numeric values are rejected.

Example:

```json
{
  "preset": "normal",
  "width_mm": 38,
  "height_mm": 20,
  "bar_height_mm": 12.5,
  "left_margin_mm": 3.5,
  "right_margin_mm": 2.5
}
```

### Format selection

`write_barcode.formats` defaults to `["svg", "pdf"]`. When supplied, it must
be a non-empty array containing only the unique strings `svg` and/or `pdf`.
Order is preserved in the returned `outputs` array.

### Paths and overwrite behavior

- `write_svg.output_path` must end in `.svg`.
- `write_pdf.output_path` must end in `.pdf`.
- `verify_svg.path` must name an existing `.svg` file.
- `verify_pdf.path` must name an existing `.pdf` file.
- `write_barcode.output_base` is converted to selected `.svg`/`.pdf` targets;
  any existing suffix on the base is replaced.
- Output parent directories must already exist.
- Existing targets are rejected unless `overwrite` is explicitly `true`.
- Agents should not set `overwrite: true` unless replacement is part of the
  user's requested task.

## Result objects

Generated and written results use these common records.

Resolved layout metadata:

```json
{
  "width_mm": 35.0,
  "height_mm": 19.0,
  "left_margin_mm": 3.407079646017699,
  "right_margin_mm": 2.168141592920354,
  "module_width_mm": 0.30973451327433627,
  "bar_height_mm": 11.78
}
```

Colour metadata:

```json
{"space": "CMYK", "c": 0, "m": 0, "y": 0, "k": 100}
```

Verification record:

```json
{"valid": true, "errors": []}
```

Operation-specific result fields:

- `generate_svg`: `isbn`, `display_text`, `svg`, `layout`, `color`.
- `write_svg` and `write_pdf`: `path`, `format`, `isbn`, `display_text`,
  `layout`, `color`, `verification`.
- `write_barcode`: `isbn` and an `outputs` array of written artifact records.
- `verify_svg`: `path`, `isbn`, `valid`, `errors`, `layout`.
- `verify_pdf`: `path`, `valid`, `errors`, `layout`.

`verify_pdf` does not accept an expected ISBN and does not independently decode
the PDF's bars or human-readable digits. Its scope is PDF framing, requested page
size, and the presence of the process-black command. `verify_svg` performs the
ISBN/module, guard-bar, text, dimensions, geometry, and CMYK-intent checks.

## File safety and atomicity

### One output file

Each `write_svg` or `write_pdf` call protects its target as follows:

1. Validate the requested target and overwrite policy without changing it.
2. Write new content to a temporary sibling in the target directory.
3. Verify that temporary artifact.
4. Replace the target with one filesystem operation only after verification.
5. Remove the temporary file if generation or verification fails.

This is an atomic write at the individual-file boundary: callers should observe
either the previous complete target or the new complete target, not a partially
written target. An error before replacement leaves an existing target intact.

### SVG/PDF bundle

`write_barcode` preflights every selected target before writing the first one.
This prevents predictable partial output, such as discovering only after the SVG
write that the PDF target already exists.

The bundle is **not** a multi-file transaction. Selected artifacts are installed
one at a time and there is no rollback of an artifact already installed. If an
unexpected failure occurs after the first artifact is installed, that artifact
may remain even though the later artifact was not written. Agents must inspect
the success envelope and, after a failure, check the requested output paths
instead of assuming an all-or-nothing two-file commit.

## Common failures and recovery

| Error | Agent response |
|---|---|
| Invalid ISBN/check digit | Ask for or obtain the correct assigned ISBN; do not correct it silently. |
| Display digits do not match | Correct only the display label supplied by the caller. |
| Unknown or unexpected parameter | Rebuild the request from `SKILL.yaml`; do not retry unchanged. |
| Missing output directory | Create it only if directory creation is authorized, otherwise ask for a valid target. |
| Existing output | Keep `overwrite` false unless replacement is explicitly intended. |
| Invalid layout | Correct units or dimensions; do not reduce below documented production requirements casually. |
| Verification `valid: false` | Treat the artifact as unverified and report `result.errors`. |
| Runtime/write failure | Check which requested output paths exist before deciding whether a bundle retry is safe. |

## Examples

Write the default SVG/PDF pair:

```bash
printf '%s' '{
  "operation": "write_barcode",
  "params": {
    "isbn": "9786253798338",
    "output_base": "/tmp/book-barcode"
  }
}' | python3 isbn_barcode.py
```

Write one minimum-size PDF:

```bash
printf '%s' '{
  "operation": "write_pdf",
  "params": {
    "isbn": "9786253798338",
    "output_path": "/tmp/book-barcode.pdf",
    "layout": {"preset": "minimum"}
  }
}' | python3 isbn_barcode.py
```

Verify an existing SVG:

```bash
printf '%s' '{
  "operation": "verify_svg",
  "params": {
    "path": "/tmp/book-barcode.svg",
    "isbn": "9786253798338",
    "layout": {"preset": "normal"}
  }
}' | python3 isbn_barcode.py
```

## Validation

From the BookBarcode repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m build
```

Operation, parameter, response, path, or side-effect changes require coordinated
updates to `SKILL.yaml`, this guide, affected human documentation, examples, and
tests. When BookBarcode is also integrated into an external agent-tools registry,
that external registry entry must be reviewed separately; it is not the
canonical local manifest for this repository.
