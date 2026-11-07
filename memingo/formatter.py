from pathlib import Path


def format_source(source: str) -> str:
    lines = source.expandtabs(4).splitlines()
    depth = 0
    formatted = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            formatted.append("")
            continue
        if line.startswith("}"):
            depth = max(0, depth - 1)
        formatted.append("    " * depth + line)
        depth += line.count("{") - line.count("}")
        depth = max(0, depth)
    return "\n".join(formatted).rstrip() + "\n"


def format_file(path: str, write=False) -> str:
    source_path = Path(path)
    formatted = format_source(source_path.read_text(encoding="utf-8"))
    if write:
        source_path.write_text(formatted, encoding="utf-8")
    return formatted
