import importlib.util
import tempfile
from types import SimpleNamespace
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

    def test_apt_indexes_cover_independent_and_detected_architectures(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "site" / "linux"
            package = root / "memingo_arm64.deb"
            package.write_bytes(b"fake deb")
            def package_architecture(command, text=True):
                return "arm64"
            with mock.patch.object(MODULE.shutil, "which", side_effect=lambda name: f"/usr/bin/{name}"), mock.patch.object(
                MODULE.subprocess, "check_output", side_effect=package_architecture
            ), mock.patch.object(MODULE.subprocess, "run") as run:
                def fake_run(command, **kwargs):
                    if command[0].endswith("dpkg-scanpackages"):
                        return SimpleNamespace(stdout="")
                    return SimpleNamespace(stdout="MD5Sum:\n abc 1 sample\nSHA1:\n def 1 sample\nSHA256:\n ghi 1 sample\nSHA512:\n jkl 1 sample\n")
                run.side_effect = fake_run
                result = MODULE.build_apt_repository(output, None, [package])
            self.assertTrue(result)
            release = (output / "apt" / "dists" / "stable" / "Release").read_text(encoding="utf-8")
            self.assertIn("Architectures: amd64 arm64 armhf i386", release)
            self.assertTrue((output / "apt" / "dists" / "stable" / "main" / "binary-amd64" / "Packages.gz").is_file())
            self.assertTrue((output / "apt" / "dists" / "stable" / "main" / "binary-arm64" / "Packages.gz").is_file())
            commands = [call.args[0] for call in run.call_args_list]
            self.assertIn("--arch", commands[0])
            self.assertEqual(sum(1 for command in commands if command[0] == "dpkg-scanpackages"), 4)

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
