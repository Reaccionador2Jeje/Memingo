import json
import tempfile
import unittest
from pathlib import Path

from memingo.interpreter import execute
from memingo.mgoa import add_package, install_project


class MgoaLocalSourceTests(unittest.TestCase):
    def test_add_local_mgo_file_and_reinstall_from_lockfile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            project.mkdir()
            (project / "memingo.toml").write_text(
                '[package]\nname = "app"\nversion = "0.1.0"\n'
                'entry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            (project / "main.mgo").write_text(
                'borrow "greetings"\ngreet("MGOA")\n', encoding="utf-8"
            )
            source = project / "greetings.mgo"
            source.write_text(
                'vibe greeting = "Hello"\n'
                'ritual greet(name) { spill greeting + " " + name }\n',
                encoding="utf-8",
            )

            installed = add_package(project, str(source))
            self.assertEqual(installed["name"], "greetings")
            self.assertEqual(installed["version"], "0.0.0-local")
            self.assertEqual(
                execute((project / "main.mgo").read_text(encoding="utf-8"),
                        project_directory=project),
                ["Hello MGOA"],
            )

            lock = json.loads((project / "memingo.lock.json").read_text(encoding="utf-8"))
            record = lock["dependencies"]["greetings"]
            self.assertEqual(record["source"], "local")
            self.assertEqual(record["path"], "greetings.mgo")

            installed_path = project / ".memingo" / "packages" / "greetings"
            self.assertTrue((installed_path / "main.mgo").is_file())
            (installed_path / "main.mgo").unlink()
            install_project(project)
            self.assertTrue((installed_path / "main.mgo").is_file())
            self.assertEqual(
                execute((project / "main.mgo").read_text(encoding="utf-8"),
                        project_directory=project),
                ["Hello MGOA"],
            )

    def test_local_mgo_name_is_normalized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            project.mkdir()
            (project / "memingo.toml").write_text(
                '[package]\nname = "app"\nversion = "0.1.0"\n'
                'entry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            source = root / "my helpers!.mgo"
            source.write_text('spill "ok"\n', encoding="utf-8")
            installed = add_package(project, str(source))
            self.assertEqual(installed["name"], "my-helpers")


if __name__ == "__main__":
    unittest.main()
