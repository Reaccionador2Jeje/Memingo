import contextlib
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from memingo.__main__ import build_project, main, project_stats
from memingo.packages import add_dependency, install_dependencies, read_manifest, remove_dependency


class ProjectToolsTests(unittest.TestCase):
    def test_init_add_install_remove_and_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            self.assertEqual(main(["init", temporary, "--name", "skibidi-app"]), 0)
            manifest = read_manifest(root)
            self.assertEqual(manifest["package"]["name"], "skibidi-app")
            self.assertTrue((root / "main.mgo").exists())

            add_dependency(root, "meme-core=1.2.0")
            manifest = read_manifest(root)
            self.assertEqual(manifest["dependencies"]["meme-core"], "1.2.0")

            dependencies = install_dependencies(root)
            self.assertEqual(dependencies["meme-core"], "1.2.0")
            self.assertTrue((root / ".memingo" / "packages" / "meme-core" / "PACKAGE.json").exists())
            self.assertTrue((root / "memingo.lock.json").exists())

            self.assertEqual(build_project(root), 0)
            self.assertTrue((root / "dist" / "skibidi-app.zip").exists())

            remove_dependency(root, "meme-core")
            manifest = read_manifest(root)
            self.assertNotIn("meme-core", manifest["dependencies"])

    def test_run_directory_and_build_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(main(["init", temporary, "--name", "run-app"]), 0)
            (root / "main.mgo").write_text('spill "from project"\n', encoding="utf-8")
            (root / "assets").mkdir()
            (root / "assets" / "data.txt").write_text("asset", encoding="utf-8")

            stream = io.StringIO()
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                self.assertEqual(main(["run", temporary]), 0)
            self.assertIn("from project", stream.getvalue())

            self.assertEqual(build_project(root), 0)
            with zipfile.ZipFile(root / "dist" / "run-app.zip") as archive:
                self.assertIn("assets/data.txt", archive.namelist())
                self.assertNotIn(".env", archive.namelist())

            stream = io.StringIO()
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                self.assertEqual(project_stats(root), 0)
            self.assertIn("MGO files", stream.getvalue())
            self.assertEqual(main(["stats", str(root)]), 0)


if __name__ == "__main__":
    unittest.main()
