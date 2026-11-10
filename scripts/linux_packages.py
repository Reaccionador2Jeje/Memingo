#!/usr/bin/env python3
"""Shared helpers for building Memingo Linux packages.

The same component definitions are used for Debian (apt), RPM (dnf) and
Arch Linux (pacman) packages so every channel ships the same set of
Memingo services.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SITE = ROOT / "site"
PACKAGES = ROOT / "packages"
REGISTRY = SITE / "mgoa"
VSCODE = ROOT / "vscode-extension"

MAINTAINER = "Memingo <noreply@example.com>"
HOMEPAGE = "https://github.com/Reaccionador2Jeje/Memingo"
LICENSE = "BSD-3-Clause"
REPOSITORY_URL = "https://reaccionador2jeje.github.io/Memingo"


@dataclass
class Component:
    name: str
    version: str
    summary: str
    description: str
    stage: Callable[[Path], None]
    arch: str = "all"
    depends: tuple[str, ...] = ()
    recommends: tuple[str, ...] = ()
    suggests: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    replaces: tuple[str, ...] = ()
    optdepends: tuple[str, ...] = ()
    license: str = LICENSE
    url: str = HOMEPAGE
    extra: dict = field(default_factory=dict)


def read_version() -> str:
    version_file = ROOT / "memingo" / "__init__.py"
    match = re.search(r'__version__\s*=\s*"([^"]+)"', version_file.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError("Could not read the Memingo version")
    return match.group(1)


def read_manifest(path: Path) -> dict:
    try:
        import tomllib
    except ImportError:  # Python 3.10
        import sys

        sys.path.insert(0, str(ROOT))
        from memingo.packages import _read_simple_toml

        return _read_simple_toml(path)
    with path.open("rb") as stream:
        return tomllib.load(stream)


def registry_packages() -> list[dict]:
    directories = []
    for directory in sorted(PACKAGES.iterdir()) if PACKAGES.is_dir() else []:
        manifest = directory / "package.toml"
        if not manifest.exists():
            manifest = directory / "memingo.toml"
        if directory.is_dir() and manifest.exists():
            data = read_manifest(manifest).get("package", {})
            directories.append(
                {
                    "name": str(data.get("name", directory.name)).strip(),
                    "version": str(data.get("version", "")).strip(),
                    "description": str(data.get("description", "")).strip(),
                    "license": str(data.get("license", LICENSE)).strip(),
                    "homepage": str(data.get("homepage", HOMEPAGE)).strip(),
                }
            )
    return directories


def _write_wrapper(path: Path, launcher: str) -> None:
    path.write_text(
        "#!/usr/bin/sh\n"
        f'exec /usr/bin/python3 -I /usr/lib/memingo/{launcher} "$@"\n',
        encoding="utf-8",
    )
    path.chmod(0o755)


def stage_runtime(staging: Path) -> None:
    runtime = staging / "usr" / "lib" / "memingo"
    runtime.mkdir(parents=True)
    shutil.copytree(
        ROOT / "memingo",
        runtime / "memingo",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(ROOT / "scripts" / "launcher.py", runtime / "launcher.py")
    shutil.copy2(ROOT / "scripts" / "mgoa.py", runtime / "mgoa.py")

    bin_dir = staging / "usr" / "bin"
    bin_dir.mkdir(parents=True)
    _write_wrapper(bin_dir / "memingo", "launcher.py")
    _write_wrapper(bin_dir / "mgoa", "mgoa.py")

    doc_dir = staging / "usr" / "share" / "doc" / "memingo"
    doc_dir.mkdir(parents=True)
    for name in ("README.md", "LANGUAGE.md", "LICENSE"):
        source = ROOT / name
        if source.exists():
            shutil.copy2(source, doc_dir / name)


def _offline_registry_index(source_index: Path, packages_dir: Path) -> dict:
    index = json.loads(source_index.read_text(encoding="utf-8"))
    table = index.get("approved", {}).get("packages", {})
    for record in table.values():
        for release in record.get("versions", {}).values():
            archive = str(release.get("archive", ""))
            name = posixpath.basename(urlparse(archive).path)
            release["archive"] = f"file://{packages_dir}/{name}"
    return index


def stage_registry(staging: Path) -> None:
    source_index = REGISTRY / "index.json"
    source_packages = REGISTRY / "packages"
    if not source_index.exists() or not source_packages.is_dir():
        raise RuntimeError(
            "Missing site/mgoa registry. Run `python3 scripts/build-registry.py` first."
        )

    destination = staging / "usr" / "share" / "memingo" / "registry"
    package_dir = destination / "packages"
    package_dir.mkdir(parents=True)

    archives = sorted(source_packages.glob("*.zip"))
    if not archives:
        raise RuntimeError("The registry does not contain package archives")
    for archive in archives:
        shutil.copy2(archive, package_dir / archive.name)

    index = _offline_registry_index(source_index, package_dir)
    (destination / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    (destination / "README.md").write_text(
        "# Memingo offline registry\n\n"
        "This directory contains the official Memingo package registry and every\n"
        "published package archive. Point mgoa at the local index to install\n"
        "packages without network access:\n\n"
        "```bash\n"
        "mgoa install --registry file:///usr/share/memingo/registry/index.json <package>\n"
        "```\n",
        encoding="utf-8",
    )

    wrapper = staging / "usr" / "bin" / "memingo-registry"
    wrapper.parent.mkdir(parents=True, exist_ok=True)
    wrapper.write_text(
        "#!/usr/bin/sh\n"
        'echo "Memingo offline registry: file:///usr/share/memingo/registry/index.json"\n'
        'echo "Usage: mgoa install --registry file:///usr/share/memingo/registry/index.json <package>"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)


def find_vsix() -> Path | None:
    candidates = sorted(VSCODE.glob("*.vsix"))
    return candidates[-1] if candidates else None


def stage_vscode(staging: Path) -> None:
    vsix = find_vsix()
    if vsix is None:
        raise RuntimeError(
            "No VSIX found. Build it with `npx --yes @vscode/vsce package` in vscode-extension/."
        )

    destination = staging / "usr" / "share" / "memingo" / "vscode"
    destination.mkdir(parents=True)
    shutil.copy2(vsix, destination / "memingo.vsix")

    (destination / "README.md").write_text(
        "# Memingo for Visual Studio Code\n\n"
        "Install the bundled extension with:\n\n"
        "```bash\n"
        "memingo-vscode-install\n"
        "# or\n"
        "code --install-extension /usr/share/memingo/vscode/memingo.vsix\n"
        "```\n",
        encoding="utf-8",
    )

    helper = staging / "usr" / "bin" / "memingo-vscode-install"
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        "#!/usr/bin/sh\n"
        "set -eu\n"
        "VSIX=/usr/share/memingo/vscode/memingo.vsix\n"
        'for editor in code code-insiders codium; do\n'
        '  if command -v "$editor" >/dev/null 2>&1; then\n'
        '    exec "$editor" --install-extension "$VSIX" --force\n'
        "  fi\n"
        "done\n"
        'echo "No se encontró VS Code, Code - Insiders ni VSCodium." >&2\n'
        'echo "Instala la extensión manualmente con: code --install-extension $VSIX" >&2\n'
        "exit 1\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)


def stage_full(staging: Path) -> None:
    # Meta package: no payload.
    staging.mkdir(parents=True, exist_ok=True)


def _has_artifact(extension: str) -> bool:
    return any(
        "memingo-ide" in path.name.lower()
        for path in DIST.glob(f"*{extension}")
    )


def build_components(version: str, artifact_extension: str = ".deb") -> list[Component]:
    components = [
        Component(
            name="memingo",
            version=version,
            summary="Meme-inspired programming language and package manager",
            description=(
                "Memingo includes the memingo interpreter, the mgoa package manager "
                "and the language documentation."
            ),
            stage=stage_runtime,
            depends=("python3 >= 3.10",),
            provides=("memingo-lang",),
        ),
        Component(
            name="memingo-registry",
            version=version,
            summary="Official Memingo package registry for offline mgoa installs",
            description=(
                "Installs the official Memingo registry index and all published package "
                "archives under /usr/share/memingo/registry."
            ),
            stage=stage_registry,
            depends=("memingo",),
        ),
    ]

    if find_vsix() is not None:
        components.append(
            Component(
                name="memingo-vscode",
                version=version,
                summary="Memingo language support for Visual Studio Code",
                description=(
                    "Installs the Memingo VSIX and the memingo-vscode-install helper, "
                    "which registers the extension with VS Code, VSCodium or Code - Insiders."
                ),
                stage=stage_vscode,
                recommends=("code",),
                optdepends=("code: install the extension into Visual Studio Code",),
            )
        )

    dependencies = [component.name for component in components]
    if _has_artifact(artifact_extension):
        dependencies.append("memingo-ide")

    components.append(
        Component(
            name="memingo-full",
            version=version,
            summary="Complete Memingo development environment",
            description=(
                "Meta package that installs the Memingo runtime, the official registry, "
                "the VS Code extension and, when available, the Memingo IDE."
            ),
            stage=stage_full,
            depends=tuple(dependencies),
        )
    )
    return components


def iter_payload(staging: Path) -> Iterable[Path]:
    for path in sorted(staging.rglob("*")):
        relative = path.relative_to(staging)
        if relative.parts and relative.parts[0] == "DEBIAN":
            continue
        if path.name in {".PKGINFO", ".MTREE", ".BUILDINFO", ".INSTALL"}:
            continue
        yield path


def installed_size(staging: Path) -> int:
    return sum(path.stat().st_size for path in iter_payload(staging) if path.is_file())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Debian
# ---------------------------------------------------------------------------


def _deb_dependency(value: str) -> str:
    value = value.strip()
    if "(" in value:
        return value
    match = re.match(r"^(\S+)\s*(>=|<=|=|>>|<<)\s*(.+)$", value)
    if match:
        return f"{match.group(1)} ({match.group(2)} {match.group(3)})"
    return value


def _deb_control(component: Component) -> str:
    lines = [
        f"Package: {component.name}",
        f"Version: {component.version}",
        "Section: devel",
        "Priority: optional",
        f"Architecture: {component.arch}",
    ]
    if component.depends:
        lines.append("Depends: " + ", ".join(_deb_dependency(dep) for dep in component.depends))
    if component.recommends:
        lines.append("Recommends: " + ", ".join(_deb_dependency(dep) for dep in component.recommends))
    if component.suggests:
        lines.append("Suggests: " + ", ".join(_deb_dependency(dep) for dep in component.suggests))
    if component.provides:
        lines.append("Provides: " + ", ".join(component.provides))
    if component.conflicts:
        lines.append("Conflicts: " + ", ".join(component.conflicts))
    if component.replaces:
        lines.append("Replaces: " + ", ".join(component.replaces))
    lines.extend(
        [
            f"Maintainer: {MAINTAINER}",
            f"Homepage: {component.url}",
            f"Description: {component.summary}",
        ]
    )
    for line in component.description.splitlines():
        lines.append(" " + line if line else " .")
    return "\n".join(lines) + "\n"


def build_deb(component: Component, staging: Path) -> Path | None:
    if not shutil.which("dpkg-deb"):
        print("dpkg-deb is required (install the dpkg package)", file=__import__("sys").stderr)
        return None

    control_dir = staging / "DEBIAN"
    control_dir.mkdir(parents=True, exist_ok=True)
    (control_dir / "control").write_text(_deb_control(component), encoding="utf-8")

    sums = []
    for path in iter_payload(staging):
        if path.is_file():
            relative = path.relative_to(staging).as_posix()
            sums.append(f"{md5_file(path)}  {relative}")
    if sums:
        (control_dir / "md5sums").write_text("\n".join(sums) + "\n", encoding="utf-8")

    output = DIST / f"{component.name}_{component.version}_{component.arch}.deb"
    if output.exists():
        output.unlink()
    subprocess.run(
        ["dpkg-deb", "--build", "--root-owner-group", str(staging), str(output)],
        check=True,
    )
    return output


# ---------------------------------------------------------------------------
# RPM
# ---------------------------------------------------------------------------


def _rpm_file_entries(staging: Path) -> list[str]:
    entries: set[str] = set()
    for path in iter_payload(staging):
        relative = path.relative_to(staging).as_posix()
        parts = relative.split("/")
        if len(parts) < 2:
            continue
        if parts[0] != "usr":
            entries.add("/" + relative)
        elif parts[1] == "bin":
            entries.add("/" + relative)
        elif parts[1] == "lib" and len(parts) >= 3:
            entries.add("/usr/lib/" + parts[2])
        elif parts[1] == "share" and len(parts) >= 4:
            if parts[2] == "doc":
                entries.add("/usr/share/doc/" + parts[3])
            else:
                entries.add("/usr/share/" + parts[2] + "/" + parts[3])
        else:
            entries.add("/" + relative)
    return sorted(entries)


def _rpm_requires(component: Component) -> str:
    lines = [f"Requires: {dependency}" for dependency in component.depends]
    lines.extend(f"Recommends: {dependency}" for dependency in component.recommends)
    lines.extend(f"Suggests: {dependency}" for dependency in component.suggests)
    lines.extend(f"Provides: {value}" for value in component.provides)
    lines.extend(f"Conflicts: {value}" for value in component.conflicts)
    lines.extend(f"Obsoletes: {value}" for value in component.replaces)
    return "\n".join(lines)


def build_rpm(component: Component, staging: Path) -> Path | None:
    if not shutil.which("rpmbuild"):
        print("rpmbuild is required (install rpm-build)", file=__import__("sys").stderr)
        return None

    with tempfile.TemporaryDirectory(prefix=f"memingo-rpm-{component.name}-") as temporary:
        temporary_path = Path(temporary)
        topdir = temporary_path / "rpmbuild"
        for directory in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            (topdir / directory).mkdir(parents=True)

        source_root = temporary_path / f"{component.name}-{component.version}"
        shutil.copytree(staging, source_root / "payload")
        source_archive = topdir / "SOURCES" / f"{component.name}-{component.version}.tar.gz"
        with tarfile.open(source_archive, "w:gz") as archive:
            archive.add(source_root, arcname=source_root.name)

        files = _rpm_file_entries(staging)
        files_section = "\n".join(files) if files else "%defattr(-,root,root,-)"
        spec = topdir / "SPECS" / f"{component.name}.spec"
        spec.write_text(
            f"Name: {component.name}\n"
            f"Version: {component.version}\n"
            "Release: 1%{?dist}\n"
            f"Summary: {component.summary}\n"
            f"License: {component.license}\n"
            f"URL: {component.url}\n"
            "BuildArch: noarch\n"
            "AutoReqProv: no\n"
            f"{_rpm_requires(component)}\n"
            f"Source0: {component.name}-{component.version}.tar.gz\n\n"
            f"%description\n{component.description}\n\n"
            "%prep\n%setup -q\n\n"
            "%build\n\n"
            "%install\n"
            "rm -rf %{buildroot}\n"
            "mkdir -p %{buildroot}\n"
            "cp -a payload/. %{buildroot}/\n\n"
            f"%files\n{files_section}\n",
            encoding="utf-8",
        )

        subprocess.run(
            ["rpmbuild", "-bb", "--define", f"_topdir {topdir}", str(spec)],
            check=True,
        )
        built = list((topdir / "RPMS").rglob("*.rpm"))
        if not built:
            raise RuntimeError(f"rpmbuild completed without producing an RPM for {component.name}")
        output = DIST / built[0].name
        if output.exists():
            output.unlink()
        shutil.copy2(built[0], output)
        return output


# ---------------------------------------------------------------------------
# Arch Linux
# ---------------------------------------------------------------------------


def _arch_dependency(value: str) -> str:
    value = value.strip()
    if value.startswith("python3"):
        rest = value[len("python3") :].strip().strip("()")
        return "python" + re.sub(r"\s+", "", rest)
    return value


def _arch_pkginfo(component: Component, staging: Path) -> str:
    lines = [
        f"pkgname = {component.name}",
        f"pkgbase = {component.name}",
        f"pkgver = {component.version}-1",
        f"pkgdesc = {component.summary}",
        f"url = {component.url}",
        f"builddate = {int(os.environ.get('SOURCE_DATE_EPOCH', time.time()))}",
        f"packager = {MAINTAINER}",
        f"size = {installed_size(staging)}",
        "arch = any",
        f"license = {component.license}",
    ]
    lines.extend(f"depend = {_arch_dependency(dependency)}" for dependency in component.depends)
    lines.extend(f"optdepend = {dependency}" for dependency in component.optdepends)
    lines.extend(f"provides = {value}" for value in component.provides)
    lines.extend(f"conflict = {value}" for value in component.conflicts)
    lines.extend(f"replaces = {value}" for value in component.replaces)
    return "\n".join(lines) + "\n"


def _arch_mtree(staging: Path) -> bytes:
    lines = ["#mtree", "/set type=file uid=0 gid=0 mode=644"]
    for path in sorted(staging.rglob("*")):
        relative = path.relative_to(staging)
        if relative.as_posix() in {".PKGINFO", ".MTREE"}:
            continue
        name = "./" + relative.as_posix()
        stat = path.lstat()
        timestamp = int(stat.st_mtime)
        if path.is_symlink():
            lines.append(f"{name} time={timestamp} type=link link={os.readlink(path)}")
        elif path.is_dir():
            lines.append(f"{name} time={timestamp} type=dir mode=755")
        else:
            lines.append(
                f"{name} time={timestamp} size={stat.st_size} "
                f"mode={stat.st_mode & 0o777:o} md5digest={md5_file(path)} "
                f"sha256digest={sha256_file(path)}"
            )
    return gzip.compress(("\n".join(lines) + "\n").encode("utf-8"), mtime=0)


def build_arch(component: Component, staging: Path) -> Path | None:
    if not shutil.which("zstd"):
        print("zstd is required to build Arch Linux packages", file=__import__("sys").stderr)
        return None

    (staging / ".PKGINFO").write_text(_arch_pkginfo(component, staging), encoding="utf-8")
    (staging / ".MTREE").write_bytes(_arch_mtree(staging))

    output = DIST / f"{component.name}-{component.version}-1-any.pkg.tar.zst"
    if output.exists():
        output.unlink()

    with tempfile.TemporaryDirectory(prefix=f"memingo-arch-{component.name}-") as temporary:
        archive_path = Path(temporary) / "package.tar"
        with tarfile.open(archive_path, "w", format=tarfile.GNU_FORMAT) as archive:
            for name in (".PKGINFO", ".MTREE"):
                archive.add(staging / name, arcname=name, recursive=False)
            for path in iter_payload(staging):
                archive.add(
                    path,
                    arcname=path.relative_to(staging).as_posix(),
                    recursive=False,
                )
        subprocess.run(
            ["zstd", "-q", "-f", str(archive_path), "-o", str(output)],
            check=True,
        )
    return output


# ---------------------------------------------------------------------------
# Arch Linux repository database
# ---------------------------------------------------------------------------


def _parse_pkginfo(text: str) -> dict:
    result: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        if " = " not in raw_line:
            continue
        key, value = raw_line.split(" = ", 1)
        result.setdefault(key.strip(), []).append(value.strip())
    return result


def read_arch_package(package: Path) -> tuple[dict, list[str]]:
    if not shutil.which("zstd"):
        raise RuntimeError("zstd is required to read Arch Linux packages")
    raw = subprocess.check_output(["zstd", "-dc", str(package)])
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        members = archive.getmembers()
        pkginfo_member = next((member for member in members if member.name == ".PKGINFO"), None)
        if pkginfo_member is None:
            raise RuntimeError(f"{package.name} does not contain .PKGINFO")
        pkginfo = archive.extractfile(pkginfo_member).read().decode("utf-8")
        files = [
            member.name
            for member in members
            if member.name not in {".PKGINFO", ".MTREE", ".BUILDINFO", ".INSTALL"}
        ]
    metadata = _parse_pkginfo(pkginfo)
    return metadata, sorted(files)


def _first(metadata: dict, key: str, default: str = "") -> str:
    values = metadata.get(key)
    return values[0] if values else default


def _desc_entry(package: Path, metadata: dict, signature: bytes | None) -> str:
    license_value = "\n".join(metadata.get("license", []))
    lines = [
        "%FILENAME%",
        package.name,
        "",
        "%NAME%",
        _first(metadata, "pkgname"),
        "",
        "%BASE%",
        _first(metadata, "pkgbase", _first(metadata, "pkgname")),
        "",
        "%VERSION%",
        _first(metadata, "pkgver"),
        "",
        "%DESC%",
        _first(metadata, "pkgdesc"),
        "",
        "%CSIZE%",
        str(package.stat().st_size),
        "",
        "%ISIZE%",
        _first(metadata, "size", "0"),
        "",
        "%MD5SUM%",
        md5_file(package),
        "",
        "%SHA256SUM%",
        sha256_file(package),
        "",
    ]
    if signature is not None:
        import base64

        lines.extend(["%PGPSIG%", base64.b64encode(signature).decode("ascii"), ""])
    lines.extend(
        [
            "%URL%",
            _first(metadata, "url"),
            "",
            "%LICENSE%",
            license_value,
            "",
            "%ARCH%",
            _first(metadata, "arch", "any"),
            "",
            "%BUILDDATE%",
            _first(metadata, "builddate"),
            "",
            "%PACKAGER%",
            _first(metadata, "packager"),
            "",
        ]
    )
    for key, label in (
        ("replaces", "%REPLACES%"),
        ("conflict", "%CONFLICTS%"),
        ("provides", "%PROVIDES%"),
        ("depend", "%DEPENDS%"),
        ("optdepend", "%OPTDEPENDS%"),
    ):
        values = metadata.get(key, [])
        if values:
            lines.extend([label, *values, ""])
    return "\n".join(lines)


def build_pacman_repository(output: Path, packages: list[Path]) -> bool:
    if not packages:
        return False
    if not shutil.which("zstd"):
        print("Pacman repository: zstd is required", file=__import__("sys").stderr)
        return False

    repository = output / "arch" / "x86_64"
    repository.mkdir(parents=True, exist_ok=True)

    entries: list[tuple[str, str, str]] = []
    for package in sorted(packages):
        shutil.copy2(package, repository / package.name)
        metadata, files = read_arch_package(package)
        name = _first(metadata, "pkgname")
        version = _first(metadata, "pkgver")
        if not name or not version:
            raise RuntimeError(f"Invalid .PKGINFO in {package.name}")
        signature_path = package.with_name(package.name + ".sig")
        signature = signature_path.read_bytes() if signature_path.exists() else None
        directory = f"{name}-{version}"
        desc = _desc_entry(package, metadata, signature)
        files_content = desc + "\n%FILES%\n" + "\n".join(files) + "\n"
        entries.append((directory, desc, files_content))

    def add_entry(archive: tarfile.TarFile, directory: str, name: str, content: str) -> None:
        info = tarfile.TarInfo(directory)
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.mtime = 0
        archive.addfile(info)
        payload = content.encode("utf-8")
        file_info = tarfile.TarInfo(f"{directory}/{name}")
        file_info.size = len(payload)
        file_info.mode = 0o644
        file_info.mtime = 0
        archive.addfile(file_info, io.BytesIO(payload))

    db_archive = repository / "memingo.db.tar.gz"
    files_archive = repository / "memingo.files.tar.gz"

    with tarfile.open(db_archive, "w:gz", format=tarfile.GNU_FORMAT) as archive:
        for directory, desc, _ in entries:
            add_entry(archive, directory, "desc", desc)

    with tarfile.open(files_archive, "w:gz", format=tarfile.GNU_FORMAT) as archive:
        for directory, desc, files_content in entries:
            add_entry(archive, directory, "desc", desc)
            add_entry(archive, directory, "files", files_content)

    # pacman requests <repo>.db and <repo>.files. Serve real gzip archives
    # (GitHub Pages does not preserve symbolic links).
    shutil.copy2(db_archive, repository / "memingo.db")
    shutil.copy2(files_archive, repository / "memingo.files")
    return True
