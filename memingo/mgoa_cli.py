import argparse
import sys

from . import __version__
from .cli import (
    banner, heading, key_value, success, info, table, error, panel, status_bar,
    tip, command_header, CYAN, GREEN, YELLOW,
)
from .completion import mgoa_completion
from .mgoa import (
    PackageError, add_package, install_project, list_installed, package_info,
    publish_package, remove_package, search_registry,
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

    info_parser = subparsers.add_parser("info", help="Show package metadata from a registry")
    info_parser.add_argument("package")
    info_parser.add_argument("--registry", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    list_parser = subparsers.add_parser("list", help="List installed project packages")
    list_parser.add_argument("--project", default=".")

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

    completion_parser = subparsers.add_parser("completion", help="Print shell completion scripts")
    completion_parser.add_argument("shell", choices=("bash", "zsh", "fish"))

    args = parser.parse_args(argv)

    try:
        if args.command not in {None, "completion"}:
            command_header("mgoa", args.command)
        if args.command is None:
            banner(__version__, "MEMINGO PACKAGE MANAGER")
            status_bar([
                ("Registry", "mgoa", CYAN),
                ("Packages", "ready", GREEN),
                ("Version", __version__, YELLOW),
            ])
            panel("Package console", [
                "mgoa search <text>      Find packages",
                "mgoa add <package>      Install into a project",
                "mgoa list               Inspect installed dependencies",
                "mgoa publish <dir>      Build a package archive",
            ])
            tip("Use mgoa --help for the complete command catalog.")
            return 0
        if args.command == "completion":
            print(mgoa_completion(args.shell), end="")
            return 0
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
        if args.command == "info":
            details = package_info(args.package, args.registry)
            heading(f"Package {details['name']}", details["registry"])
            key_value([
                ("Latest", details["latest"] or "unknown"),
                ("Source", details["source"]),
                ("Approved", "yes" if details["approved"] else "no"),
                ("Description", details["description"] or "-"),
            ])
            if details["versions"]:
                table(
                    ["version", "sha256", "archive"],
                    [
                        [release["version"], release["sha256"] or "-", release["archive"] or "-"]
                        for release in details["versions"]
                    ],
                )
            return 0
        if args.command == "list":
            packages = list_installed(args.project)
            if not packages:
                info("No installed packages")
                return 0
            heading("Installed packages", args.project)
            table(
                ["package", "requested", "locked", "source", "approved", "installed"],
                [
                    [
                        package["name"],
                        str(package["requested"]),
                        str(package["version"]),
                        package["source"],
                        "yes" if package["approved"] else "no",
                        "yes" if package["installed"] else "no",
                    ]
                    for package in packages
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
