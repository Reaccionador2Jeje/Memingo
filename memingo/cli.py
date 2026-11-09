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
MAGENTA = "\033[38;5;213m"
BLUE = "\033[38;5;75m"


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
    print()
    print(color("  ╭────────────────────╮", YELLOW))
    print(color("  │       MEMINGO       │", BOLD + YELLOW))
    print(color("  ╰───┬────────────┬───╯", YELLOW))
    print(color("      │  " + subtitle[:18].upper().ljust(18) + "  │  " + f"v{version}", BOLD + CYAN))
    print(color("      ╰──────────────╯", DIM))


def logo():
    print(color(r"  ▄▄▄  ▄▄▄  ▄▄▄  ▄▄ ", BOLD + YELLOW))
    print(color(r"  █▄▀  █▄█  █▀▄  █▄ ", BOLD + YELLOW))


def brand_mark():
    print(color("  ◆ MEMINGO SYSTEMS", BOLD + MAGENTA))


def command_header(program, command=None, subtitle=None):
    label = program.upper() if command is None else f"{program.upper()} / {command.upper()}"
    detail = subtitle or "MEMINGO COMMAND SYSTEM"
    print()
    print(color("  ╭─" + "─" * min(width() - 4, 52) + "╮", CYAN))
    print(color("  │ ◆", MAGENTA + BOLD) + " " + color(label.ljust(48), BOLD + WHITE))
    print(color("  │", CYAN) + " " + color(detail, DIM))
    print(color("  ╰─" + "─" * min(width() - 4, 52) + "╯", CYAN))


def success(message):
    print(color("  ✓", GREEN + BOLD), color(message, WHITE))


def info(message):
    print(color("•", CYAN + BOLD), message)


def warning(message):
    print(color("!", YELLOW + BOLD), message)


def error(message):
    print(color("×", RED + BOLD), message, file=sys.stderr)


def heading(title, subtitle=None):
    print()
    print(color("  ┌─ " + title.upper(), BOLD + YELLOW))
    print(color("  │", DIM), color(subtitle, CYAN) if subtitle else "")
    print(color("  └" + "─" * max(12, width() - 4), DIM))


def key_value(rows, label_width=18):
    print(color("  ┌" + "─" * (label_width + 2), DIM))
    for label, value in rows:
        print(color("  │", DIM) + " " + color(str(label).upper().ljust(label_width), CYAN) + color("  " + str(value), WHITE))
    print(color("  └" + "─" * (label_width + 2), DIM))


def panel(title, lines, accent=CYAN):
    max_width = max([len(str(title))] + [len(str(line)) for line in lines])
    max_width = max(24, min(max_width + 4, width() - 4))
    print()
    print(color("  ╭─ " + title.upper().ljust(max_width - 3) + "╮", accent))
    for line in lines:
        print(color("  │", accent) + " " + str(line).ljust(max_width - 1) + color("│", accent))
    print(color("  ╰" + "─" * (max_width + 1) + "╯", accent))


def status_bar(items):
    segments = []
    for label, value, tone in items:
        segments.append(color(label.upper(), DIM) + " " + color(str(value), tone + BOLD))
    print()
    print("  " + color(" ◆ ", MAGENTA + BOLD) + color("  │  ".join(segments), WHITE))


def tip(message):
    print(color("  ↳ ", YELLOW + BOLD) + color("TIP  ", DIM) + message)


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
