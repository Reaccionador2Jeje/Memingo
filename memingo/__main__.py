import argparse
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
from .formatter import format_file
from .mgoa import PackageError, add_package, install_project, remove_package
from .lexer import LexerError
from .packages import (
    add_dependency, init_project, install_dependencies,
    read_manifest, remove_dependency,
)
from .parser import ParseError, parse
from .server import serve
from .cli import banner, heading, key_value, success, info, error, warning, table, spinner


def run_file(path: str) -> int:
    try:
        source_path = Path(path).resolve()
        project_directory = source_path.parent
        with open(source_path, "r", encoding="utf-8") as source_file:
            for line in execute(source_file.read(), project_directory=project_directory):
                print(line)
        return 0
    except (LexerError, ParseError, RuntimeErrorMemingo) as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1


def repl() -> int:
    banner(__version__, "INTERACTIVE MEMINGO REPL")
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
            print(f"Memingo error: {error}", file=sys.stderr)


def run_project(directory=".") -> int:
    try:
        manifest = read_manifest(directory)
    except FileNotFoundError as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1
    entry = manifest.get("package", {}).get("entry", "main.mgo")
    return run_file(str(Path(directory).resolve() / entry))


def run_dev(directory=".", interval=0.5) -> int:
    manifest = read_manifest(directory)
    entry = Path(directory) / manifest.get("package", {}).get("entry", "main.mgo")
    last_signature = None
    banner(__version__, "MEMINGO DEV MODE")
    info("Watching for file changes. Press Ctrl+C to stop.")
    try:
        while True:
            signature = entry.stat().st_mtime_ns if entry.exists() else None
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


def build_project(directory=".", output="dist") -> int:
    manifest = read_manifest(directory)
    entry_name = manifest.get("package", {}).get("entry", "main.mgo")
    entry = Path(directory) / entry_name
    if not entry.exists():
        print(f"Memingo error: Missing entry file: {entry}", file=sys.stderr)
        return 1

    output_dir = Path(directory) / output
    output_dir.mkdir(parents=True, exist_ok=True)
    package_name = manifest.get("package", {}).get("name", "memingo-app")
    archive = output_dir / f"{package_name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(entry, entry_name)
        for source in Path(directory).glob("*.mgo"):
            if source != entry:
                bundle.write(source, source.name)
        bundle.write(Path(directory) / "memingo.toml", "memingo.toml")
    heading("Build complete")
    success(f"Archive: {archive}")
    return 0


