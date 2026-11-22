import unittest
from pathlib import Path

from memingo.interpreter import Interpreter
from memingo.parser import parse


ROOT = Path(__file__).resolve().parent.parent
MEME_PACKAGES = ("brainrot", "yapstats", "luckymeme", "whenisbro")


class MemeStandardLibraryTests(unittest.TestCase):
    def test_meme_packages_parse_and_pass_self_test(self):
        for package in MEME_PACKAGES:
            with self.subTest(package=package):
                source_path = ROOT / "packages" / package / "main.mgo"
                source = source_path.read_text(encoding="utf-8")
                interpreter = Interpreter(project_directory=ROOT)
                interpreter.run(parse(source))
                self_test = interpreter.global_environment.get("self_test")
                self.assertTrue(self_test.call(interpreter, []))


if __name__ == "__main__":
    unittest.main()
