import json
import tempfile
import unittest
from pathlib import Path

from memingo.interpreter import execute
from memingo.mgoa import PackageError, add_package, install_package, publish_package
from memingo.packages import read_manifest


class MgoaTests(unittest.TestCase):
    def test_local_package_publish_install_and_borrow(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            project.mkdir()

            (project / "memingo.toml").write_text(
                '[package]\nname = "demo-app"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            (project / "main.mgo").write_text('borrow "hello-memes"\ngreet("Team")\n', encoding="utf-8")

            package = root / "hello-memes"
            package.mkdir()
            (package / "package.toml").write_text(
                '[package]\nname = "hello-memes"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text(
                'vibe meme_hello = "Hello from approved package"\nritual greet(name) { spill meme_hello + " " + name }\n',
                encoding="utf-8",
            )

            installed = add_package(project, str(package))
            output = execute((project / "main.mgo").read_text(encoding="utf-8"), project_directory=project)
            self.assertEqual(installed["name"], "hello-memes")
            self.assertEqual(output, ["Hello from approved package Team"])

            archive = publish_package(package, root / "dist")
            self.assertTrue(archive.exists())
            self.assertTrue(Path(str(archive) + ".sha256").exists())

    def test_publish_rejects_unsafe_names_and_excludes_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            package.mkdir()
            (package / "memingo.toml").write_text(
                '[package]\nname = "../../escape"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text('spill "nope"\n', encoding="utf-8")
            with self.assertRaises(PackageError):
                publish_package(package, root / "dist")

            (package / "memingo.toml").write_text(
                '[package]\nname = "safe"\nversion = "0.1.0"\nentry = "main.mgo"\ndescription = "kept"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            archive = publish_package(package, package / "dist")
            import zipfile
            names = zipfile.ZipFile(archive).namelist()
            self.assertIn("main.mgo", names)
            self.assertIn("memingo.toml", names)
            self.assertFalse(any(name.startswith("dist/") for name in names))

    def test_install_verifies_lockfile_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            project.mkdir()
            (project / "memingo.toml").write_text(
                '[package]\nname = "app"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            package = root / "hello"
            package.mkdir()
            (package / "memingo.toml").write_text(
                '[package]\nname = "hello"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text('spill "hello"\n', encoding="utf-8")
            installed = add_package(project, str(package))
            self.assertEqual(installed["name"], "hello")
            self.assertEqual(read_manifest(project)["dependencies"]["hello"], "0.1.0")

            lock_path = project / "memingo.lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["dependencies"]["hello"]["sha256"] = "0" * 64
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            with self.assertRaises(PackageError):
                install_package(project, str(package), expected_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
