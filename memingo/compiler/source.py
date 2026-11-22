"""Source text, offsets, locations, and spans for compiler tooling.

Offsets are Python string offsets (Unicode code points), not UTF-8 byte offsets.
Line and column numbers are one-based so diagnostics match editor conventions.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True, slots=True)
class Span:
    """A half-open range [start, end) in a source file."""

    source_id: str
    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("span start cannot be negative")
        if self.end < self.start:
            raise ValueError("span end cannot be before span start")

    @property
    def length(self) -> int:
        return self.end - self.start

    @property
    def is_empty(self) -> bool:
        return self.start == self.end


@dataclass(frozen=True, slots=True)
class SourceLocation:
    source_id: str
    line: int
    column: int
    offset: int


@dataclass(frozen=True, slots=True)
class SourceFile:
    """An immutable source document with fast offset-to-location lookup."""

    source_id: str
    text: str
    _line_starts: tuple[int, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id cannot be empty")
        starts = [0]
        starts.extend(index + 1 for index, char in enumerate(self.text) if char == "\n")
        object.__setattr__(self, "_line_starts", tuple(starts))

    @property
    def line_count(self) -> int:
        return len(self._line_starts)

    def location_at(self, offset: int) -> SourceLocation:
        """Convert a zero-based character offset to a one-based location."""
        if offset < 0 or offset > len(self.text):
            raise ValueError(f"offset {offset} is outside source {self.source_id!r}")
        line_index = bisect_right(self._line_starts, offset) - 1
        line_start = self._line_starts[line_index]
        return SourceLocation(self.source_id, line_index + 1, offset - line_start + 1, offset)

    def line_text(self, line: int) -> str:
        """Return a line without its trailing newline; lines are one-based."""
        if line < 1 or line > self.line_count:
            raise ValueError(f"line {line} is outside source {self.source_id!r}")
        start = self._line_starts[line - 1]
        end = self._line_starts[line] if line < self.line_count else len(self.text)
        return self.text[start:end].removesuffix("\n").removesuffix("\r")

    def slice(self, span: Span) -> str:
        if span.source_id != self.source_id:
            raise ValueError("span belongs to a different source file")
        if span.end > len(self.text):
            raise ValueError("span extends beyond source text")
        return self.text[span.start:span.end]

    def span(self, start: int, end: int) -> Span:
        if end > len(self.text):
            raise ValueError("span extends beyond source text")
        return Span(self.source_id, start, end)


class SourceMap:
    """Registry of source files referenced by compiler spans."""

    def __init__(self, sources: Iterable[SourceFile] = ()) -> None:
        self._sources: dict[str, SourceFile] = {}
        for source in sources:
            self.add(source)

    def add(self, source: SourceFile) -> SourceFile:
        if source.source_id in self._sources:
            raise ValueError(f"source {source.source_id!r} is already registered")
        self._sources[source.source_id] = source
        return source

    def replace(self, source: SourceFile) -> SourceFile:
        self._sources[source.source_id] = source
        return source

    def get(self, source_id: str) -> SourceFile:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise KeyError(f"unknown source file {source_id!r}") from exc

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._sources

    def __len__(self) -> int:
        return len(self._sources)
