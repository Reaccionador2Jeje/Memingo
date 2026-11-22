import tempfile
import unittest
from pathlib import Path

from memingo.android import (
    AndroidProjectError,
    initialize_android_project,
    validate_android_project,
    generate_android_project,
)
from memingo.__main__ import main


class AndroidProjectTests(unittest.TestCase):
    def test_android_init_adds_native_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "demo-app"
            config = initialize_android_project(root)

            self.assertEqual(config["application_id"], "com.example.demo_app")
            self.assertEqual(config["schema_version"], 1)
            self.assertEqual(config["min_sdk"], 23)
            self.assertEqual(config["target_sdk"], 35)
            self.assertEqual(config["ui"], "compose")
            self.assertTrue((root / "main.mgo").is_file())
            self.assertIn("[android]", (root / "memingo.toml").read_text(encoding="utf-8"))

    def test_android_init_accepts_explicit_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = initialize_android_project(
                temporary,
                application_id="dev.atdev.sample",
                min_sdk=24,
                target_sdk=34,
            )
            self.assertEqual(config["application_id"], "dev.atdev.sample")
            self.assertEqual(config["min_sdk"], 24)
            self.assertEqual(config["target_sdk"], 34)

    def test_android_init_does_not_overwrite_existing_android_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            manifest = (root / "memingo.toml").read_text(encoding="utf-8")

            with self.assertRaisesRegex(AndroidProjectError, "already configured"):
                initialize_android_project(root, application_id="dev.atdev.changed")

            self.assertEqual((root / "memingo.toml").read_text(encoding="utf-8"), manifest)

    def test_invalid_application_id_is_rejected_without_manifest_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "memingo.toml"
            manifest.write_text(
                '[package]\nname = "demo"\nversion = "1.0.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            (root / "main.mgo").write_text('spill "hello"\n', encoding="utf-8")
            original = manifest.read_text(encoding="utf-8")

            with self.assertRaises(AndroidProjectError):
                initialize_android_project(root, application_id="not a package")

            self.assertEqual(manifest.read_text(encoding="utf-8"), original)

    def test_invalid_sdk_ranges_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(AndroidProjectError, "min_sdk"):
                initialize_android_project(temporary, min_sdk=20)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(AndroidProjectError, "target_sdk"):
                initialize_android_project(temporary, min_sdk=35, target_sdk=34)

    def test_validation_rejects_missing_android_section_and_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "memingo.toml").write_text(
                '[package]\nname = "demo"\nversion = "1.0.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AndroidProjectError, "Missing \\[android\\]"):
                validate_android_project(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            (root / "main.mgo").unlink()
            with self.assertRaisesRegex(AndroidProjectError, "entry file does not exist"):
                validate_android_project(root)

    def test_validation_rejects_unknown_keys_and_bad_target_sdk(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            manifest = root / "memingo.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8") + 'mystery = true\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(AndroidProjectError, "Unknown"):
                validate_android_project(root)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            manifest = root / "memingo.toml"
            source = manifest.read_text(encoding="utf-8").replace("target_sdk = 35", "target_sdk = 22")
            manifest.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(AndroidProjectError, "target_sdk"):
                validate_android_project(root)

    def test_validation_rejects_unsupported_schema_version(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            manifest = root / "memingo.toml"
            source = manifest.read_text(encoding="utf-8").replace(
                "schema_version = 1", "schema_version = 2"
            )
            manifest.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(AndroidProjectError, "schema_version"):
                validate_android_project(root)

    def test_cli_android_init_and_check(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(main(["android", "init", temporary, "--application-id", "dev.atdev.cli"]), 0)
            self.assertEqual(main(["android", "check", temporary]), 0)


    def test_generate_creates_native_compose_gradle_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "hello-app"
            initialize_android_project(root, application_id="dev.atdev.hello")
            result = generate_android_project(root)

            activity = root / "android/app/src/main/java/dev/atdev/hello/MainActivity.kt"
            gradle = root / "android/app/build.gradle.kts"
            manifest = root / "android/app/src/main/AndroidManifest.xml"
            self.assertTrue(activity.is_file())
            self.assertTrue(gradle.is_file())
            self.assertTrue(manifest.is_file())
            self.assertIn("package dev.atdev.hello", activity.read_text(encoding="utf-8"))
            self.assertIn("Hello from Memingo!", activity.read_text(encoding="utf-8"))
            self.assertIn("com.android.application", gradle.read_text(encoding="utf-8"))
            self.assertEqual(len(result["generated_files"]), 6)
            self.assertTrue((root / "assets").is_dir())

    def test_generate_is_repeatable_and_refreshes_only_owned_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            first = generate_android_project(root)
            activity = first["main_activity"]
            original = activity.read_text(encoding="utf-8")
            generate_android_project(root)
            self.assertEqual(activity.read_text(encoding="utf-8"), original)

    def test_generate_refuses_to_overwrite_user_owned_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_android_project(root)
            target = root / "android/settings.gradle.kts"
            target.parent.mkdir(parents=True)
            target.write_text("// my custom settings\\n", encoding="utf-8")

            with self.assertRaisesRegex(AndroidProjectError, "Refusing to overwrite"):
                generate_android_project(root)
            self.assertEqual(target.read_text(encoding="utf-8"), "// my custom settings\\n")

    def test_generate_requires_valid_android_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(AndroidProjectError):
                generate_android_project(temporary)

    def test_cli_android_generate(self):
        with tempfile.TemporaryDirectory() as temporary:
            initialize_android_project(temporary)
            self.assertEqual(main(["android", "generate", temporary]), 0)


if __name__ == "__main__":
    unittest.main()
