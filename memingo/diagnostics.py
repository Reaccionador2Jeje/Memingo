"""Source-aware diagnostics shared by the Memingo CLI."""

from __future__ import annotations

import re
from pathlib import Path


_LOCATION = re.compile(r"(?:at )?line (\d+), column (\d+)", re.IGNORECASE)


def format_diagnostic(error: Exception, source: str, filename: str | Path | None = None) -> str:
    """Render an exception with a source location and a small code excerpt.

    Lexer and parser errors already carry token coordinates. Runtime errors are
    annotated by Interpreter.execute_block, so all three phases share one view.
    """
    message = str(error)
    match = _LOCATION.search(message)
    if not match:
        label = f" in {filename}" if filename else ""
        return f"error{label}: {message}"

    line_number, column = (int(value) for value in match.groups())
    clean_message = _LOCATION.sub("", message).strip()
    lines = source.splitlines()
    if not lines:
        lines = [""]
    line_number = max(1, min(line_number, len(lines)))
    start = max(1, line_number - 1)
    end = min(len(lines), line_number + 1)
    gutter = len(str(end))
    location = str(filename) if filename else "<source>"
    output = [f"error: {clean_message}", f" --> {location}:{line_number}:{column}", "  |"]
    for number in range(start, end + 1):
        text = lines[number - 1]
        output.append(f"{number:>{gutter}} | {text}")
        if number == line_number:
            output.append(f"{'':>{gutter}} | {' ' * max(0, column - 1)}^")
    return "\n".join(output)
