import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from memingo.interpreter import execute
from memingo.mgoa import add_package
from memingo.packages import _read_simple_toml


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "site" / "mgoa" / "index.json"
ARCHIVES = ROOT / "site" / "mgoa" / "packages"
PACKAGE_SOURCES = ROOT / "packages"


def load_registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


class RegistryPackageTests(unittest.TestCase):
    def test_registry_catalog_is_populated(self):
        registry = load_registry()
        self.assertEqual(registry["schema"], "memingo-approved/v1")
        packages = registry["approved"]["packages"]
        self.assertGreaterEqual(len(packages), 10)
        for name, record in packages.items():
            self.assertEqual(name, name.strip())
            self.assertTrue(record.get("description"), name)
            self.assertTrue(record.get("latest"), name)
            self.assertIn(record["latest"], record["versions"])
            self.assertTrue(record["versions"][record["latest"]]["archive"].endswith(".zip"))

    def test_every_source_package_is_published(self):
        registry = load_registry()["approved"]["packages"]
        sources = sorted(
            path.name
            for path in PACKAGE_SOURCES.iterdir()
            if path.is_dir() and ((path / "package.toml").exists() or (path / "memingo.toml").exists())
        )
        self.assertEqual(sources, sorted(registry))
        for name in sources:
            manifest_path = PACKAGE_SOURCES / name / "package.toml"
            if not manifest_path.exists():
                manifest_path = PACKAGE_SOURCES / name / "memingo.toml"
            manifest = _read_simple_toml(manifest_path)
            package = manifest["package"]
            self.assertEqual(package["name"], name)
            self.assertEqual(package["version"], registry[name]["latest"])

    def test_registry_archives_match_checksums(self):
        packages = load_registry()["approved"]["packages"]
        for name, record in packages.items():
            version = record["latest"]
            release = record["versions"][version]
            archive = ARCHIVES / Path(release["archive"]).name
            self.assertEqual(archive.name, f"{name}-{version}.zip")
            self.assertTrue(archive.is_file(), archive)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            self.assertEqual(digest, release["sha256"], name)
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertIn("main.mgo", names)
                self.assertTrue(
                    "package.toml" in names or "memingo.toml" in names,
                    name,
                )

    def test_every_package_installs_and_passes_self_test(self):
        registry = load_registry()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            local_registry = json.loads(json.dumps(registry))
            for record in local_registry["approved"]["packages"].values():
                for release in record["versions"].values():
                    release["archive"] = (ARCHIVES / Path(release["archive"]).name).as_uri()
            index_path = root / "index.json"
            index_path.write_text(json.dumps(local_registry), encoding="utf-8")
            registry_url = index_path.as_uri()

            for name in sorted(registry["approved"]["packages"]):
                with self.subTest(package=name):
                    project = root / f"app-{name}"
                    project.mkdir()
                    (project / "memingo.toml").write_text(
                        f'[package]\nname = "{name}-app"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                        encoding="utf-8",
                    )
                    installed = add_package(project, name, registry_url=registry_url)
                    self.assertEqual(installed["name"], name)
                    self.assertTrue(installed["approved"])
                    output = execute(
                        f'borrow "{name}"\nspill self_test()\n',
                        project_directory=project,
                    )
                    self.assertEqual(output, ["based"], name)


if __name__ == "__main__":
    unittest.main()
