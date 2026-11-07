import tempfile
import unittest
from pathlib import Path

from memingo.__main__ import build_project, main
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


if __name__ == "__main__":
    unittest.main()
