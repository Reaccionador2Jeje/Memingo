import unittest
from pathlib import Path

from memingo.desktop import STARTER, CONFIG_FILE
from memingo.parser import parse


class DesktopAppTests(unittest.TestCase):
    def test_starter_program_is_valid_memingo(self):
        self.assertIsNotNone(parse(STARTER))

    def test_setup_wizard_starter_has_expected_project_entry(self):
        self.assertIn('greet("creator")', STARTER)
        self.assertEqual(CONFIG_FILE.parts[-2:], ("Memingo", "desktop.json"))

    def test_desktop_entry_imports_gui(self):
        source = (Path(__file__).resolve().parents[1] / "scripts" / "desktop_entry.py").read_text(encoding="utf-8")
        self.assertIn("from memingo.desktop import main", source)


if __name__ == "__main__":
    unittest.main()
