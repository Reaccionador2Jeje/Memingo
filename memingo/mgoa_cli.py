import argparse
import sys

from . import __version__
from .cli import banner, heading, success, info, warning, table, error
from .mgoa import (
    PackageError, add_package, install_project, publish_package,
    remove_package, search_registry,
)


def main(argv=None):
    banner(__version__, "MEMINGO APPROVED PACKAGES")
    parser = argparse.ArgumentParser(
        prog="mgoa",
        description="Memingo Approved - package manager for Memingo",
    )
    parser.add_argument("--registry", help="Approved package registry URL")
    subparsers = parser.add_subparsers(dest="command")

    search_parser = subparsers.add_parser("search", help="Search approved packages")
    search_parser.add_argument("query", nargs="?", default="")

    add_parser = subparsers.add_parser("add", help="Install an approved package into a project")
    add_parser.add_argument("spec", help="name, name@version, local directory, or package archive")
    add_parser.add_argument("--project", default=".")

    install_parser = subparsers.add_parser("install", help="Install project dependencies")
    install_parser.add_argument("directory", nargs="?", default=".")

    update_parser = subparsers.add_parser("update", help="Update project dependencies")
    update_parser.add_argument("directory", nargs="?", default=".")

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
                info("No approved packages found")
                return 0
            table(
                ["package", "latest", "description"],
                [[package["name"], package["latest"], package["description"]] for package in matches],
            )
            return 0
        if args.command == "add":
            installed = add_package(args.project, args.spec, args.registry)
            heading("Approved package installed")
            success(f"{installed['name']}@{installed['version']}")
            return 0
        if args.command == "install":
            installed = install_project(args.directory, args.registry)
            heading("Dependencies installed", str(len(installed)))
            success(f"{len(installed)} approved package(s) ready")
            return 0
        if args.command == "update":
            installed = install_project(args.directory, args.registry)
            heading("Dependencies updated", str(len(installed)))
            success(f"{len(installed)} approved package(s) ready")
            return 0
        if args.command == "remove":
            remove_package(args.project, args.name)
            success(f"Removed package {args.name}")
            return 0
        if args.command == "publish":
            archive = publish_package(args.directory, args.output)
            heading("Approved package archive")
            success(str(archive))
            return 0
        parser.print_help()
        return 2
    except PackageError as exception:
        error(f"mgoa: {exception}")
        return 1
    except Exception as exception:
        error(f"mgoa: unexpected error: {exception}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
