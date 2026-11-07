from pathlib import Path
import json


LOCKFILE = "memingo.lock.json"
MANIFEST = "memingo.toml"


def init_project(directory=".", name="my-memingo-app"):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / MANIFEST
    if not manifest.exists():
        manifest.write_text(
            f'[package]\nname = "{name}"\nversion = "0.2.0"\nentry = "main.mgo"\n\n[dependencies]\n',
            encoding="utf-8",
        )

    main_file = root / "main.mgo"
    if not main_file.exists():
        main_file.write_text(
            'vibe app = "Memingo"\nspill "Welcome to " + app + "!"\n',
            encoding="utf-8",
        )
    return manifest


def read_manifest(directory="."):
    return _read_simple_toml(Path(directory) / MANIFEST)


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
    dependencies[name] = version
    _write_simple_toml(manifest_path, data)

    packages_dir = root / ".memingo" / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)
    lock_path = root / LOCKFILE
    lock = _read_lock(lock_path)
    lock["dependencies"] = dependencies
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def remove_dependency(directory=".", name=""):
    root = Path(directory)
    data = read_manifest(root)
    dependencies = data.setdefault("dependencies", {})
    if name not in dependencies:
        raise ValueError(f"Dependency '{name}' is not installed")
    dependencies.pop(name)
    _write_simple_toml(root / MANIFEST, data)

    lock_path = root / LOCKFILE
    lock = _read_lock(lock_path)
    lock["dependencies"] = dependencies
    lock_path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install_dependencies(directory="."):
    root = Path(directory)
    data = read_manifest(root)
    dependencies = data.get("dependencies", {})
    packages_dir = root / ".memingo" / "packages"
    packages_dir.mkdir(parents=True, exist_ok=True)

    lock = {"dependencies": dependencies}
    for name, version in dependencies.items():
        package_dir = packages_dir / name
        package_dir.mkdir(parents=True, exist_ok=True)
        (package_dir / "PACKAGE.json").write_text(
            json.dumps({"name": name, "version": version}, indent=2),
            encoding="utf-8",
        )
    (root / LOCKFILE).write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dependencies


def _read_lock(path):
    if not path.exists():
        return {"dependencies": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"dependencies": {}}


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
            raw_value = raw_value.strip().strip('"')
            target = result.setdefault(section, {}) if section else result
            target[key] = raw_value
    return result


def _write_simple_toml(path, data):
    package = data.get("package", {})
    dependencies = data.get("dependencies", {})
    lines = ["[package]"]
    for key in ("name", "version", "entry"):
        if key in package:
            lines.append(f'{key} = "{package[key]}"')
    lines.extend(["", "[dependencies]"])
    for name, version in dependencies.items():
        lines.append(f'{name} = "{version}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
