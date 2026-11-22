"""Foundational building blocks for the next-generation Memingo compiler.

The existing interpreter remains the default execution engine. This package
introduces source tracking and diagnostics without changing language behavior.
"""

from .diagnostics import Diagnostic, DiagnosticBag, Label, Severity
from .source import SourceFile, SourceLocation, SourceMap, Span

__all__ = [
    "Diagnostic", "DiagnosticBag", "Label", "Severity",
    "SourceFile", "SourceLocation", "SourceMap", "Span",
]
