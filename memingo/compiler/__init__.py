"""Foundational building blocks for the next-generation Memingo compiler."""

from .checker import TypeCheckResult, TypeChecker, check
from .hir import HIRNode, HIRProgram, lower
from .pipeline import CompilationResult, compile_source
from .ownership import OwnershipChecker, OwnershipResult, check_ownership
from .borrow import BorrowChecker, BorrowResult, check_borrows
from .diagnostics import Diagnostic, DiagnosticBag, Label, Severity
from .source import SourceFile, SourceLocation, SourceMap, Span
from .types import (
    ANY, BASED, CAPTION, DECIMAL, GHOST, WHOLE, Type, TypeKind,
    common_type, function_of, is_assignable, list_of, map_of,
)

__all__ = [
    "ANY", "BASED", "CAPTION", "DECIMAL", "GHOST", "WHOLE",
    "CompilationResult", "OwnershipChecker", "OwnershipResult", "check_ownership", "BorrowChecker", "BorrowResult", "check_borrows", "HIRNode", "HIRProgram", "Diagnostic", "DiagnosticBag", "Label", "Severity",
    "SourceFile", "SourceLocation", "SourceMap", "Span",
    "Type", "TypeKind", "TypeCheckResult", "TypeChecker",
    "check", "compile_source", "lower", "common_type", "function_of", "is_assignable",
    "list_of", "map_of",
]
