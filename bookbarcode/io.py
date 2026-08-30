"""Validated, atomic file writing shared by the public library facade."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Callable

from .verification import VerificationResult


Verifier = Callable[[Path], VerificationResult]


def validate_output_path(
    value: str | Path,
    suffix: str,
    overwrite: bool,
) -> Path:
    """Validate an output target without changing the filesystem."""
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    path = Path(value)
    if path.suffix.lower() != suffix:
        raise ValueError(f"output path must end with {suffix}")
    if not path.parent.exists() or not path.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {path.parent}")
    if path.exists() and not overwrite:
        raise FileExistsError(f"output file already exists: {path}")
    return path


def write_verified_atomically(
    path: str | Path,
    content: bytes,
    *,
    suffix: str,
    verifier: Verifier,
    overwrite: bool = False,
) -> Path:
    """Verify a temporary sibling and atomically move it into place.

    No target file is modified unless the generated temporary artifact passes
    verification. Existing targets require explicit ``overwrite=True``.
    """
    target = validate_output_path(path, suffix, overwrite)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=target.suffix,
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        verification = verifier(temporary_path)
        if not verification.valid:
            details = "; ".join(verification.errors)
            raise RuntimeError(f"generated artifact failed verification: {details}")
        os.replace(temporary_path, target)
        temporary_path = None
        return target
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
