import tempfile
import unittest
from pathlib import Path

from memingo.interpreter import execute
from memingo.mgoa import add_package, publish_package


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


if __name__ == "__main__":
    unittest.main()
