import argparse
import sys

from .mgoa import (
    PackageError, add_package, install_project, publish_package,
    remove_package, search_registry,
)


def main(argv=None):
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
                print("No approved packages found.")
                return 0
            for package in matches:
                print(f"{package['name']}@{package['latest']}  {package['description']}")
            return 0
        if args.command == "add":
            installed = add_package(args.project, args.spec, args.registry)
            print(f"Installed approved package: {installed['name']}@{installed['version']}")
            return 0
        if args.command == "install":
            installed = install_project(args.directory, args.registry)
            print(f"Installed {len(installed)} approved package(s)")
            return 0
        if args.command == "remove":
            remove_package(args.project, args.name)
            print(f"Removed package: {args.name}")
            return 0
        if args.command == "publish":
            archive = publish_package(args.directory, args.output)
            print(f"Approved package archive: {archive}")
            return 0
        parser.print_help()
        return 2
    except PackageError as error:
        print(f"mgoa: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"mgoa: unexpected error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
