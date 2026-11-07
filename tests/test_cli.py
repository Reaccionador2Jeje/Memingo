import contextlib
import io
import os
import unittest

from memingo.cli import banner, error, heading, key_value, success, table


class CliStyleTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("FORCE_COLOR", None)
        os.environ["NO_COLOR"] = "1"

    def tearDown(self):
        os.environ.pop("NO_COLOR", None)

    def capture(self, function, *args):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            function(*args)
        return stream.getvalue()

    def test_banner_and_success_output(self):
        output = self.capture(banner, "0.1.0") + self.capture(success, "ready")
        self.assertIn("MEMINGO", output.upper())
        self.assertIn("ready", output)
        self.assertNotIn("\033[", output)

    def test_heading_key_value_and_table(self):
        output = self.capture(heading, "Package Manager")
        output += self.capture(key_value, [("Python", "3.12")])
        output += self.capture(table, ["package", "latest"], [["hello-memes", "0.1.0"]])
        self.assertIn("PACKAGE MANAGER", output.upper())
        self.assertIn("hello-memes", output)


if __name__ == "__main__":
    unittest.main()
