"""Android project configuration and validation for Memingo.

A0 deliberately manages project metadata only. Code generation and Gradle
invocation belong to later Android backend milestones.
"""

import html
import json
import os
import re
import shutil
import subprocess
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
        "schema_version": schema_version,
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


# Files in this directory are generated and owned by Memingo's Android backend.
GENERATED_MARKER = "Generated by Memingo Android backend"
ANDROID_GENERATED_FILES = {
    "settings.gradle.kts": lambda config: """// Generated by Memingo Android backend. Do not edit this file directly.
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "MemingoAndroid"
include(":app")
""",
    "build.gradle.kts": lambda config: """// Generated by Memingo Android backend. Do not edit this file directly.
plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21" apply false
}
""",
    "gradle.properties": lambda config: """# Generated by Memingo Android backend. Do not edit this file directly.
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
org.gradle.parallel=true
android.useAndroidX=true
kotlin.code.style=official
""",
    "app/build.gradle.kts": lambda config: _android_app_gradle(config),
    "app/src/main/AndroidManifest.xml": lambda config: _android_manifest(config),
    "app/src/main/java/__PACKAGE__/MainActivity.kt": lambda config: _android_activity(config),
}


def _android_package_path(application_id):
    return application_id.replace(".", "/")


def _android_app_gradle(config):
    return f"""// Generated by Memingo Android backend. Do not edit this file directly.
plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}}

android {{
    namespace = "{config['application_id']}"
    compileSdk = {config['target_sdk']}

    defaultConfig {{
        applicationId = "{config['application_id']}"
        minSdk = {config['min_sdk']}
        targetSdk = {config['target_sdk']}
        versionCode = {config['version_code']}
        versionName = {json.dumps(config["version_name"], ensure_ascii=False)}
    }}

    buildFeatures {{
        compose = true
    }}

    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}
    kotlinOptions {{
        jvmTarget = "17"
    }}
}}

dependencies {{
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    debugImplementation("androidx.compose.ui:ui-tooling")
}}
"""


def _android_manifest(config):
    label = html.escape(config["name"], quote=True)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by Memingo Android backend. Do not edit this file directly. -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:allowBackup="true"
        android:label="{label}"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
'''


def _android_activity(config):
    package_name = config["application_id"]
    title = json.dumps(config["name"], ensure_ascii=False).replace("$", "\\$")
    return f'''// Generated by Memingo Android backend. Do not edit this file directly.
package {package_name}

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {{
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContent {{
            MaterialTheme {{
                Surface(modifier = Modifier.fillMaxSize()) {{
                    WelcomeScreen()
                }}
            }}
        }}
    }}
}}

@Composable
private fun WelcomeScreen() {{
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {{
        Text(
            text = "Hello from Memingo!",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold
        )
        Text(text = "{title}")
    }}
}}
'''


def generate_android_project(directory="."):
    """Generate a minimal native Kotlin/Compose Android Gradle project."""
    config = validate_android_project(directory)
    root = config["root"]
    android_root = root / "android"
    package_path = _android_package_path(config["application_id"])
    generated = {}
    for relative, factory in ANDROID_GENERATED_FILES.items():
        target_relative = relative.replace("__PACKAGE__", package_path)
        target = android_root / target_relative
        generated[target] = factory(config)

    # Never replace user-owned files. Existing generated files are refreshed
    # only when they carry the explicit Memingo ownership marker.
    conflicts = []
    for target in generated:
        if target.exists():
            try:
                current = target.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                conflicts.append(target)
                continue
            if GENERATED_MARKER not in current:
                conflicts.append(target)
    if conflicts:
        names = ", ".join(str(path.relative_to(root)) for path in conflicts)
        raise AndroidProjectError(
            "Refusing to overwrite user-owned Android file(s): " + names
        )

    for target, source in generated.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".memingo-tmp")
        try:
            temporary.write_text(source, encoding="utf-8")
            temporary.replace(target)
        finally:
            if temporary.exists():
                temporary.unlink()

    (root / "assets").mkdir(exist_ok=True)
    return {
        **config,
        "android_project": android_root,
        "generated_files": tuple(
            str(path.relative_to(root)) for path in sorted(generated)
        ),
        "main_activity": android_root / "app" / "src" / "main" / "java" / package_path / "MainActivity.kt",
    }


def android_build_environment():
    """Return detected Android build tools and actionable missing requirements."""
    java = shutil.which("java")
    gradle = shutil.which("gradle")
    sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
    missing = []
    if not java:
        missing.append("Java 17 or newer (java on PATH)")
    if not gradle:
        missing.append("Gradle 8.9 or newer (gradle on PATH)")
    if not sdk or not Path(sdk).is_dir():
        missing.append("Android SDK (set ANDROID_SDK_ROOT or ANDROID_HOME)")
    return {"java": java, "gradle": gradle, "sdk": sdk, "missing": missing}


def build_android_debug(directory="."):
    """Build a debug APK with the installed Android SDK and Gradle toolchain."""
    config = validate_android_project(directory)
    android_root = config["root"] / "android"
    if not (android_root / "app" / "build.gradle.kts").is_file():
        raise AndroidProjectError(
            "Native project files are missing. Run 'memingo android generate' first."
        )
    environment = android_build_environment()
    if environment["missing"]:
        raise AndroidProjectError(
            "Android build toolchain is incomplete: " + "; ".join(environment["missing"])
        )

    command = [
        environment["gradle"], "--no-daemon", "--project-dir",
        str(android_root), ":app:assembleDebug",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=config["root"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except OSError as exception:
        raise AndroidProjectError(f"Could not start Gradle: {exception}") from exception
    if result.returncode != 0:
        tail = "\n".join(result.stdout.splitlines()[-30:])
        raise AndroidProjectError(
            f"Gradle debug build failed (exit {result.returncode}).\n{tail}"
        )
    apk = android_root / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if not apk.is_file():
        raise AndroidProjectError(
            "Gradle reported success but the expected APK was not created"
        )
    return {"apk": apk, "output": result.stdout}
