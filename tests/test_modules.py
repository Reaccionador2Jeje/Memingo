import tempfile
import unittest
from pathlib import Path

from memingo.interpreter import Interpreter, RuntimeErrorMemingo
from memingo.parser import parse


class ModuleImportTests(unittest.TestCase):
    def run_source(self, root, source):
        interpreter = Interpreter(project_directory=root)
        interpreter.run(parse(source))
        return interpreter

    def test_import_exposes_module_values_and_functions_under_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "maths.mgo").write_text(
                'vibe answer = 42\nritual double(value) { drop value * 2 }\n',
                encoding="utf-8",
            )
            interpreter = self.run_source(
                root,
                'import "maths.mgo" as maths\nspill maths.answer\nspill maths.double(21)\n',
            )
            self.assertEqual(interpreter.output, ["42", "42"])

    def test_import_is_cached_and_aliases_share_module_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "counter.mgo").write_text(
                'vibe count = 1\nritual get_count() { drop count }\n',
                encoding="utf-8",
            )
            interpreter = self.run_source(
                root,
                'import "counter.mgo" as first\nimport "counter.mgo" as second\nspill first.get_count()\nspill second.count\n',
            )
            self.assertEqual(interpreter.output, ["1", "1"])
            self.assertIs(
                interpreter.global_environment.get("first"),
                interpreter.global_environment.get("second"),
            )

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / (root.name + "-outside.mgo")
            outside.write_text('spill "no"\n', encoding="utf-8")
            try:
                with self.assertRaisesRegex(RuntimeErrorMemingo, "inside the project"):
                    self.run_source(root, f'import "../{outside.name}" as nope')
            finally:
                outside.unlink(missing_ok=True)


    def test_detects_circular_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "first.mgo").write_text('import "second.mgo" as second\n', encoding="utf-8")
            (root / "second.mgo").write_text('import "first.mgo" as first\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeErrorMemingo, "Circular module import"):
                self.run_source(root, 'import "first.mgo" as first')

    def test_reports_missing_module(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeErrorMemingo, "Module not found"):
                self.run_source(Path(directory), 'import "missing.mgo" as missing')


if __name__ == "__main__":
    unittest.main()
