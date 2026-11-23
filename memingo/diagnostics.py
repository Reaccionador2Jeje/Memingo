"""Meme-native diagnostics for Memingo source errors."""

import difflib
import re

from .lexer import LexerError
from .parser import ParseError


ERRORS = {
    "SKILL_ISSUE": ("💀", "SKILL ISSUE", "A name or operation is not available."),
    "BRUH": ("🤨", "BRUH", "The source code could not be understood."),
    "RATIO": ("📉", "RATIO", "The operation does not work with these values."),
    "GHOSTED": ("👻", "GHOSTED", "The value you tried to use is missing."),
    "OVERCOOKED": ("🔥", "OVERCOOKED", "Execution reached a safety limit."),
    "SUS": ("🧐", "SUS", "Something about this operation is invalid."),
}

KEYWORDS = {
    "vibe", "ritual", "drop", "when", "nah", "grind", "spill", "borrow",
    "based", "cringe", "ghost",
}


def classify_error(exception):
    message = str(exception)
    if isinstance(exception, (LexerError, ParseError)):
        return "BRUH"
    lowered = message.lower()
    if "undefined variable" in lowered or "attempted to call a non-function" in lowered:
        return "SKILL_ISSUE"
    if "division by zero" in lowered or "requires numbers" in lowered or "requires a number" in lowered:
        return "RATIO"
    if "cannot access" in lowered or "ghost" in lowered or "not found" in lowered:
        return "GHOSTED"
    if "limit reached" in lowered or "recursion" in lowered or "maximum recursion" in lowered:
        return "OVERCOOKED"
    return "SUS"


def _location(message):
    match = re.search(r"line (\d+), column (\d+)", message)
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)


def _suggestion(message, source):
    missing = re.search(r"Undefined variable ['\"]([^'\"]+)['\"]", message)
    if not missing:
        return None
    candidates = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", source))
    candidates.difference_update(KEYWORDS)
    candidates.discard(missing.group(1))
    matches = difflib.get_close_matches(missing.group(1), sorted(candidates), n=1, cutoff=0.72)
    return f"Did you mean '{matches[0]}'?" if matches else "Check the spelling or declare the variable with 'vibe'."


def format_diagnostic(exception, source="", filename="<source>", mode="meme"):
    """Render a stable diagnostic in meme or automation-friendly serious mode."""
    message = str(exception)
    line, column = _location(message)
    if mode == "serious":
        location = f"{filename}:{line}:{column}" if line is not None else filename
        return f"{location}: error: {message}"

    code = classify_error(exception)
    emoji, title, hint = ERRORS[code]
    lines = source.splitlines()
    output = [f"{emoji} {title}: {message}"]
    if line is not None:
        output.append(f"📍 {filename}:{line}:{column}")
        if 1 <= line <= len(lines):
            text = lines[line - 1]
            output.append(f"  {line:>3} | {text}")
            output.append(f"      | {' ' * max(0, column - 1)}^")
    else:
        output.append(f"📍 {filename}")
    suggestion = _suggestion(message, source)
    output.append(f"💡 {suggestion or hint}")
    return "\n".join(output)
