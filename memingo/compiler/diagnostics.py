"""Structured compiler diagnostics with source-aware text rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .source import SourceMap, Span


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"
    HELP = "help"


@dataclass(frozen=True, slots=True)
class Label:
    span: Span
    message: str = ""
    primary: bool = False


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    labels: tuple[Label, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("diagnostic code cannot be empty")
        if not self.message.strip():
            raise ValueError("diagnostic message cannot be empty")

    def render(self, sources: SourceMap) -> str:
        """Render a compact, dependency-free diagnostic for terminals."""
        lines = [f"{self.severity.value}[{self.code}]: {self.message}"]
        for label in self.labels:
            source = sources.get(label.span.source_id)
            location = source.location_at(label.span.start)
            lines.append(f" --> {source.source_id}:{location.line}:{location.column}")
            excerpt = source.line_text(location.line)
            lines.append(f"{location.line:>4} | {excerpt}")
            width = max(1, label.span.length)
            width = min(width, max(1, len(excerpt) - location.column + 1))
            marker = " " * (location.column - 1) + "^" * width
            if label.message:
                marker += f" {label.message}"
            lines.append(f"     | {marker}")
        lines.extend(f" note: {note}" for note in self.notes)
        return "\n".join(lines)


@dataclass
class DiagnosticBag:
    """Collect diagnostics while allowing compilation to continue."""

    _items: list[Diagnostic] = field(default_factory=list)

    def emit(self, diagnostic: Diagnostic) -> Diagnostic:
        self._items.append(diagnostic)
        return diagnostic

    def error(self, code: str, message: str, *labels: Label) -> Diagnostic:
        return self.emit(Diagnostic(code, message, Severity.ERROR, tuple(labels)))

    def warning(self, code: str, message: str, *labels: Label) -> Diagnostic:
        return self.emit(Diagnostic(code, message, Severity.WARNING, tuple(labels)))

    @property
    def items(self) -> tuple[Diagnostic, ...]:
        return tuple(self._items)

    @property
    def has_errors(self) -> bool:
        return any(item.severity is Severity.ERROR for item in self._items)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)
