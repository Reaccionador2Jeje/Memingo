#!/usr/bin/env python3
"""Build the Memingo services as Debian, RPM and Arch Linux packages."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from linux_packages import (
    DIST,
    REGISTRY,
    ROOT,
    build_arch,
    build_components,
    build_deb,
    build_rpm,
    read_version,
)


FORMATS = ("deb", "rpm", "arch")


def ensure_registry() -> None:
    if (REGISTRY / "index.json").exists() and (REGISTRY / "packages").is_dir():
        return
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build-registry.py")], check=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=FORMATS,
        action="append",
        help="Build only the selected format (repeatable)",
    )
    parser.add_argument(
        "--component",
        action="append",
        help="Build only the selected component (repeatable)",
    )
    parser.add_argument("--list", action="store_true", help="List available components and exit")
    args = parser.parse_args(argv)

    ensure_registry()
    version = read_version()
    formats = tuple(args.only) if args.only else FORMATS

    components = build_components(version)
    if args.list:
        for component in components:
            print(f"{component.name} {component.version}: {component.summary}")
        return 0

    if args.component:
        requested = set(args.component)
        available = {component.name for component in components}
        missing = requested - available
        if missing:
            print(
                "Componentes no disponibles: " + ", ".join(sorted(missing)),
                file=sys.stderr,
            )
            return 1
        components = [component for component in components if component.name in requested]

    DIST.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for component in components:
        for format_name in formats:
            staging = DIST / "staging" / f"{component.name}-{format_name}"
            if staging.exists():
                shutil.rmtree(staging)
            staging.mkdir(parents=True)
            component.stage(staging)

            builder = {"deb": build_deb, "rpm": build_rpm, "arch": build_arch}[format_name]
            output = builder(component, staging)
            if output:
                outputs.append(output)
                print(output)

            shutil.rmtree(staging)

    staging_root = DIST / "staging"
    if staging_root.exists() and not any(staging_root.iterdir()):
        staging_root.rmdir()

    if not outputs:
        print("No packages were built.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
