"""Public compilation pipeline for Memingo source files."""

from __future__ import annotations

from dataclasses import dataclass

from .checker import TypeCheckResult, check
from .diagnostics import Diagnostic, DiagnosticBag, Severity
from .hir import HIRProgram, lower
from .source import SourceFile, SourceMap


@dataclass(frozen=True, slots=True)
class CompilationResult:
    source: SourceFile
    sources: SourceMap
    hir: HIRProgram | None
    diagnostics: tuple[Diagnostic, ...]
    type_check: TypeCheckResult | None

    @property
    def succeeded(self) -> bool:
        return self.hir is not None and not any(
            item.severity is Severity.ERROR for item in self.diagnostics
        )


def compile_source(text: str, source_id: str = "<memory>") -> CompilationResult:
    """Parse, type-check, and lower source without executing it."""
    from ..lexer import LexerError
    from ..parser import ParseError, parse

    source = SourceFile(source_id, text)
    sources = SourceMap((source,))
    diagnostics = DiagnosticBag()

    try:
        program = parse(text, source_id=source_id)
    except (LexerError, ParseError) as exc:
        diagnostics.error("M0001", str(exc))
        return CompilationResult(source, sources, None, diagnostics.items, None)

    checked = check(program, diagnostics)
    hir = lower(program, checked.expression_types)
    return CompilationResult(source, sources, hir, diagnostics.items, checked)
