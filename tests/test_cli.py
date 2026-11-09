import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memingo.cli import banner, command_header, error, heading, key_value, panel, status_bar, success, table, tip
from memingo.__main__ import main as memingo_main, serve_api
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


class ApiCliTests(unittest.TestCase):
    def test_serve_api_loads_exported_app(self):
        with tempfile.TemporaryDirectory() as directory:
            app_file = Path(directory) / "app.py"
            app_file.write_text(
                "from memingo import MemingoApp\\napp = MemingoApp()\\n",
                encoding="utf-8",
            )
            with patch("memingo.__main__.serve_app") as start_server:
                self.assertEqual(serve_api(str(app_file), "127.0.0.1", 8123), 0)
                start_server.assert_called_once()
                app, host, port = start_server.call_args.args
                self.assertEqual(host, "127.0.0.1")
                self.assertEqual(port, 8123)
                self.assertEqual(type(app).__name__, "MemingoApp")

    def test_serve_api_requires_memingo_app_export(self):
        with tempfile.TemporaryDirectory() as directory:
            app_file = Path(directory) / "app.py"
            app_file.write_text("app = object()\\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must export 'app = MemingoApp"):
                serve_api(str(app_file))


if __name__ == "__main__":
    unittest.main()
