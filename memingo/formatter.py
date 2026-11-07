from pathlib import Path


OPENING = "([{"
CLOSING = ")]}"


def _delimiter_delta(line):
    depth = 0
    in_string = False
    escaped = False
    for char in line:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == "#":
            break
        if char == '"':
            in_string = True
        elif char in OPENING:
            depth += 1
        elif char in CLOSING:
            depth -= 1
    return depth


def _leading_closers(line):
    count = 0
    for char in line.strip():
        if char.isspace():
            continue
        if char in CLOSING:
            count += 1
        else:
            break
    return count


def format_source(source: str) -> str:
    lines = source.expandtabs(4).splitlines()
    depth = 0
    formatted = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            formatted.append("")
            continue
        indent_depth = max(0, depth - _leading_closers(line))
        formatted.append("    " * indent_depth + line)
        depth = max(0, depth + _delimiter_delta(line))
    return "\n".join(formatted).rstrip() + "\n"


def format_file(path: str, write=False) -> str:
    source_path = Path(path)
    formatted = format_source(source_path.read_text(encoding="utf-8"))
    if write:
        source_path.write_text(formatted, encoding="utf-8")
    return formatted
