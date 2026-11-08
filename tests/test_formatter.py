import tempfile
import unittest
from pathlib import Path

from memingo.formatter import format_file, format_source


class FormatterTests(unittest.TestCase):
    def test_indentation_handles_nested_blocks(self):
        source = (
            "ritual f(n) {\n"
            "when n <= 1 {\n"
            "drop 1\n"
            "}\n"
            "drop n * f(n - 1)\n"
            "}\n"
        )
        self.assertEqual(
            format_source(source),
            "ritual f(n) {\n"
            "    when n <= 1 {\n"
            "        drop 1\n"
            "    }\n"
            "    drop n * f(n - 1)\n"
            "}\n",
        )

    def test_multiline_collections_and_trailing_commas(self):
        source = (
            "vibe world = {\n"
            'name: "MemeCraft",\n'
            "size: 30\n"
            "}\n"
            "vibe items = [\n"
            'item,\n'
            "]\n"
        )
        self.assertEqual(
            format_source(source),
            "vibe world = {\n"
            '    name: "MemeCraft",\n'
            "    size: 30\n"
            "}\n"
            "vibe items = [\n"
            "    item,\n"
            "]\n",
        )

    def test_strings_and_comments_do_not_change_depth(self):
        source = 'spill "brace } in string" # comment {\nvibe x = 1\n'
        self.assertEqual(
            format_source(source),
            'spill "brace } in string" # comment {\nvibe x = 1\n',
        )

    def test_formatting_is_idempotent(self):
        source = "vibe items = [\n{name: \"grass\"},\n{name: \"stone\"},\n]\n"
        once = format_source(source)
        self.assertEqual(format_source(once), once)

    def test_format_file_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "main.mgo"
            path.write_text("vibe x = 1\nvibe y = 2\n", encoding="utf-8")
            formatted = format_file(str(path))
            self.assertEqual(formatted, "vibe x = 1\nvibe y = 2\n")
            format_file(str(path), write=True)
            self.assertEqual(path.read_text(encoding="utf-8"), formatted)


if __name__ == "__main__":
    unittest.main()
