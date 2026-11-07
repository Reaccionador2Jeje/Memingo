import argparse
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from . import __version__
from .interpreter import Interpreter, RuntimeErrorMemingo, execute
from .lexer import LexerError
from .packages import (
    add_dependency, init_project, install_dependencies,
    read_manifest, remove_dependency,
)
from .parser import ParseError, parse
from .server import serve


def run_file(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as source_file:
            for line in execute(source_file.read()):
                print(line)
        return 0
    except (LexerError, ParseError, RuntimeErrorMemingo) as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Memingo error: {error}", file=sys.stderr)
        return 1


def repl() -> int:
    print(f"Memingo {__version__}")
    print("Escribe codigo Memingo. Usa Ctrl+D para salir.")
    interpreter = Interpreter()
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
    return run_file(str(Path(directory) / entry))


def run_dev(directory=".", interval=0.5) -> int:
    manifest = read_manifest(directory)
    entry = Path(directory) / manifest.get("package", {}).get("entry", "main.mgo")
    last_signature = None
    print("Memingo dev mode. Press Ctrl+C to stop.")
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
    print(f"Built {archive}")
    return 0


def run_tests(directory=".", pattern="test*.py") -> int:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(directory), "-p", pattern],
        cwd=directory,
        check=False,
    )
    return result.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="memingo", description="Memingo programming language")
    parser.add_argument("--version", action="version", version=f"Memingo {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("repl", help="Open the interactive REPL")

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
    update_parser.add_argument("directory", nargs="?", default=".")

    args = parser.parse_args(argv)

    if args.command is None:
        return repl()
    if args.command == "repl":
        return repl()
    if args.command == "init":
        manifest = init_project(args.directory, args.name)
        print(f"Created Memingo project: {manifest}")
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
        add_dependency(args.project, args.spec)
        print(f"Added dependency: {args.spec}")
        return 0
    if args.command == "remove":
        remove_dependency(args.project, args.name)
        print(f"Removed dependency: {args.name}")
        return 0
    if args.command == "install":
        dependencies = install_dependencies(args.directory)
        print(f"Installed {len(dependencies)} dependencies")
        return 0
    if args.command == "update":
        dependencies = install_dependencies(args.directory)
        print(f"Updated {len(dependencies)} dependencies")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
