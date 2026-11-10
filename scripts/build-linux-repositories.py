#!/usr/bin/env python3
"""Create APT, DNF/RPM and pacman repository metadata for Memingo."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

from linux_packages import DIST, build_pacman_repository


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "site" / "linux"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha512(path: Path) -> str:
    digest = hashlib.sha512()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deb_package_name(package: Path) -> str:
    try:
        return subprocess.check_output(
            ["dpkg-deb", "-f", str(package), "Package"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return package.name.split("_", 1)[0]


def build_apt_repository(output: Path, packages: list[Path]) -> bool:
    if not shutil.which("dpkg-scanpackages"):
        print("APT repository: dpkg-scanpackages is required (install dpkg-dev)", file=sys.stderr)
        return False

    apt_root = output / "apt"
    for package in packages:
        name = deb_package_name(package)
        pool = apt_root / "pool" / "main" / name[0] / name
        pool.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package, pool / package.name)

    distribution = apt_root / "dists" / "stable"
    component = distribution / "main" / "binary-amd64"
    component.mkdir(parents=True, exist_ok=True)

    packages_file = component / "Packages"
    with packages_file.open("w", encoding="utf-8") as stream:
        subprocess.run(
            ["dpkg-scanpackages", "pool/", "/dev/null"],
            cwd=apt_root,
            stdout=stream,
            check=True,
        )
    with packages_file.open("rb") as source, gzip.open(str(packages_file) + ".gz", "wb") as target:
        shutil.copyfileobj(source, target)

    now = subprocess.check_output(["date", "-Ru"], text=True).strip()
    release = distribution / "Release"
    lines = [
        "Origin: Memingo",
        "Label: Memingo",
        "Suite: stable",
        "Codename: stable",
        f"Date: {now}",
        "Architectures: amd64",
        "Components: main",
        "Description: Memingo APT package repository",
        "",
    ]
    hash_lines = []
    for algorithm, function in (("SHA256", sha256), ("SHA512", sha512)):
        hash_lines.append(f"{algorithm}:")
        for relative in sorted(distribution.rglob("*")):
            if not relative.is_file() or relative.name in {"Release", "Release.gpg", "InRelease"}:
                continue
            relative_path = relative.relative_to(distribution).as_posix()
            hash_lines.append(f" {function(relative)} {relative.stat().st_size} {relative_path}")
    lines.extend(hash_lines)
    release.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def build_rpm_repository(output: Path, packages: list[Path]) -> bool:
    if not shutil.which("createrepo_c"):
        print("RPM repository: createrepo_c is required (install createrepo-c)", file=sys.stderr)
        return False

    rpm_root = output / "rpm"
    rpm_packages = rpm_root / "Packages"
    rpm_packages.mkdir(parents=True, exist_ok=True)
    for package in packages:
        shutil.copy2(package, rpm_packages / package.name)
    subprocess.run(["createrepo_c", "--update", "--database", str(rpm_root)], check=True)
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--only", choices=("apt", "rpm", "arch"), action="append")
    args = parser.parse_args(argv)

    output = Path(args.output).resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    deb_packages = sorted(DIST.glob("*.deb"))
    rpm_packages = sorted(DIST.glob("*.rpm"))
    arch_packages = sorted(DIST.glob("*.pkg.tar.zst"))
    formats = tuple(args.only) if args.only else ("apt", "rpm", "arch")
    built: list[Path] = []

    if "apt" in formats and deb_packages:
        if build_apt_repository(output, deb_packages):
            built.append(output / "apt")
    if "rpm" in formats and rpm_packages:
        if build_rpm_repository(output, rpm_packages):
            built.append(output / "rpm")
    if "arch" in formats and arch_packages:
        if build_pacman_repository(output, arch_packages):
            built.append(output / "arch")

    if not built:
        print(
            "No repository was built. Build packages first with scripts/build-packages.py",
            file=sys.stderr,
        )
        return 1
    for repository in built:
        print(repository)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
