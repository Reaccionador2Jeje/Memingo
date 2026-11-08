#!/usr/bin/env python3
"""Build the mgoa registry packages and index.json from packages/."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "packages"
SITE = ROOT / "site" / "mgoa"
ARCHIVES = SITE / "packages"
INDEX = SITE / "index.json"
DEFAULT_BASE_URL = "https://reaccionador2jeje.github.io/Memingo/mgoa/packages"
IGNORED_PARTS = {"__pycache__", "dist", ".git", ".memingo"}


def read_manifest(package_directory):
    for name in ("memingo.toml", "package.toml"):
        path = package_directory / name
        if path.exists():
            sys.path.insert(0, str(ROOT))
            from memingo.packages import _read_simple_toml

            return _read_simple_toml(path)
    raise SystemExit(f"Missing memingo.toml or package.toml in {package_directory}")


def package_record(package_directory, base_url):
    manifest = read_manifest(package_directory)
    package = manifest.get("package")
    if not isinstance(package, dict):
        raise SystemExit(f"Manifest is missing a [package] section in {package_directory}")
    name = str(package.get("name", "")).strip()
    version = str(package.get("version", "")).strip()
    entry = str(package.get("entry", "main.mgo")).strip()
    if not name or not version:
        raise SystemExit(f"Package name and version are required in {package_directory}")
    if not (package_directory / entry).is_file():
        raise SystemExit(f"Package entry '{entry}' does not exist in {package_directory}")

    archive = ARCHIVES / f"{name}-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source in sorted(package_directory.rglob("*")):
            if not source.is_file() or source.is_symlink():
                continue
            relative = source.relative_to(package_directory)
            if set(relative.parts) & IGNORED_PARTS:
                continue
            if source.suffix in (".pyc", ".pyo"):
                continue
            bundle.write(source, relative.as_posix())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    record = {
        "description": str(package.get("description", "")),
        "latest": version,
        "versions": {
            version: {
                "archive": f"{base_url.rstrip('/')}/{archive.name}",
                "sha256": digest,
            }
        },
    }
    for key in ("license", "homepage", "repository"):
        if package.get(key):
            record[key] = str(package[key])
    return name, record, archive


def find_package_directories():
    if not PACKAGES.is_dir():
        raise SystemExit(f"Missing package source directory: {PACKAGES}")
    directories = [
        path for path in sorted(PACKAGES.iterdir())
        if path.is_dir()
        and ((path / "memingo.toml").exists() or (path / "package.toml").exists())
    ]
    if not directories:
        raise SystemExit(f"No packages found in {PACKAGES}")
    return directories


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Public URL for the package archives")
    parser.add_argument("--check", action="store_true", help="Validate packages without writing files")
    args = parser.parse_args(argv)

    directories = find_package_directories()
    if not args.check:
        ARCHIVES.mkdir(parents=True, exist_ok=True)
        for stale in ARCHIVES.glob("*.zip"):
            stale.unlink()

    packages = {}
    built = []
    for directory in directories:
        if args.check:
            manifest = read_manifest(directory)
            package = manifest.get("package", {})
            name = str(package.get("name", "")).strip()
            version = str(package.get("version", "")).strip()
            archive = ARCHIVES / f"{name}-{version}.zip"
            if not archive.exists():
                raise SystemExit(f"Missing archive for {name}@{version}: {archive}")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            index = json.loads(INDEX.read_text(encoding="utf-8"))
            record = index["approved"]["packages"].get(name, {})
            release = record.get("versions", {}).get(version, {})
            if release.get("sha256") != digest:
                raise SystemExit(f"Checksum mismatch for {name}@{version}")
            packages[name] = record
            built.append(archive)
            continue
        name, record, archive = package_record(directory, args.base_url)
        if name in packages:
            raise SystemExit(f"Duplicate package name: {name}")
        packages[name] = record
        built.append(archive)

    if not args.check:
        index = {
            "schema": "memingo-approved/v1",
            "approved": {"packages": packages},
        }
        INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for archive in built:
        print(archive)
    print(f"{len(packages)} package(s) {'validated' if args.check else 'built'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
