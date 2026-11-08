import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

from .config import DEFAULT_LOCKFILE, DEFAULT_MANIFEST, DEFAULT_REGISTRY


LOCKFILE = DEFAULT_LOCKFILE
MANIFEST = DEFAULT_MANIFEST

_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_IGNORED_PARTS = {".git", ".memingo", "__pycache__", "node_modules", ".venv", "dist", ".env"}


class PackageError(Exception):
    pass


@dataclass
class ResolvedPackage:
    path: Path
    archive_sha256: str = ""
    release: dict = None
    local: bool = False
    source: dict = None
    approved: bool = False


def _validate_package_name(name, kind="package name"):
    if not isinstance(name, str) or not _NAME_PATTERN.match(name):
        raise PackageError(
            f"Invalid {kind} '{name}'. Use letters, digits, dots, dashes or underscores."
        )
    return name


def _validate_version(version):
    if not isinstance(version, str) or not _VERSION_PATTERN.match(version):
        raise PackageError(
            f"Invalid package version '{version}'. Use a version such as 1.2.3 or 1.2.3-beta.1."
        )
    return version


def cache_root():
    base = os.environ.get("MGOA_CACHE")
    if base:
        return Path(base)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "mgoa/cache"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mgoa"


def read_manifest(directory):
    from .packages import read_manifest as read_simple_manifest
    return read_simple_manifest(directory)


def _load_toml(path):
    path = Path(path)
    try:
        import tomllib
    except ImportError:
        from .packages import _read_simple_toml
        try:
            return _read_simple_toml(path)
        except Exception as error:
            raise PackageError(f"Could not read manifest {path}: {error}")

    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except Exception as error:
        raise PackageError(f"Could not read manifest {path}: {error}")


def _read_lock(path):
    if not path.exists():
        return {"dependencies": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"dependencies": {}}
    if not isinstance(data, dict):
        return {"dependencies": {}}
    data.setdefault("dependencies", {})
    if not isinstance(data["dependencies"], dict):
        data["dependencies"] = {}
    return data


def _write_lock(path, lock):
    path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _looks_like_path(spec):
    return spec.startswith(("./", "../", "/", "~")) or spec in (".", "..") or Path(spec).exists()


def _is_url(spec):
    return bool(_URL_PATTERN.match(spec))


def _split_url_checksum(url):
    """Return the archive URL and an optional sha256 checksum from its fragment."""
    if "#" not in url:
        return url, None
    base, fragment = url.split("#", 1)
    if fragment.lower().startswith("sha256="):
        return base, fragment[len("sha256="):]
    return url, None


def parse_spec(spec):
    spec = spec.strip()
    if not spec:
        raise PackageError("Package name cannot be empty")
    if _is_url(spec):
        return spec, "*"
    if _looks_like_path(spec):
        return spec, "*"
    if "@" in spec:
        name, version = spec.rsplit("@", 1)
    else:
        name, version = spec, "*"
    version = version or "*"
    _validate_package_name(name)
    if version != "*":
        _validate_version(version)
    return name, version


