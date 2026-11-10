import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

from . import __version__
from .interpreter import Interpreter, RuntimeErrorMemingo, execute
from .formatter import format_source
from .diagnostics import render_diagnostic
from .mgoa import PackageError, add_package, install_project, remove_package
from .lexer import LexerError
from .packages import ensure_project, init_project, read_manifest, resolve_entry
from .parser import ParseError, parse
from .server import MemingoApp, serve, serve_app
from .cli import (
    banner, heading, key_value, success, info, error, warning, table, panel,
    status_bar, tip, command_header, CYAN, GREEN, YELLOW,
)
from .completion import memingo_completion
from .lsp import run_language_server


def run_ide_web(host="127.0.0.1", port=3000) -> int:
    """Launch the separately installed Memingo IDE Web server."""
    executable = shutil.which("memingo-ide-web")
    if not executable:
        print(
            "Memingo IDE Web no está instalado o no está disponible en PATH.\n"
            "Desde el repositorio Memingo-IDE ejecuta: npm install && npm link",
            file=sys.stderr,
        )
        return 127
    # El proceso Node.js imprime la URL cuando el socket ya está escuchando.
    # subprocess.call mantiene este comando en primer plano hasta Ctrl+C.
    try:
        return subprocess.call([executable, "--host", host, "--port", str(port)])
    except OSError as exception:
        print(f"Memingo IDE Web error: {exception}", file=sys.stderr)
        return 1


