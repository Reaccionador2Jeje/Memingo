import re


def _location(error):
    line = getattr(error, "line", None)
    column = getattr(error, "column", None)

    if line is not None and column is not None:
        return line, column

    match = re.search(r"line (\d+), column (\d+)", str(error))
    if match:
        return int(match.group(1)), int(match.group(2))

    return None, None


def _help_for(message):
    lowered = message.lower()

    if "undefined variable" in lowered:
        return "Check the variable name or declare it first with 'vibe'."
    if "division by zero" in lowered:
        return "Make sure the divisor is not zero."
    if "unexpected character" in lowered or "unknown escape" in lowered:
        return "Check the character or escape sequence at this position."
    if "expected " in lowered or "unexpected token" in lowered:
        return "Check the syntax around this position."
    return "Review this statement and the values it uses."


def render_diagnostic(error, source, filename="<source>"):
    """Render a source-aware diagnostic for lexer, parser and runtime errors."""
    message = re.sub(
        r"\s+at line \d+, column \d+$",
        "",
        str(error),
    )
    line, column = _location(error)

    if line is None or column is None:
        return f"Memingo error: {message}"

    lines = source.splitlines()
    if source.endswith("\n"):
        lines.append("")

    if not 1 <= line <= len(lines):
        return f"Memingo error: {message}"

    first = max(1, line - 1)
    last = min(len(lines), line + 1)
    width = len(str(last))
    output = [
        "",
        "MEMINGO ERROR",
        "",
        f"--> {filename}:{line}:{column}",
        "",
    ]

    for number in range(first, last + 1):
        text = lines[number - 1].expandtabs(4)
        output.append(f" {number:>{width}} | {text}")

        if number == line:
            prefix = lines[number - 1][:max(0, column - 1)].expandtabs(4)
            output.append(f" {' ' * width} | {' ' * len(prefix)}^")

    output.extend(["", message, "", f"Help: {_help_for(message)}", ""])
    return "\n".join(output)
