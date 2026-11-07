import os
import shutil
import sys
from contextlib import contextmanager
from time import monotonic, sleep


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
YELLOW = "\033[38;5;220m"
RED = "\033[38;5;203m"
GREEN = "\033[38;5;114m"
CYAN = "\033[38;5;81m"
WHITE = "\033[38;5;255m"


def supports_color():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(text, code):
    return f"{code}{text}{RESET}" if supports_color() else text


def width():
    return max(40, min(shutil.get_terminal_size(fallback=(80, 24)).columns, 100))


def rule(char="─"):
    return char * width()


def banner(version="0.2.0", subtitle="CODE THE BIT"):
    print(color("\n  MEMINGO", BOLD + YELLOW))
    print(color(f"  {subtitle}", DIM))
    print(color(f"  version {version}  ", CYAN))


def logo():
    print(color(r"  ▄▄▄  ▄▄▄  ▄▄▄  ▄▄ ", BOLD + YELLOW))
    print(color(r"  █▄▀  █▄█  █▀▄  █▄ ", BOLD + YELLOW))


def success(message):
    print(color("✓", GREEN + BOLD), message)


def info(message):
    print(color("•", CYAN + BOLD), message)


def warning(message):
    print(color("!", YELLOW + BOLD), message)


def error(message):
    print(color("×", RED + BOLD), message, file=sys.stderr)


def heading(title, subtitle=None):
    print()
    print(color(title.upper(), BOLD + WHITE))
    if subtitle:
        print(color(subtitle, DIM))
    print(color(rule("─"), DIM))


def key_value(rows, label_width=18):
    for label, value in rows:
        print(f"  {color(str(label).ljust(label_width), DIM + CYAN)} {value}")


def table(headers, rows):
    widths = [len(str(header)) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    print()
    header_line = "  ".join(str(header).ljust(widths[index]) for index, header in enumerate(headers))
    print(color(header_line.upper(), BOLD + CYAN))
    print(color("  ".join("─" * width for width in widths), DIM))
    for row in rows:
        print("  ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


@contextmanager
def spinner(message, complete="done"):
    if not supports_color() or not sys.stdout.isatty():
        info(message)
        yield
        success(complete)
        return
    frames = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
    started = monotonic()
    index = 0
    sys.stdout.write(f"\r{color(frames[index], CYAN)} {message}")
    sys.stdout.flush()
    try:
        yield
    finally:
        elapsed = monotonic() - started
        sys.stdout.write("\r  \r")
        success(f"{complete}  {elapsed:.2f}s")
        sys.stdout.flush()


def progress_bar(current, total, label=""):
    if total <= 0:
        return
    percentage = current / total
    bar_width = 32
    filled = int(bar_width * percentage)
    bar = "█" * filled + "░" * (bar_width - filled)
    output = f"\r{color(bar, CYAN)} {percentage:3.0%} {label}"
    sys.stdout.write(output)
    sys.stdout.flush()
    if current >= total:
        sys.stdout.write("\n")
