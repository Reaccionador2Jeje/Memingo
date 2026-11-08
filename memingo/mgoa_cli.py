import argparse
import sys

from . import __version__
from .cli import banner, heading, success, info, table, error
from .mgoa import (
    PackageError, add_package, install_project, publish_package,
    remove_package, search_registry,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="mgoa",
        description="Package manager for Memingo",
    )
    parser.add_argument("--version", action="version", version=f"mgoa {__version__}")
    parser.add_argument("--registry", help="Package registry URL (defaults to the official registry)")
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser("search", help="Search packages in a registry")
    search_parser.add_argument("query", nargs="?", default="")
    search_parser.add_argument("--registry", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    add_parser = subparsers.add_parser("add", help="Install a package into a project")
    add_parser.add_argument(
        "spec",
        help="name, name@version, HTTP(S) archive URL, local directory, or package archive",
    )
    add_parser.add_argument("--project", default=".")
    add_parser.add_argument("--registry", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    install_parser = subparsers.add_parser("install", help="Install project dependencies")
    install_parser.add_argument("directory", nargs="?", default=".")
    install_parser.add_argument("--registry", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    update_parser = subparsers.add_parser("update", help="Update project dependencies")
    update_parser.add_argument("directory", nargs="?", default=".")
    update_parser.add_argument("--registry", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    remove_parser = subparsers.add_parser("remove", help="Remove an installed package")
    remove_parser.add_argument("name")
    remove_parser.add_argument("--project", default=".")

    publish_parser = subparsers.add_parser("publish", help="Build a package archive for submission")
    publish_parser.add_argument("directory", nargs="?", default=".")
    publish_parser.add_argument("--output", default="dist")

    args = parser.parse_args(argv)

    try:
        if args.command == "search":
            matches = search_registry(args.query, args.registry)
            if not matches:
                info("No packages found")
                return 0
            table(
                ["package", "latest", "source", "description"],
                [
                    [
                        package["name"],
                        package["latest"],
                        package["source"],
                        package["description"],
                    ]
                    for package in matches
                ],
            )
            return 0
        if args.command == "add":
            installed = add_package(args.project, args.spec, args.registry)
            heading("Package installed")
            success(f"{installed['name']}@{installed['version']}")
            return 0
        if args.command == "install":
            installed = install_project(args.directory, args.registry)
            heading("Dependencies installed", str(len(installed)))
            success(f"{len(installed)} package(s) ready")
            return 0
        if args.command == "update":
            installed = install_project(args.directory, args.registry, frozen=False)
            heading("Dependencies updated", str(len(installed)))
            success(f"{len(installed)} package(s) ready")
            return 0
        if args.command == "remove":
            remove_package(args.project, args.name)
            success(f"Removed package {args.name}")
            return 0
        if args.command == "publish":
            archive = publish_package(args.directory, args.output)
            heading("Package archive")
            success(str(archive))
            return 0
        banner(__version__, "MEMINGO PACKAGE MANAGER")
        parser.print_help()
        return 2
    except (PackageError, FileNotFoundError, ValueError) as exception:
        error(f"mgoa: {exception}")
        return 1
    except KeyboardInterrupt:
        print("\nmgoa interrupted.", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0
    except Exception as exception:
        error(f"mgoa: unexpected error: {exception}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
