import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


DEFAULT_REGISTRY = "https://reaccionador2jeje.github.io/Memingo/mgoa/index.json"
LOCKFILE = "memingo.lock.json"
MANIFEST = "memingo.toml"


class PackageError(Exception):
    pass


def cache_root():
    base = os.environ.get("MGOA_CACHE")
    if base:
        return Path(base)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "mgoa/cache"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "mgoa"


def read_manifest(directory):
    from .packages import read_manifest
    return read_manifest(directory)


def parse_spec(spec):
    spec = spec.strip()
    if not spec:
        raise PackageError("Package name cannot be empty")
    if "@" in spec and not spec.startswith(("./", "../", "/")):
        name, version = spec.rsplit("@", 1)
        return name, version or "*"
    return spec, "*"


def _download(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "mgoa/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            destination.write_bytes(response.read())
    except Exception as error:
        raise PackageError(f"Could not download package archive {url}: {error}")


def _safe_extract(zip_path, destination):
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(destination).resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            target = (root / member.filename).resolve()
            if root != target and root not in target.parents:
                raise PackageError(f"Unsafe package path: {member.filename}")
        archive.extractall(root)


def _find_package_root(directory, package_name=None):
    directory = Path(directory)
    if not directory.exists():
        raise PackageError("Package source does not exist")

    candidates = [directory, *directory.rglob("memingo.toml")]
    candidates.extend(directory.rglob("package.toml"))
    for candidate in candidates:
        if candidate.is_file():
            candidate = candidate.parent
        manifest = candidate / "memingo.toml"
        if not manifest.exists():
            manifest = candidate / "package.toml"
        if not manifest.exists():
            continue
        if package_name is None:
            return candidate
        import tomllib
        with manifest.open("rb") as file:
            metadata = tomllib.load(file)
        if metadata.get("package", {}).get("name") == package_name:
            return candidate
    raise PackageError("Package archive does not contain memingo.toml or package.toml")


def _approved_registry(registry_url=None):
    url = registry_url or os.environ.get("MGOA_REGISTRY") or DEFAULT_REGISTRY
    request = urllib.request.Request(url, headers={"User-Agent": "mgoa/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        raise PackageError(f"Could not access approved registry {url}: {error}")


def resolve_package(spec, registry_url=None):
    local = Path(spec)
    if local.exists():
        if local.is_file() and local.suffix.lower() == ".zip":
            temporary = Path(tempfile.mkdtemp(prefix="mgoa-"))
            _safe_extract(local, temporary / "extracted")
            return _find_package_root(temporary / "extracted")
        return _find_package_root(local)

    name, requested = parse_spec(spec)
    registry = _approved_registry(registry_url)
    packages = registry.get("approved", {}).get("packages", {})
    if name not in packages:
        raise PackageError(f"Package '{name}' is not approved by Memingo Approved (mgoa)")

    versions = packages[name].get("versions", {})
    if requested == "*":
        requested = packages[name].get("latest")
    if requested not in versions:
        raise PackageError(f"Version '{requested}' is not approved for package '{name}'")

    release = versions[requested]
    archive_url = release.get("archive")
    if not archive_url:
        raise PackageError(f"Package '{name}@{requested}' has no approved archive")
    temporary = Path(tempfile.mkdtemp(prefix="mgoa-"))
    archive = temporary / "package.zip"
    _download(archive_url, archive)
    _safe_extract(archive, temporary / "extracted")
    return _find_package_root(temporary / "extracted", package_name=name)


def install_package(project_directory=".", spec="", registry_url=None):
    project = Path(project_directory).resolve()
    source = resolve_package(spec, registry_url)
    manifest_path = source / "memingo.toml"
    if not manifest_path.exists():
        manifest_path = source / "package.toml"
    if not manifest_path.exists():
        raise PackageError("Package is missing memingo.toml or package.toml")

    import tomllib
    with manifest_path.open("rb") as file:
        metadata = tomllib.load(file)
    package = metadata.get("package", {})
    name = package.get("name")
    version = package.get("version")
    entry = package.get("entry", "main.mgo")
    if not name or not version:
        raise PackageError("Package manifest requires package.name and package.version")

    entry_path = source / entry
    if not entry_path.exists():
        raise PackageError(f"Package entry file does not exist: {entry}")

    cache = cache_root() / name / version
    if cache.exists():
        shutil.rmtree(cache)
    shutil.copytree(source, cache)

    destination = project / ".memingo" / "packages" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)

    archive_files = [path for path in source.rglob("*") if path.is_file() and path.suffix == ".mgo"]
    digest = hashlib.sha256()
    for path in sorted(archive_files):
        digest.update(path.relative_to(source).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())

    lock_path = project / LOCKFILE
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {"dependencies": {}}
    lock.setdefault("dependencies", {})[name] = {
        "version": version,
        "entry": entry,
        "sha256": digest.hexdigest(),
        "approved": True,
    }
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {"name": name, "version": version, "entry": entry, "sha256": digest.hexdigest()}


def add_package(project_directory=".", spec="", registry_url=None):
    installed = install_package(project_directory, spec, registry_url)
    project = Path(project_directory)
    from .packages import read_manifest, _write_simple_toml
    manifest = read_manifest(project)
    dependencies = manifest.setdefault("dependencies", {})
    dependencies[installed["name"]] = installed["version"]
    _write_simple_toml(project / MANIFEST, manifest)
    return installed


def remove_package(project_directory=".", name=""):
    project = Path(project_directory).resolve()
    destination = project / ".memingo" / "packages" / name
    if destination.exists():
        shutil.rmtree(destination)

    lock_path = project / LOCKFILE
    if lock_path.exists():
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock.setdefault("dependencies", {}).pop(name, None)
        lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from .packages import read_manifest, _write_simple_toml
    manifest = read_manifest(project)
    manifest.setdefault("dependencies", {}).pop(name, None)
    _write_simple_toml(project / MANIFEST, manifest)
    return True


def install_project(project_directory=".", registry_url=None):
    project = Path(project_directory).resolve()
    data = read_manifest(project)
    dependencies = data.get("dependencies", {})
    installed = []
    for name, version in dependencies.items():
        spec = name if version in (None, "", "*") else f"{name}@{version}"
        installed.append(install_package(project, spec, registry_url))
    return installed


def search_registry(query="", registry_url=None):
    registry = _approved_registry(registry_url)
    query = query.lower()
    matches = []
    for name, record in registry.get("approved", {}).get("packages", {}).items():
        text = " ".join([name, record.get("description", "")]).lower()
        if not query or query in text:
            matches.append({"name": name, "latest": record.get("latest"), "description": record.get("description", "")})
    return matches


def publish_package(directory=".", output="dist"):
    root = Path(directory).resolve()
    manifest_path = root / "memingo.toml"
    if not manifest_path.exists():
        raise PackageError("Missing memingo.toml")
    import tomllib
    with manifest_path.open("rb") as file:
        package = tomllib.load(file).get("package", {})
    name = package.get("name")
    version = package.get("version")
    if not name or not version:
        raise PackageError("Package manifest requires package.name and package.version")
    if not (root / package.get("entry", "main.mgo")).exists():
        raise PackageError("Package entry file does not exist")

    output_dir = Path(output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{name}-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source in root.rglob("*"):
            if source.is_file() and ".memingo" not in source.parts:
                bundle.write(source, source.relative_to(root).as_posix())
    return archive