def doctor() -> int:
    heading("Memingo Doctor", "installation diagnostics")
    executable = shutil.which("memingo")
    key_value([
        ("Python", sys.version.split()[0]),
        ("Module", str(Path(__file__).resolve().parent)),
        ("memingo PATH", executable or "not found"),
    ])
    if sys.version_info < (3, 10):
        error("Python 3.10 or newer is required")
        return 1
    if executable:
        success("Memingo installation is ready")
    else:
        warning("Memingo works as a module, but the command is missing from PATH")
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
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(directory), "-p", pattern],
        cwd=directory,
        check=False,
    )
    return result.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="memingo",
        description="Memingo programming language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  memingo init my-app\n  memingo run\n  memingo doctor\n  mgoa search",
    )
    parser.add_argument("--version", action="version", version=f"Memingo {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("repl", help="Open the interactive REPL")
    subparsers.add_parser("doctor", help="Check the Memingo installation")
    subparsers.add_parser("update-self", help="Update Memingo from the official installer")

    init_parser = subparsers.add_parser("init", help="Create a Memingo project")
    init_parser.add_argument("directory", nargs="?", default=".")
    init_parser.add_argument("--name", default="my-memingo-app")

    run_parser = subparsers.add_parser("run", help="Run a project or .mgo file")
    run_parser.add_argument("path", nargs="?", default=None)

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

    add_parser = subparsers.add_parser("add", help="Add a package dependency")
    add_parser.add_argument("spec")
    add_parser.add_argument("--project", default=".")

    remove_parser = subparsers.add_parser("remove", help="Remove a package dependency")
    remove_parser.add_argument("name")
    remove_parser.add_argument("--project", default=".")

    install_parser = subparsers.add_parser("install", help="Install project dependencies")
    install_parser.add_argument("directory", nargs="?", default=".")

    update_parser = subparsers.add_parser("update", help="Update installed dependencies")

    format_parser = subparsers.add_parser("fmt", help="Format Memingo source files")
    format_parser.add_argument("paths", nargs="+", help="Files or directories to format")
    format_parser.add_argument("--check", action="store_true", help="Check formatting without writing")
    update_parser.add_argument("directory", nargs="?", default=".")

    args = parser.parse_args(argv)

    if args.command is None:
        return repl()
    if args.command == "repl":
        return repl()
    if args.command == "doctor":
        return doctor()
    if args.command == "update-self":
        return update_self()
    if args.command == "init":
        manifest = init_project(args.directory, args.name)
        heading("Project created", args.name)
        success(f"Manifest: {manifest}")
        return 0
    if args.command == "run":
        if args.path:
            return run_file(args.path)
        return run_project(".")
    if args.command == "dev":
        return run_dev(args.directory)
    if args.command == "build":
        return build_project(args.directory, args.output)
    if args.command == "test":
        return run_tests(args.directory, args.pattern)
    if args.command == "serve":
        serve(args.directory, args.host, args.port)
        return 0
    if args.command == "add":
        try:
            project_path = Path(args.project).resolve()
            if not (project_path / "memingo.toml").exists():
                raise FileNotFoundError(f"Missing project manifest: {project_path / 'memingo.toml'}")
            installed = add_package(project_path, args.spec)
            success(f"Added approved dependency {installed['name']}@{installed['version']}")
            return 0
        except Exception as exception:
            error(f"Memingo add error: {exception}")
            return 1
    if args.command == "remove":
        try:
            project_path = Path(args.project).resolve()
            if not (project_path / "memingo.toml").exists():
                raise FileNotFoundError(f"Missing project manifest: {project_path / 'memingo.toml'}")
            remove_package(project_path, args.name)
            success(f"Removed dependency {args.name}")
            return 0
        except Exception as exception:
            error(f"Memingo remove error: {exception}")
            return 1
    if args.command == "install":
        try:
            project_path = Path(args.directory).resolve()
            if not (project_path / "memingo.toml").exists():
                raise FileNotFoundError(f"Missing project manifest: {project_path / 'memingo.toml'}")
            manifest = read_manifest(project_path)
            if not manifest.get("dependencies", {}):
                info("No dependencies to install")
                return 0
            dependencies = install_project(project_path)
            heading("Dependencies installed", str(len(dependencies)))
            success(f"{len(dependencies)} approved package(s) ready")
            return 0
        except Exception as exception:
            error(f"Memingo install error: {exception}")
            return 1
    if args.command == "update":
        try:
            project_path = Path(args.directory).resolve()
            if not (project_path / "memingo.toml").exists():
                raise FileNotFoundError(f"Missing project manifest: {project_path / 'memingo.toml'}")
            manifest = read_manifest(project_path)
            if not manifest.get("dependencies", {}):
                info("No dependencies to update")
                return 0
            dependencies = install_project(project_path)
            heading("Dependencies updated", str(len(dependencies)))
            success(f"{len(dependencies)} approved package(s) ready")
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
                original = source_file.read_text(encoding="utf-8")
                formatted = format_file(source_file)
                if args.check and original != formatted:
                    warning(f"Would format: {source_file}")
                    changed += 1
                elif not args.check and original != formatted:
                    source_file.write_text(formatted, encoding="utf-8")
                    success(f"Formatted: {source_file}")
                    changed += 1
        return 1 if args.check and changed else 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
