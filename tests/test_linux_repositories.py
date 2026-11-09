import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build-linux-repositories.py"
SPEC = importlib.util.spec_from_file_location("build_linux_repositories", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LinuxRepositorySelectionTests(unittest.TestCase):
    def test_rpm_only_preserves_existing_apt_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dist = root / "dist"
            output = root / "site" / "linux"
            dist.mkdir()
            (dist / "memingo-0.2.0-1.noarch.rpm").write_bytes(b"rpm")
            apt_marker = output / "apt" / "keep.txt"
            apt_marker.parent.mkdir(parents=True)
            apt_marker.write_text("keep", encoding="utf-8")

            with mock.patch.object(MODULE, "DIST", dist), mock.patch.object(
                MODULE, "build_rpm_repository", return_value=True
            ):
                result = MODULE.main(["--only", "rpm", "--output", str(output)])

            self.assertEqual(result, 0)
            self.assertEqual(apt_marker.read_text(encoding="utf-8"), "keep")

    def test_apt_only_preserves_existing_rpm_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            dist = root / "dist"
            output = root / "site" / "linux"
            dist.mkdir()
            (dist / "memingo_0.2.0_all.deb").write_bytes(b"deb")
            rpm_marker = output / "rpm" / "keep.txt"
            rpm_marker.parent.mkdir(parents=True)
            rpm_marker.write_text("keep", encoding="utf-8")

            with mock.patch.object(MODULE, "DIST", dist), mock.patch.object(
                MODULE, "build_apt_repository", return_value=True
            ):
                result = MODULE.main(["--only", "apt", "--output", str(output)])

            self.assertEqual(result, 0)
            self.assertEqual(rpm_marker.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
