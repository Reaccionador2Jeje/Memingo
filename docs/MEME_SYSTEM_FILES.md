# M4 — System and file utilities

M4 adds three meme-themed packages that cover practical system-adjacent tasks without exposing unsafe process or shell execution.

## wherefile

Portable, string-only path helpers:

- `normalize_path(path)`: normalizes slash direction and resolves `.` / `..` segments.
- `basename(path)`, `dirname(path)`: extracts path components.
- `extension(path)`, `stem(path)`: splits a filename.
- `is_absolute(path)`: recognizes Unix and drive-letter absolute paths.
- `join_path(left, right)`: joins and normalizes paths.

This package manipulates path strings. It does not access the filesystem or guarantee that a path exists.

## themachine

Reads environment metadata through Memingo's existing `env()` helper:

- `machine_platform()`, `machine_architecture()`
- `machine_home()`, `machine_working_directory()`, `machine_user()`
- `machine_is_ci()`, `machine_is_windows()`, `machine_is_linux()`, `machine_is_macos()`

Platform and architecture can be provided through `MEMINGO_PLATFORM` and `MEMINGO_ARCH`. Unknown values remain `"unknown"`. These helpers do not launch commands or inspect privileged system state.

## snitch

Formats log messages with `log_debug()`, `log_info()`, `log_warning()` and `log_error()`. `format_log(level, message)` creates a consistent line, and `write_log(path, level, message)` appends a line using the project-scoped file helpers.

Logging is plain text; rotation, concurrent writers and structured JSON output are intentionally outside this package's current scope.

## Example

```mgo
borrow "wherefile"
borrow "themachine"
borrow "snitch"

spill join_path(machine_home(), "projects/memingo")
spill machine_platform()
write_log("app.log", "info", "Memingo is ready")
```

Every package provides `self_test()` for the registry's package validation.