def serve_api(path="app.py", host="127.0.0.1", port=8000) -> int:
    """Run a native .mgo API or a Python module exporting a MemingoApp."""
    source_path = Path(path).resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"API application file does not exist: {source_path}")

    if source_path.suffix.lower() == ".mgo":
        source = source_path.read_text(encoding="utf-8")
        interpreter = Interpreter(project_directory=source_path.parent)
        interpreter.api_host = host
        interpreter.api_port = port
        interpreter.run(parse(source))
        if not interpreter.api_server_started:
            raise ValueError(f"{source_path.name} must call api_listen(app)")
        return 0

    spec = importlib.util.spec_from_file_location("memingo_user_api", source_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load API application: {source_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = getattr(module, "app", None)
    if not isinstance(app, MemingoApp):
        raise ValueError(f"{source_path.name} must export 'app = MemingoApp()'")
    serve_app(app, host, port)
    return 0


def run_file(path: str) -> int:
    source_path = Path(path).resolve()
    source = ""
    try:
        project_directory = source_path.parent
        source = source_path.read_text(encoding="utf-8")
        for line in execute(source, project_directory=project_directory):
            print(line)
        return 0
    except (LexerError, ParseError, RuntimeErrorMemingo) as error:
        print(render_diagnostic(error, source, str(source_path)), file=sys.stderr)
        return 1
    except UnicodeError:
        print(f"Memingo error: {path} is not valid UTF-8", file=sys.stderr)
        return 1
    except RecursionError:
        print("Memingo error: Maximum recursion depth exceeded", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    except OSError as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1


def run_source(source: str, project_directory=".") -> int:
    try:
        for line in execute(source, project_directory=project_directory):
            print(line)
        return 0
    except (LexerError, ParseError, RuntimeErrorMemingo) as error:
        print(render_diagnostic(error, source, "<eval>"), file=sys.stderr)
        return 1
    except RecursionError:
        print("Memingo error: Maximum recursion depth exceeded", file=sys.stderr)
        return 1
    except UnicodeError:
        print("Memingo error: source is not valid UTF-8", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
    except OSError as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1


def project_stats(directory=".") -> int:
    try:
        root = Path(directory).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Project directory does not exist: {root}")
        files = sorted(root.rglob("*.mgo"))
        excluded = {".git", ".memingo", "dist", "__pycache__", "node_modules", ".venv"}
        files = [path for path in files if not (excluded & set(path.relative_to(root).parts))]
        lines = 0
        rituals = 0
        spills = 0
        for source_file in files:
            source = source_file.read_text(encoding="utf-8")
            lines += len(source.splitlines())
            rituals += sum(1 for line in source.splitlines() if line.lstrip().startswith("ritual "))
            spills += sum(1 for line in source.splitlines() if line.lstrip().startswith("spill "))
        heading("Memingo stats", str(root))
        key_value([
            ("MGO files", str(len(files))),
            ("Lines", str(lines)),
            ("Rituals", str(rituals)),
            ("Spills", str(spills)),
        ])
        return 0
    except (FileNotFoundError, OSError, UnicodeError, ValueError) as exception:
        error(f"Memingo stats error: {exception}")
        return 1


def check_sources(paths) -> int:
    files = []
    for input_path in paths:
        path = Path(input_path)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.mgo")))
        elif path.exists():
            files.append(path)
        else:
            print(f"Memingo error: File not found: {path}", file=sys.stderr)
            return 1
    if not files:
        print("Memingo error: No .mgo files found", file=sys.stderr)
        return 1
    checked = 0
    for source_file in files:
        try:
            source = source_file.read_text(encoding="utf-8")
            parse(source)
        except (LexerError, ParseError) as error:
            print(render_diagnostic(error, source, str(source_file)), file=sys.stderr)
            return 1
        except (UnicodeError, OSError) as error:
            print(f"Memingo error: {source_file}: {error}", file=sys.stderr)
            return 1
        checked += 1
    success(f"{checked} file(s) checked")
    return 0


def _dependency_rows(root):
    data = read_manifest(root)
    dependencies = data.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError("[dependencies] must be a table in memingo.toml")
    records = {}
    lock_path = root / "memingo.lock.json"
    if lock_path.exists():
        try:
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeError):
            lock = {}
        if isinstance(lock, dict) and isinstance(lock.get("dependencies"), dict):
            records = lock["dependencies"]
    rows = []
    for name in sorted(dependencies):
        requested = dependencies[name]
        record = records.get(name)
        if not isinstance(record, dict):
            record = {}
        source = record.get("source")
        if not source:
            if record.get("url"):
                source = "url"
            elif record.get("path"):
                source = "local"
            elif record.get("registry"):
                source = "registry"
            else:
                source = "manifest"
        installed = "yes" if (root / ".memingo" / "packages" / str(name)).is_dir() else "no"
        rows.append([
            str(name),
            str(requested) if requested not in (None, "") else "*",
            str(record.get("version", "-")),
            str(source),
            "yes" if record.get("approved") is True else "no",
            installed,
        ])
    return dependencies, records, rows


def project_info(directory=".") -> int:
    try:
        root = Path(directory).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Project directory does not exist: {root}")
        manifest, entry_name, entry_path = resolve_entry(root)
        package = manifest.get("package", {})
        dependencies, _, rows = _dependency_rows(root)
        heading("Project info", str(root))
        key_value([
            ("Name", package.get("name", "unnamed")),
            ("Version", package.get("version", "0.0.0")),
            ("Entry", entry_name),
            ("Entry exists", "yes" if entry_path.is_file() else "no"),
            ("Dependencies", str(len(dependencies))),
            ("Lockfile", "yes" if (root / "memingo.lock.json").exists() else "no"),
        ])
        if rows:
            table(["package", "requested", "locked", "source", "approved", "installed"], rows)
        else:
            info("No dependencies")
        return 0
    except (FileNotFoundError, OSError, ValueError) as exception:
        error(f"Memingo info error: {exception}")
        return 1


def project_dependencies(directory=".") -> int:
    try:
        root = Path(directory).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Project directory does not exist: {root}")
        _, _, rows = _dependency_rows(root)
        if not rows:
            info("No dependencies")
            return 0
        heading("Dependencies", str(root))
        table(["package", "requested", "locked", "source", "approved", "installed"], rows)
        return 0
    except (FileNotFoundError, OSError, ValueError) as exception:
        error(f"Memingo deps error: {exception}")
        return 1


def clean_project(directory=".", dry_run=False) -> int:
    try:
        root = Path(directory).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Project directory does not exist: {root}")
        targets = []
        for name in (".memingo", "dist"):
            target = root / name
            if target.exists() or target.is_symlink():
                targets.append(target)
        for cache in sorted(root.rglob("__pycache__")):
            if cache.is_dir() and not cache.is_symlink() and root in cache.parents:
                targets.append(cache)
        removed = 0
        heading("Clean", str(root))
        for target in targets:
            if not target.exists() and not target.is_symlink():
                continue
            if dry_run:
                info(f"Would remove: {target}")
            else:
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
                success(f"Removed: {target}")
            removed += 1
        if not removed:
            info("Nothing to clean")
        elif dry_run:
            info(f"{removed} path(s) would be removed")
        return 0
    except (OSError, ValueError) as exception:
        error(f"Memingo clean error: {exception}")
        return 1


def project_status(directory=".") -> int:
    try:
        root = Path(directory).resolve()
        manifest = ensure_project(root)
        data = read_manifest(root)
        package = data.get("package", {})
        dependencies = data.get("dependencies", {})
        if not isinstance(dependencies, dict):
            dependencies = {}
        source_files = [
            path for path in root.rglob("*.mgo")
            if not ({".git", ".memingo", "dist", "__pycache__", "node_modules", ".venv"} & set(path.relative_to(root).parts))
        ]
        banner(__version__, "SYSTEM STATUS")
        status_bar([
            ("Python", sys.version.split()[0], CYAN),
            ("Project", package.get("name", root.name), GREEN),
            ("Version", package.get("version", __version__), YELLOW),
        ])
        panel("Workspace", [
            f"Entry          {package.get('entry', 'main.mgo')}",
            f"Manifest       {manifest}",
            f"Source files   {len(source_files)}",
            f"Dependencies   {len(dependencies)}",
        ])
        return 0
    except (OSError, ValueError) as exception:
        error(f"Memingo status error: {exception}")
        return 1


def repl() -> int:
    banner(__version__, "INTERACTIVE MEMINGO REPL")
    status_bar([
        ("Language", "Memingo", CYAN),
        ("Mode", "REPL", YELLOW),
        ("Version", __version__, GREEN),
    ])
    tip("Type a Memingo ritual, then press Enter. Ctrl+D exits.")
    info("Write Memingo code. Press Ctrl+D to exit.")
    interpreter = Interpreter(project_directory=Path.cwd())
    while True:
        try:
            source = input("memingo> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        try:
            previous_output_count = len(interpreter.output)
            result = interpreter.run(parse(source))
            for line in interpreter.output[previous_output_count:]:
                print(line)
            if result is not None and len(interpreter.output) == previous_output_count:
                print(result)
        except (LexerError, ParseError, RuntimeErrorMemingo) as error:
            print(render_diagnostic(error, source, "<repl>"), file=sys.stderr)
        except (RecursionError, UnicodeError) as error:
            print(f"Memingo error: {error}", file=sys.stderr)
        except KeyboardInterrupt:
            print()
            return 0


def run_project(directory=".") -> int:
    try:
        _, _, entry = resolve_entry(directory)
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1
    return run_file(str(entry))


def run_dev(directory=".", interval=0.5) -> int:
    _, _, entry = resolve_entry(directory)
    last_signature = None
    banner(__version__, "MEMINGO DEV MODE")
    info("Watching for file changes. Press Ctrl+C to stop.")
    try:
        while True:
            signature = _project_signature(directory)
            if signature != last_signature:
                print(f"\n--- running {entry} ---")
                run_file(str(entry))
                last_signature = signature
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nDev mode stopped.")
        return 0
    except FileNotFoundError as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1


def _project_signature(directory):
    root = Path(directory).resolve()
    files = [root / "memingo.toml", root / ".env"]
    files.extend(root.rglob("*.mgo"))
    signature = []
    for source in sorted(files):
        if not source.is_file():
            continue
        parts = set(source.relative_to(root).parts)
        if parts & {".git", ".memingo", "dist", "__pycache__", "node_modules", ".venv"}:
            continue
        signature.append((source.relative_to(root).as_posix(), source.stat().st_mtime_ns))
    return tuple(signature)


def build_project(directory=".", output="dist") -> int:
    manifest, _, entry = resolve_entry(directory)
    package = manifest.get("package", {})
    root = Path(directory).resolve()
    if not entry.is_file():
        print(f"Memingo error: Missing entry file: {entry}", file=sys.stderr)
        return 1

    output_dir = (root / output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = package.get("name", "memingo-app")
    archive = output_dir / f"{package_name}.zip"
    ignored = {".git", ".memingo", "__pycache__", "node_modules", ".venv", ".env", output_dir.name}
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source in sorted(root.rglob("*")):
            if not source.is_file():
                continue
            relative = source.relative_to(root)
            if set(relative.parts) & ignored:
                continue
            if source.resolve() == archive.resolve():
                continue
            bundle.write(source, relative.as_posix())
    heading("Build complete")
    success(f"Archive: {archive}")
    return 0


def doctor() -> int:
    executable = shutil.which("memingo")
    package_manager = shutil.which("mgoa")
    banner(__version__, "SYSTEM DIAGNOSTICS")
    status_bar([
        ("Python", sys.version.split()[0], CYAN),
        ("memingo", "ready" if executable else "module", GREEN if executable else YELLOW),
        ("mgoa", "ready" if package_manager else "module", GREEN if package_manager else YELLOW),
    ])
    heading("Memingo Doctor", "installation diagnostics")
    key_value([
        ("Python", sys.version.split()[0]),
        ("Platform", sys.platform),
        ("Module", str(Path(__file__).resolve().parent)),
        ("memingo PATH", executable or "not found"),
        ("mgoa PATH", package_manager or "not found"),
    ])
    if sys.version_info < (3, 10):
        error("Python 3.10 or newer is required")
        return 1
    if executable:
        success("Memingo installation is ready")
    else:
        warning("Memingo works as a module, but the command is missing from PATH")
    if not package_manager:
        warning("mgoa works as a module, but the package manager command is missing from PATH")
    return 0


def update_self() -> int:
    base_url = "https://github.com/Reaccionador2Jeje/Memingo/raw/refs/heads/main/site/downloads"
    if os.name == "nt":
        script_name = "install.ps1"
    else:
        script_name = "install.sh"

    temporary = tempfile.TemporaryDirectory(prefix="memingo-update-")
    script_path = Path(temporary.name) / script_name
    try:
        urllib.request.urlretrieve(base_url + "/" + script_name, script_path)
        if os.name == "nt":
            command = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script_path)]
        else:
            script_path.chmod(0o755)
            command = ["sh", str(script_path)]
        result = subprocess.run(command, check=False)
        return result.returncode
    except Exception as exception:
        error(f"Memingo update failed: {exception}")
        return 1


def run_tests(directory=".", pattern="test*.py") -> int:
    root = Path(directory).resolve()
    if not root.is_dir():
        print(f"Memingo error: Test directory does not exist: {root}", file=sys.stderr)
        return 1
    environment = os.environ.copy()
    search_paths = [str(Path(__file__).resolve().parent.parent), str(Path.cwd()), str(root)]
    existing = environment.get("PYTHONPATH")
    if existing:
        search_paths.append(existing)
    environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(search_paths))
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", ".", "-p", pattern],
        cwd=root,
        env=environment,
        check=False,
    )
    return result.returncode



def debug_file(path: str, breakpoints=None) -> int:
    """Run a file and emit a machine-readable statement trace for IDE debuggers."""
    source_path = Path(path).resolve()
    try:
        source = source_path.read_text(encoding="utf-8")
        interpreter = Interpreter(project_directory=source_path.parent)
        trace = []
        interpreter.debug_trace = trace
        exit_code = 0
        error_message = None
        try:
            interpreter.run(parse(source))
        except (LexerError, ParseError, RuntimeErrorMemingo, RecursionError, UnicodeError) as exception:
            exit_code = 1
            error_message = str(exception)
        selected = set(breakpoints or [])
        for index, event in enumerate(trace):
            event["index"] = index
            event["breakpoint"] = event.get("line") in selected
        payload = {
            "file": str(source_path),
            "events": trace,
            "output": interpreter.output,
            "error": error_message,
            "exitCode": exit_code,
        }
        print("MEMINGO_DEBUG:" + json.dumps(payload, ensure_ascii=False))
        return exit_code
    except (OSError, UnicodeError) as exception:
        print("MEMINGO_DEBUG:" + json.dumps({
            "file": str(source_path), "events": [], "output": [],
            "error": str(exception), "exitCode": 1,
        }, ensure_ascii=False))
        return 1


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="memingo",
        description="Memingo programming language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  memingo init my-app\n  memingo run\n  memingo eval 'spill 2 + 2'\n  memingo check examples\n  memingo info\n  memingo doctor\n  mgoa search",
    )
    parser.add_argument("--version", action="version", version=f"Memingo {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("repl", help="Open the interactive REPL")
    subparsers.add_parser("doctor", help="Check the Memingo installation")
    subparsers.add_parser("update-self", help="Update Memingo from the official installer")
    status_parser = subparsers.add_parser("status", help="Show a complete project and runtime dashboard")
    status_parser.add_argument("directory", nargs="?", default=".")

    init_parser = subparsers.add_parser("init", help="Create a Memingo project")
    init_parser.add_argument("directory", nargs="?", default=".")
    init_parser.add_argument("--name", default="my-memingo-app")

    manifest_parser = subparsers.add_parser("manifest", help="Create a missing memingo.toml")
    manifest_parser.add_argument("directory", nargs="?", default=".")
    manifest_parser.add_argument("--name", default=None)

    run_parser = subparsers.add_parser("run", help="Run a project or .mgo file")
    run_parser.add_argument("path", nargs="?", default=None)

    debug_parser = subparsers.add_parser("debug", help="Run a file and collect a statement-by-statement debug trace")
    debug_parser.add_argument("path", help="Memingo .mgo source file")
    debug_parser.add_argument("--breakpoints", default="", help="Comma-separated source line numbers to mark")

    eval_parser = subparsers.add_parser("eval", help="Run Memingo code from the command line")
    eval_parser.add_argument("code", nargs="+", help="Memingo source code")
    eval_parser.add_argument("--project", default=".", help="Project directory used for borrow and .env")

    check_parser = subparsers.add_parser("check", help="Parse Memingo files without running them")
    check_parser.add_argument("paths", nargs="*", default=["."], help="Files or directories to check")

    stats_parser = subparsers.add_parser("stats", help="Summarize Memingo source files in a project")
    stats_parser.add_argument("directory", nargs="?", default=".")

    info_parser = subparsers.add_parser("info", help="Show project information")
    info_parser.add_argument("directory", nargs="?", default=".")

    deps_parser = subparsers.add_parser("deps", help="List project dependencies")
    deps_parser.add_argument("directory", nargs="?", default=".")

    clean_parser = subparsers.add_parser("clean", help="Remove generated files and caches")
    clean_parser.add_argument("directory", nargs="?", default=".")
    clean_parser.add_argument("--dry-run", action="store_true", help="Show what would be removed")

    dev_parser = subparsers.add_parser("dev", help="Run a project whenever files change")
    dev_parser.add_argument("directory", nargs="?", default=".")

    build_parser = subparsers.add_parser("build", help="Build a project archive")
    build_parser.add_argument("directory", nargs="?", default=".")
    build_parser.add_argument("-o", "--output", default="dist")

    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("directory", nargs="?", default=".")
    test_parser.add_argument("-p", "--pattern", default="test*.py")

    serve_parser = subparsers.add_parser("serve", help="Serve static files over HTTP")
    serve_parser.add_argument("directory", nargs="?", default=".")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    api_parser = subparsers.add_parser("api", help="Run a route-based HTTP application")
    api_parser.add_argument("file", nargs="?", default="app.py")
    api_parser.add_argument("--host", default="127.0.0.1")
    api_parser.add_argument("--port", type=int, default=8000)

    add_parser = subparsers.add_parser("add", help="Add a package dependency")
    add_parser.add_argument("spec")
    add_parser.add_argument("--project", default=".")

    remove_parser = subparsers.add_parser("remove", help="Remove a package dependency")
    remove_parser.add_argument("name")
    remove_parser.add_argument("--project", default=".")

    install_parser = subparsers.add_parser("install", help="Install project dependencies")
    install_parser.add_argument("directory", nargs="?", default=".")

    update_parser = subparsers.add_parser("update", help="Update installed dependencies")
    update_parser.add_argument("directory", nargs="?", default=".")

    format_parser = subparsers.add_parser("fmt", help="Format Memingo source files")
    format_parser.add_argument("paths", nargs="+", help="Files or directories to format")
    format_parser.add_argument("--check", action="store_true", help="Check formatting without writing")

    completion_parser = subparsers.add_parser("completion", help="Print shell completion scripts")
    completion_parser.add_argument("shell", choices=("bash", "zsh", "fish"))

    ide_parser = subparsers.add_parser("ide", help="Launch Memingo IDE Web on localhost")
    ide_parser.add_argument("--host", default="127.0.0.1", help="Local interface (loopback only)")
    ide_parser.add_argument("--port", type=int, default=3000, help="HTTP port (default: 3000)")

    lsp_parser = subparsers.add_parser("lsp", help="Start the Memingo Language Server Protocol server")
    lsp_parser.add_argument("--stdio", action="store_true", help="Use the standard LSP stdio transport")

    args = parser.parse_args(argv)

    raw_output_commands = {"completion", "ide", "lsp", "run", "debug", "eval", "repl", "dev", "serve", "api", "test"}
    if args.command not in raw_output_commands and args.command is not None:
        command_header("memingo", args.command)

    if args.command is None:
        return repl()
    if args.command == "repl":
        return repl()
    if args.command == "doctor":
        return doctor()
    if args.command == "update-self":
        return update_self()
    if args.command == "status":
        return project_status(args.directory)
    if args.command == "init":
        try:
            manifest = init_project(args.directory, args.name)
        except (OSError, ValueError) as exception:
            error(f"Memingo init error: {exception}")
            return 1
        heading("Project created", args.name)
        success(f"Manifest: {manifest}")
        return 0
    if args.command == "manifest":
        try:
            root = Path(args.directory).resolve()
            existed = (root / "memingo.toml").exists()
            manifest = ensure_project(root, args.name)
        except (OSError, ValueError) as exception:
            error(f"Memingo manifest error: {exception}")
            return 1
        if existed:
            info(f"Manifest already exists: {manifest}")
        else:
            heading("Project manifest created", args.name or root.name)
            success(f"Manifest: {manifest}")
        return 0
    if args.command == "run":
        if args.path:
            target = Path(args.path)
            if target.is_dir():
                return run_project(target)
            return run_file(args.path)
        return run_project(".")
    if args.command == "debug":
        try:
            breakpoints = [int(value) for value in args.breakpoints.split(",") if value.strip()]
            if any(value < 1 for value in breakpoints):
                raise ValueError("Breakpoint line numbers must be positive")
            return debug_file(args.path, breakpoints)
        except ValueError as exception:
            print(f"Memingo debug error: {exception}", file=sys.stderr)
            return 2
    if args.command == "eval":
        return run_source(" ".join(args.code), args.project)
    if args.command == "check":
        return check_sources(args.paths)
    if args.command == "lsp":
        return run_language_server()
    if args.command == "ide":
        if not 1 <= args.port <= 65535:
            error("Memingo IDE Web port must be between 1 and 65535.")
            return 2
        if args.host not in ("127.0.0.1", "localhost", "::1"):
            error("Memingo IDE Web solo permite interfaces localhost por seguridad.")
            return 2
        return run_ide_web(args.host, args.port)
    if args.command == "completion":
        try:
            print(memingo_completion(args.shell), end="")
            return 0
        except ValueError as exception:
            error(str(exception))
            return 1
    if args.command == "stats":
        return project_stats(args.directory)
    if args.command == "info":
        return project_info(args.directory)
    if args.command == "deps":
        return project_dependencies(args.directory)
    if args.command == "clean":
        return clean_project(args.directory, args.dry_run)
    if args.command == "dev":
        try:
            return run_dev(args.directory)
        except (FileNotFoundError, OSError, ValueError) as exception:
            error(f"Memingo dev error: {exception}")
            return 1
    if args.command == "build":
        try:
            return build_project(args.directory, args.output)
        except (FileNotFoundError, OSError, ValueError) as exception:
            error(f"Memingo build error: {exception}")
            return 1
    if args.command == "test":
        return run_tests(args.directory, args.pattern)
    if args.command == "serve":
        try:
            serve(args.directory, args.host, args.port)
        except (OSError, ValueError) as exception:
            error(f"Memingo serve error: {exception}")
            return 1
        return 0
    if args.command == "api":
        try:
            return serve_api(args.file, args.host, args.port)
        except (OSError, ValueError, ImportError, LexerError, ParseError, RuntimeErrorMemingo, UnicodeError) as exception:
            error(f"Memingo API error: {exception}")
            return 1
    if args.command == "add":
        try:
            project_path = Path(args.project).resolve()
            installed = add_package(project_path, args.spec)
            success(f"Added dependency {installed['name']}@{installed['version']}")
            return 0
        except Exception as exception:
            error(f"Memingo add error: {exception}")
            return 1
    if args.command == "remove":
        try:
            project_path = Path(args.project).resolve()
            remove_package(project_path, args.name)
            success(f"Removed dependency {args.name}")
            return 0
        except Exception as exception:
            error(f"Memingo remove error: {exception}")
            return 1
    if args.command == "install":
        try:
            project_path = Path(args.directory).resolve()
            ensure_project(project_path)
            manifest = read_manifest(project_path)
            dependencies = install_project(project_path)
            if not manifest.get("dependencies", {}):
                info("No dependencies to install")
                return 0
            heading("Dependencies installed", str(len(dependencies)))
            success(f"{len(dependencies)} package(s) ready")
            return 0
        except Exception as exception:
            error(f"Memingo install error: {exception}")
            return 1
    if args.command == "update":
        try:
            project_path = Path(args.directory).resolve()
            ensure_project(project_path)
            manifest = read_manifest(project_path)
            dependencies = install_project(project_path, frozen=False)
            if not manifest.get("dependencies", {}):
                info("No dependencies to update")
                return 0
            heading("Dependencies updated", str(len(dependencies)))
            success(f"{len(dependencies)} package(s) ready")
            return 0
        except Exception as exception:
            error(f"Memingo update error: {exception}")
            return 1
    if args.command == "fmt":
        changed = 0
        for input_path in args.paths:
            path = Path(input_path)
            files = list(path.rglob("*.mgo")) if path.is_dir() else [path]
            for source_file in files:
                if not source_file.exists():
                    print(f"Memingo error: File not found: {source_file}", file=sys.stderr)
                    return 1
                try:
                    original = source_file.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exception:
                    error(f"Memingo fmt error: {source_file}: {exception}")
                    return 1
                formatted = format_source(original)
                if args.check and original != formatted:
                    warning(f"Would format: {source_file}")
                    changed += 1
                elif not args.check and original != formatted:
                    try:
                        source_file.write_text(formatted, encoding="utf-8")
                    except OSError as exception:
                        error(f"Memingo fmt error: {source_file}: {exception}")
                        return 1
                    success(f"Formatted: {source_file}")
                    changed += 1
        return 1 if args.check and changed else 0
    parser.print_help()
    return 2


def main(argv=None) -> int:
    # Replace unsupported terminal glyphs on legacy Windows consoles.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (OSError, ValueError):
                pass
    try:
        code = _main(argv)
        try:
            sys.stdout.flush()
        except BrokenPipeError:
            code = 0
        return code
    except KeyboardInterrupt:
        print("\nMemingo interrupted.", file=sys.stderr)
        return 130
    except BrokenPipeError:
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except OSError:
            pass
        return 0
    except SystemExit:
        raise
    except Exception as exception:
        print(f"Memingo error: {exception}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())