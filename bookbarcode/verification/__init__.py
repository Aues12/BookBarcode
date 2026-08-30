"""Public artifact verification functions and result type."""

from .pdf import verify_pdf
from .result import VerificationResult
from .svg import verify_svg

__all__ = ["VerificationResult", "verify_pdf", "verify_svg"]
