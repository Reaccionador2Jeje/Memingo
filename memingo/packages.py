from pathlib import Path
import json

from .config import DEFAULT_PROJECT_ENV_TEMPLATE
from .version import __version__


LOCKFILE = "memingo.lock.json"
MANIFEST = "memingo.toml"


def init_project(directory=".", name="my-memingo-app"):
    project_name = str(name).strip()
    if not project_name or any(character in project_name for character in '"\\\n\r'):
        raise ValueError("Project name cannot be empty and must not contain quotes or line breaks")
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / MANIFEST
    if not manifest.exists():
        manifest.write_text(
            f'[package]\nname = "{project_name}"\nversion = "{__version__}"\nentry = "main.mgo"\n\n[dependencies]\n',
            encoding="utf-8",
        )

    main_file = root / "main.mgo"
    if not main_file.exists():
        main_file.write_text(
            'vibe app = "Memingo"\nspill "Welcome to " + app + "!"\n',
            encoding="utf-8",
        )

    env_file = root / ".env"
    if not env_file.exists():
        env_file.write_text(DEFAULT_PROJECT_ENV_TEMPLATE, encoding="utf-8")

    gitignore = root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(".memingo/\ndist/\n__pycache__/\n.env\n", encoding="utf-8")
    return manifest


def read_manifest(directory="."):
    return _read_simple_toml(Path(directory) / MANIFEST)


def resolve_entry(directory="."):
    """Read a project manifest and return its validated entry point."""
    root = Path(directory).resolve()
    data = read_manifest(root)
    package = data.get("package")
    if not isinstance(package, dict):
        raise ValueError(f"Manifest is missing a [package] section: {root / MANIFEST}")
    entry = package.get("entry", "main.mgo")
    if not isinstance(entry, str) or not entry.strip():
        raise ValueError("[package].entry must be a non-empty string")
    entry = entry.strip()
    entry_path = (root / entry).resolve()
    if entry_path != root and root not in entry_path.parents:
        raise ValueError("[package].entry must stay inside the project directory")
    return data, entry, entry_path


def add_dependency(directory=".", spec=""):
    if "=" not in spec:
        spec = spec + "=*"
    name, version = spec.split("=", 1)
    name = name.strip()
    version = version.strip()
    if not name:
        raise ValueError("Dependency name cannot be empty")

    root = Path(directory)
    manifest_path = root / MANIFEST
    data = read_manifest(root)
    dependencies = data.setdefault("dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError("[dependencies] must be a table in memingo.toml")
    dependencies[name] = version
    _write_simple_toml(manifest_path, data)

    lock_path = root / LOCKFILE
    lock = _read_lock(lock_path)
    records = lock.setdefault("dependencies", {})
    for dependency, requested in dependencies.items():
        existing = records.get(dependency)
        if isinstance(existing, dict):
            existing["version"] = requested
        else:
            records[dependency] = {"version": requested}
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def remove_dependency(directory=".", name=""):
    root = Path(directory)
    data = read_manifest(root)
    dependencies = data.setdefault("dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError("[dependencies] must be a table in memingo.toml")
    if name not in dependencies:
        raise ValueError(f"Dependency '{name}' is not installed")
    dependencies.pop(name)
    _write_simple_toml(root / MANIFEST, data)

    lock_path = root / LOCKFILE
    lock = _read_lock(lock_path)
    lock.setdefault("dependencies", {}).pop(name, None)
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install_dependencies(directory="."):
    """Create lightweight dependency records without contacting the registry.

    Projects that use approved packages should call ``mgoa install`` so the
    package contents are downloaded into ``.memingo/packages``.
    """
    root = Path(directory)
    data = read_manifest(root)
    dependencies = data.get("dependencies", {})
    if not isinstance(dependencies, dict):
        raise ValueError("[dependencies] must be a table in memingo.toml")
    packages_dir = root / ".memingo" / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)

    lock = _read_lock(root / LOCKFILE)
    records = lock.setdefault("dependencies", {})
    for name, version in dependencies.items():
        package_dir = packages_dir / name
        package_dir.mkdir(parents=True, exist_ok=True)
        record_path = package_dir / "PACKAGE.json"
        if not record_path.exists():
            record_path.write_text(
                json.dumps({"name": name, "version": version}, indent=2),
                encoding="utf-8",
            )
        existing = records.get(name)
        if isinstance(existing, dict):
            existing.setdefault("version", version)
        else:
            records[name] = {"version": version}
    (root / LOCKFILE).write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dependencies


def _read_lock(path):
    if not path.exists():
        return {"dependencies": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"dependencies": {}}
    if not isinstance(data, dict):
        return {"dependencies": {}}
    data.setdefault("dependencies", {})
    if not isinstance(data["dependencies"], dict):
        data["dependencies"] = {}
    return data


def _parse_simple_value(raw_value):
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_simple_value(item) for item in inner.split(",")]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _read_simple_toml(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing package manifest: {path}")

    try:
        import tomllib
    except ImportError:
        tomllib = None

    if tomllib is not None:
        with path.open("rb") as file:
            return tomllib.load(file)

    result = {}
    section = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            result.setdefault(section, {})
        elif "=" in line:
            key, raw_value = line.split("=", 1)
            key = key.strip()
            target = result.setdefault(section, {}) if section else result
            target[key] = _parse_simple_value(raw_value)
    return result


def _toml_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value), ensure_ascii=False)


def _write_simple_toml(path, data):
    lines = []
    root_values = {key: value for key, value in data.items() if not isinstance(value, dict)}
    for key, value in root_values.items():
        lines.append(f"{key} = {_toml_value(value)}")
    if root_values:
        lines.append("")

    for section, values in data.items():
        if not isinstance(values, dict):
            continue
        lines.append(f"[{section}]")
        for key, value in values.items():
            if not isinstance(value, dict):
                lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
        for key, value in values.items():
            if not isinstance(value, dict):
                continue
            lines.append(f"[{section}.{key}]")
            for nested_key, nested_value in value.items():
                lines.append(f"{nested_key} = {_toml_value(nested_value)}")
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