def _download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "mgoa/0.2"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except Exception as error:
        raise PackageError(f"Could not download package archive {url}: {error}")
    destination.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _safe_extract(zip_path, destination):
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(destination).resolve()
    try:
        archive = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as error:
        raise PackageError(f"Invalid package archive {zip_path}: {error}") from error
    with archive:
        for member in archive.infolist():
            raw_name = member.filename.replace("\\", "/")
            member_path = Path(raw_name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise PackageError(f"Unsafe package path: {member.filename}")
            target = (root / raw_name).resolve()
            if root != target and root not in target.parents:
                raise PackageError(f"Unsafe package path: {member.filename}")
            mode = (member.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise PackageError(f"Package archive contains a symbolic link: {member.filename}")
        archive.extractall(root)


def _find_package_root(directory, package_name=None):
    directory = Path(directory)
    if not directory.exists():
        raise PackageError("Package source does not exist")

    candidates = [directory]
    candidates.extend(sorted(path.parent for path in directory.rglob("memingo.toml")))
    candidates.extend(sorted(path.parent for path in directory.rglob("package.toml")))

    seen = set()
    for candidate in candidates:
        if candidate.is_file():
            candidate = candidate.parent
        if candidate in seen:
            continue
        seen.add(candidate)
        manifest = candidate / MANIFEST
        if not manifest.exists():
            manifest = candidate / "package.toml"
        if not manifest.exists():
            continue
        if package_name is None:
            return candidate
        metadata = _load_toml(manifest)
        package_info = metadata.get("package")
        if isinstance(package_info, dict) and package_info.get("name") == package_name:
            return candidate
    raise PackageError("Package archive does not contain memingo.toml or package.toml")


def _registry_url(registry_url=None):
    return registry_url or os.environ.get("MGOA_REGISTRY") or DEFAULT_REGISTRY


def _load_registry(registry_url=None):
    url = _registry_url(registry_url)
    request = urllib.request.Request(url, headers={"User-Agent": "mgoa/0.2"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise PackageError(f"Could not access package registry {url}: {error}")
    if not isinstance(data, dict):
        raise PackageError(f"Package registry returned an invalid document: {url}")
    return data


def _registry_packages(registry):
    """Return the package table and whether the registry is the curated one."""
    approved = registry.get("approved")
    if isinstance(approved, dict) and isinstance(approved.get("packages"), dict):
        return approved["packages"], True
    packages = registry.get("packages")
    if isinstance(packages, dict):
        return packages, False
    raise PackageError("Registry must contain an 'approved.packages' or 'packages' table")


def _verify_archive_digest(expected, actual, label):
    if not expected:
        return
    normalized = str(expected).strip().lower()
    if normalized.startswith("sha256:"):
        normalized = normalized[len("sha256:"):]
    if normalized != actual:
        raise PackageError(
            f"Checksum mismatch for {label}: expected {normalized}, got {actual}"
        )


def _resolve_archive_url(url):
    archive_url, expected = _split_url_checksum(url)
    temporary = Path(tempfile.mkdtemp(prefix="mgoa-"))
    archive = temporary / "package.zip"
    digest = _download(archive_url, archive)
    _verify_archive_digest(expected, digest, archive_url)
    _safe_extract(archive, temporary / "extracted")
    return ResolvedPackage(
        path=_find_package_root(temporary / "extracted"),
        archive_sha256=digest,
        release={"archive": archive_url},
        source={"source": "url", "url": url},
        approved=False,
    )


def resolve_package(spec, registry_url=None):
    local = Path(spec).expanduser()
    if local.exists():
        if local.is_file() and local.suffix.lower() == ".zip":
            temporary = Path(tempfile.mkdtemp(prefix="mgoa-"))
            digest = hashlib.sha256(local.read_bytes()).hexdigest()
            _safe_extract(local, temporary / "extracted")
            return ResolvedPackage(
                path=_find_package_root(temporary / "extracted"),
                archive_sha256=digest,
                release={},
                local=True,
                source={"source": "local", "path": str(local.resolve())},
            )
        return ResolvedPackage(
            path=_find_package_root(local),
            local=True,
            source={"source": "local", "path": str(local.resolve())},
        )

    package_name, requested = parse_spec(spec)
    if _is_url(package_name):
        return _resolve_archive_url(package_name)

    registry_url = _registry_url(registry_url)
    registry = _load_registry(registry_url)
    packages, approved_registry = _registry_packages(registry)
    if package_name not in packages:
        raise PackageError(f"Package '{package_name}' is not available in {registry_url}")
    package_record = packages[package_name]
    if not isinstance(package_record, dict):
        raise PackageError(f"Package '{package_name}' has an invalid registry record")

    versions = package_record.get("versions", {})
    if not isinstance(versions, dict):
        raise PackageError(f"Package '{package_name}' has no valid versions")
    if requested == "*":
        requested = package_record.get("latest")
    if not requested:
        raise PackageError(f"Package '{package_name}' has no latest version")
    _validate_version(requested)
    if requested not in versions:
        raise PackageError(f"Version '{requested}' is not available for package '{package_name}'")

    release = versions[requested]
    if not isinstance(release, dict):
        raise PackageError(f"Package '{package_name}@{requested}' has an invalid release record")
    archive_url = release.get("archive")
    if not archive_url:
        raise PackageError(f"Package '{package_name}@{requested}' has no archive URL")
    archive_url = urljoin(registry_url, str(archive_url))

    temporary = Path(tempfile.mkdtemp(prefix="mgoa-"))
    archive = temporary / "package.zip"
    digest = _download(archive_url, archive)
    _verify_archive_digest(
        release.get("sha256") or release.get("integrity"),
        digest,
        f"{package_name}@{requested}",
    )
    _safe_extract(archive, temporary / "extracted")
    approval = release.get("approved", package_record.get("approved", approved_registry))
    return ResolvedPackage(
        path=_find_package_root(temporary / "extracted", package_name=package_name),
        archive_sha256=digest,
        release=release,
        source={"source": "registry", "registry": registry_url},
        approved=approval is True,
    )


def _package_digest(source):
    digest = hashlib.sha256()
    for path in sorted(Path(source).rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if set(relative.parts) & _IGNORED_PARTS:
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _copy_package(source, destination):
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(*_IGNORED_PARTS))


def install_package(project_directory=".", spec="", registry_url=None, expected_sha256=None):
    project = Path(project_directory).resolve()
    resolved = resolve_package(spec, registry_url)
    source = resolved.path

    manifest_path = source / MANIFEST
    if not manifest_path.exists():
        manifest_path = source / "package.toml"
    if not manifest_path.exists():
        raise PackageError("Package is missing memingo.toml or package.toml")

    metadata = _load_toml(manifest_path)
    package = metadata.get("package")
    if not isinstance(package, dict):
        raise PackageError(f"Manifest is missing a [package] section: {manifest_path}")
    name = _validate_package_name(package.get("name"))
    version = _validate_version(package.get("version"))
    entry = package.get("entry", "main.mgo")
    if not isinstance(entry, str) or not entry:
        raise PackageError("Package manifest requires a non-empty entry file")

    source_root = source.resolve()
    entry_path = (source / entry).resolve()
    if entry_path != source_root and source_root not in entry_path.parents:
        raise PackageError(f"Package entry escapes the package directory: {entry}")
    if not entry_path.exists():
        raise PackageError(f"Package entry file does not exist: {entry}")

    digest = _package_digest(source)
    if expected_sha256 and expected_sha256 != digest:
        raise PackageError(
            f"Lockfile checksum mismatch for {name}@{version}. "
            "Run 'mgoa update' if you intentionally changed the package."
        )

    cache = cache_root() / name / version
    if cache.exists():
        shutil.rmtree(cache)
    cache.parent.mkdir(parents=True, exist_ok=True)
    _copy_package(source, cache)

    destination = project / ".memingo" / "packages" / name
    same_location = source.resolve() == destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    _copy_package(cache if same_location else source, destination)

    lock_path = project / LOCKFILE
    lock = _read_lock(lock_path)
    record = {
        "version": version,
        "entry": entry,
        "sha256": digest,
        "archive_sha256": resolved.archive_sha256,
        "approved": bool(resolved.approved),
    }
    if resolved.source:
        record.update(resolved.source)
    lock["dependencies"][name] = record
    _write_lock(lock_path, lock)

    return {
        "name": name,
        "version": version,
        "entry": entry,
        "sha256": digest,
        "archive_sha256": resolved.archive_sha256,
        "source": resolved.source or {},
        "approved": bool(resolved.approved),
    }


def add_package(project_directory=".", spec="", registry_url=None):
    installed = install_package(project_directory, spec, registry_url)
    project = Path(project_directory)
    from .packages import _write_simple_toml
    manifest = read_manifest(project)
    dependencies = manifest.setdefault("dependencies", {})
    dependencies[installed["name"]] = installed["version"]
    _write_simple_toml(project / MANIFEST, manifest)
    return installed


def remove_package(project_directory=".", name=""):
    name = _validate_package_name(name)
    project = Path(project_directory).resolve()
    destination = project / ".memingo" / "packages" / name
    if destination.exists():
        shutil.rmtree(destination)

    lock_path = project / LOCKFILE
    if lock_path.exists():
        lock = _read_lock(lock_path)
        lock["dependencies"].pop(name, None)
        _write_lock(lock_path, lock)

    from .packages import _write_simple_toml
    manifest = read_manifest(project)
    manifest.setdefault("dependencies", {}).pop(name, None)
    _write_simple_toml(project / MANIFEST, manifest)
    return True


def install_project(project_directory=".", registry_url=None, frozen=True):
    project = Path(project_directory).resolve()
    data = read_manifest(project)
    dependencies = data.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise PackageError("[dependencies] must be a table in memingo.toml")
    lock = _read_lock(project / LOCKFILE)
    locked = lock.get("dependencies", {})
    installed = []
    for name, version in dependencies.items():
        _validate_package_name(name)
        if version not in (None, "", "*") and not isinstance(version, str):
            raise PackageError(f"Dependency '{name}' must use a version string")
        record = locked.get(name)
        if not isinstance(record, dict):
            record = {}
        expected = record.get("sha256") if frozen else None
        package_registry = registry_url or record.get("registry")
        if record.get("url"):
            spec = record["url"]
        elif record.get("path"):
            spec = record["path"]
        elif isinstance(version, str) and _is_url(version):
            spec = version
        else:
            spec = name if version in (None, "", "*") else f"{name}@{version}"
        installed.append(
            install_package(project, spec, package_registry, expected_sha256=expected)
        )
    return installed


def search_registry(query="", registry_url=None):
    registry = _load_registry(registry_url)
    packages, approved_registry = _registry_packages(registry)
    query = query.lower()
    matches = []
    for name, record in packages.items():
        if not isinstance(record, dict):
            continue
        name = str(name)
        description = record.get("description") or ""
        text = f"{name} {description}".lower()
        if query and query not in text:
            continue
        approval = record.get("approved", approved_registry)
        matches.append({
            "name": name,
            "latest": record.get("latest"),
            "description": description,
            "approved": approval is True,
            "source": "approved" if approval is True else "community",
        })
    return matches


def publish_package(directory=".", output="dist"):
    root = Path(directory).resolve()
    manifest_path = root / MANIFEST
    if not manifest_path.exists():
        manifest_path = root / "package.toml"
    if not manifest_path.exists():
        raise PackageError("Missing memingo.toml or package.toml")

    package = _load_toml(manifest_path).get("package")
    if not isinstance(package, dict):
        raise PackageError(f"Manifest is missing a [package] section: {manifest_path}")
    name = _validate_package_name(package.get("name"))
    version = _validate_version(package.get("version"))
    entry = package.get("entry", "main.mgo")
    if not isinstance(entry, str) or not entry:
        raise PackageError("Package manifest requires a non-empty entry file")
    entry_path = (root / entry).resolve()
    if root not in entry_path.parents and entry_path != root:
        raise PackageError(f"Package entry escapes the package directory: {entry}")
    if not entry_path.exists():
        raise PackageError("Package entry file does not exist")

    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{name}-{version}.zip"
    checksum = archive.with_suffix(archive.suffix + ".sha256")
    ignored = set(_IGNORED_PARTS)
    ignored.add(output_dir.name)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source in sorted(root.rglob("*")):
            if not source.is_file() or source.is_symlink():
                continue
            relative = source.relative_to(root)
            if set(relative.parts) & ignored:
                continue
            if source.resolve() in (archive.resolve(), checksum.resolve()):
                continue
            bundle.write(source, relative.as_posix())

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive
