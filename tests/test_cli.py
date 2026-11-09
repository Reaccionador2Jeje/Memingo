import contextlib
import io
import os
import unittest

from memingo.cli import banner, command_header, error, heading, key_value, panel, status_bar, success, table, tip
from memingo.__main__ import main as memingo_main
from memingo.mgoa_cli import main as mgoa_main


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

    def test_mgoa_dashboard(self):
        output = self.capture(mgoa_main, [])
        self.assertIn("MEMINGO", output.upper())
        self.assertIn("PACKAGE CONSOLE", output.upper())

    def test_shell_completion(self):
        for command, expected in (
            (lambda shell: memingo_main(["completion", shell]), ("complete -F _memingo_completion memingo", "stats", "completion")),
            (lambda shell: mgoa_main(["completion", shell]), ("complete -F _mgoa_completion mgoa", "publish", "completion")),
        ):
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                self.assertEqual(command("bash"), 0)
            output = stream.getvalue()
            for text in expected:
                self.assertIn(text, output)

        fish_output = self.capture(lambda: memingo_main(["completion", "fish"]))
        self.assertIn("complete -c memingo", fish_output)
        zsh_output = self.capture(lambda: mgoa_main(["completion", "zsh"]))
        self.assertIn("#compdef mgoa", zsh_output)

    def test_command_header(self):
        output = self.capture(command_header, "memingo", "build", "CREATE RELEASE ARTIFACT")
        self.assertIn("MEMINGO / BUILD", output.upper())
        self.assertIn("CREATE RELEASE ARTIFACT", output.upper())

    def test_art_components(self):
        output = self.capture(panel, "Project", ["main.mgo ready", "mgoa linked"])
        output += self.capture(status_bar, [("Language", "Memingo", "33"), ("Package", "mgoa", "81")])
        output += self.capture(tip, "Run memingo dev while you build")
        self.assertIn("PROJECT", output.upper())
        self.assertIn("MEMINGO", output.upper())
        self.assertIn("TIP", output.upper())

    def test_heading_key_value_and_table(self):
        output = self.capture(heading, "Package Manager")
        output += self.capture(key_value, [("Python", "3.12")])
        output += self.capture(table, ["package", "latest"], [["hello-memes", "0.1.0"]])
        self.assertIn("PACKAGE MANAGER", output.upper())
        self.assertIn("hello-memes", output)


if __name__ == "__main__":
    unittest.main()
