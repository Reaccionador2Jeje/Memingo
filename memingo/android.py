"""Android project configuration and validation for Memingo.

A0 deliberately manages project metadata only. Code generation and Gradle
invocation belong to later Android backend milestones.
"""

import json
import re
from pathlib import Path

from .packages import ensure_project, read_manifest, resolve_entry


ANDROID_DEFAULTS = {
    "min_sdk": 23,
    "target_sdk": 35,
    "version_code": 1,
}
ANDROID_ALLOWED_KEYS = frozenset({
    "schema_version",
    "application_id",
    "min_sdk",
    "target_sdk",
    "version_code",
    "version_name",
    "ui",
})
APPLICATION_ID_PATTERN = re.compile(
    r"^[a-z][A-Za-z0-9_]*(?:\.[a-z][A-Za-z0-9_]*)+$"
)


class AndroidProjectError(ValueError):
    """Raised when an Android project configuration is invalid."""


def _default_application_id(project_name):
    parts = re.findall(r"[A-Za-z0-9_]+", str(project_name).lower())
    slug = "_".join(parts).strip("_") or "app"
    if not slug[0].isalpha():
        slug = "app_" + slug
    return f"com.example.{slug}"


def _android_config(data):
    config = data.get("android")
    if not isinstance(config, dict):
        raise AndroidProjectError(
            "Missing [android] section. Run 'memingo android init' first."
        )
    return config


def validate_android_project(directory="."):
    """Validate Android metadata and the Memingo project entry point."""
    root = Path(directory).resolve()
    manifest_path = root / "memingo.toml"
    if not root.is_dir():
        raise AndroidProjectError(f"Project directory does not exist: {root}")
    if not manifest_path.is_file():
        raise AndroidProjectError(f"Missing project manifest: {manifest_path}")

    try:
        data = read_manifest(root)
    except (OSError, ValueError) as exception:
        raise AndroidProjectError(f"Cannot read memingo.toml: {exception}") from exception

    package = data.get("package")
    if not isinstance(package, dict):
        raise AndroidProjectError("memingo.toml must contain a [package] section")

    config = _android_config(data)
    unknown = sorted(set(config) - ANDROID_ALLOWED_KEYS)
    if unknown:
        raise AndroidProjectError(
            "Unknown [android] setting(s): " + ", ".join(unknown)
        )

    schema_version = config.get("schema_version", 1)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int) or schema_version != 1:
        raise AndroidProjectError("[android].schema_version must be 1")

    application_id = config.get("application_id")
    if not isinstance(application_id, str) or not APPLICATION_ID_PATTERN.fullmatch(application_id):
        raise AndroidProjectError(
            "[android].application_id must be a valid Java package name, "
            "for example 'com.example.my_app'"
        )

    values = {}
    for key, default in ANDROID_DEFAULTS.items():
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise AndroidProjectError(f"[android].{key} must be an integer")
        values[key] = value

    if not 21 <= values["min_sdk"] <= 100:
        raise AndroidProjectError("[android].min_sdk must be between 21 and 100")
    if not values["min_sdk"] <= values["target_sdk"] <= 100:
        raise AndroidProjectError(
            "[android].target_sdk must be between min_sdk and 100"
        )
    if not 1 <= values["version_code"] <= 2_100_000_000:
        raise AndroidProjectError(
            "[android].version_code must be between 1 and 2100000000"
        )

    version_name = config.get("version_name", package.get("version", "0.1.0"))
    if not isinstance(version_name, str) or not version_name.strip():
        raise AndroidProjectError("[android].version_name must be a non-empty string")

    ui = config.get("ui", "compose")
    if ui != "compose":
        raise AndroidProjectError(
            "[android].ui currently supports only 'compose'"
        )

    try:
        _, entry_name, entry_path = resolve_entry(root)
    except (OSError, ValueError) as exception:
        raise AndroidProjectError(f"Invalid Memingo entry point: {exception}") from exception
    if not entry_path.is_file():
        raise AndroidProjectError(f"Memingo entry file does not exist: {entry_name}")

    return {
        "root": root,
        "manifest": manifest_path,
        "name": package.get("name", root.name),
        "application_id": application_id,
        "min_sdk": values["min_sdk"],
        "target_sdk": values["target_sdk"],
        "version_code": values["version_code"],
        "version_name": version_name,
        "ui": ui,
        "entry": entry_name,
    }


def initialize_android_project(
    directory=".",
    application_id=None,
    min_sdk=ANDROID_DEFAULTS["min_sdk"],
    target_sdk=ANDROID_DEFAULTS["target_sdk"],
):
    """Add Android settings without replacing existing project files/settings."""
    root = Path(directory).resolve()
    ensure_project(root)
    manifest_path = root / "memingo.toml"

    try:
        data = read_manifest(root)
    except (OSError, ValueError) as exception:
        raise AndroidProjectError(f"Cannot read memingo.toml: {exception}") from exception

    if "android" in data:
        raise AndroidProjectError(
            "[android] is already configured; edit memingo.toml to change it"
        )

    package = data.get("package")
    if not isinstance(package, dict):
        raise AndroidProjectError("memingo.toml must contain a [package] section")

    selected_id = application_id or _default_application_id(
        package.get("name", root.name)
    )
    config = {
        "schema_version": 1,
        "application_id": selected_id,
        "min_sdk": min_sdk,
        "target_sdk": target_sdk,
        "version_code": 1,
        "version_name": str(package.get("version", "0.1.0")),
        "ui": "compose",
    }

    # Validate every supplied value before touching the existing manifest.
    if not isinstance(selected_id, str) or not APPLICATION_ID_PATTERN.fullmatch(selected_id):
        raise AndroidProjectError(
            "[android].application_id must be a valid Java package name, "
            "for example 'com.example.my_app'"
        )
    if isinstance(min_sdk, bool) or not isinstance(min_sdk, int) or not 21 <= min_sdk <= 100:
        raise AndroidProjectError("[android].min_sdk must be between 21 and 100")
    if isinstance(target_sdk, bool) or not isinstance(target_sdk, int) or not min_sdk <= target_sdk <= 100:
        raise AndroidProjectError("[android].target_sdk must be between min_sdk and 100")
    version_name = config["version_name"]
    if not isinstance(version_name, str) or not version_name.strip():
        raise AndroidProjectError("[android].version_name must be a non-empty string")

    lines = [
        "",
        "# Native Android application configuration (Memingo A0)",
        "[android]",
        "schema_version = 1",
        f"application_id = {json.dumps(selected_id)}",
        f"min_sdk = {min_sdk}",
        f"target_sdk = {target_sdk}",
        "version_code = 1",
        f"version_name = {json.dumps(version_name)}",
        'ui = "compose"',
        "",
    ]

    original = manifest_path.read_text(encoding="utf-8")
    temporary_path = manifest_path.with_name(manifest_path.name + ".tmp")
    try:
        temporary_path.write_text(original.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")
        temporary_path.replace(manifest_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return validate_android_project(root)
