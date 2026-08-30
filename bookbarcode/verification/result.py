"""Shared immutable result type for artifact verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    """Collect deterministic validation errors for one artifact."""

    errors: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """Return ``True`` only when no validation error was recorded."""
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a JSON-serializable mapping."""
        return {"valid": self.valid, "errors": list(self.errors)}
