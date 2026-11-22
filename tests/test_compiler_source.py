import unittest

from memingo.compiler import SourceFile, SourceMap, Span


class SourceFileTests(unittest.TestCase):
    def test_offsets_map_to_one_based_locations(self):
        source = SourceFile("hello.mgo", "vibe x = 1\nspill x")
        self.assertEqual(source.location_at(0).line, 1)
        self.assertEqual(source.location_at(5).column, 6)
        self.assertEqual(source.location_at(11).line, 2)
        self.assertEqual(source.location_at(11).column, 1)

    def test_unicode_offsets_use_python_character_positions(self):
        source = SourceFile("unicode.mgo", 'spill "🚀"')
        location = source.location_at(7)
        self.assertEqual((location.line, location.column), (1, 8))

    def test_line_text_and_slice(self):
        source = SourceFile("lines.mgo", "first\nsecond\n")
        self.assertEqual(source.line_text(1), "first")
        self.assertEqual(source.line_text(2), "second")
        self.assertEqual(source.line_text(3), "")
        self.assertEqual(source.slice(Span("lines.mgo", 6, 12)), "second")

    def test_invalid_offsets_and_spans_are_rejected(self):
        source = SourceFile("safe.mgo", "abc")
        with self.assertRaises(ValueError):
            source.location_at(4)
        with self.assertRaises(ValueError):
            Span("safe.mgo", 3, 2)
        with self.assertRaises(ValueError):
            source.slice(Span("safe.mgo", 0, 4))

    def test_source_map_rejects_duplicate_ids(self):
        source_map = SourceMap([SourceFile("main.mgo", "spill 1")])
        with self.assertRaises(ValueError):
            source_map.add(SourceFile("main.mgo", "spill 2"))
        source_map.replace(SourceFile("main.mgo", "spill 3"))
        self.assertEqual(source_map.get("main.mgo").text, "spill 3")


if __name__ == "__main__":
    unittest.main()
