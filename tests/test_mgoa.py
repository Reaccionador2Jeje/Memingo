import contextlib
import functools
import hashlib
import http.server
import json
import shutil
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path

from memingo.interpreter import execute
from memingo.mgoa import (
    PackageError, add_package, install_package, install_project, list_installed,
    package_info, publish_package, resolve_package, search_registry,
)
from memingo.packages import read_manifest


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@contextlib.contextmanager
def serve_directory(directory):
    handler = functools.partial(_QuietHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def write_package(root, name, body='vibe greeting = "hello from package"\n'):
    package = root / name
    package.mkdir()
    (package / "memingo.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
        encoding="utf-8",
    )
    (package / "main.mgo").write_text(body, encoding="utf-8")
    return package


def write_project(root, name="app"):
    project = root / name
    project.mkdir()
    (project / "memingo.toml").write_text(
        f'[package]\nname = "{name}"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
        encoding="utf-8",
    )
    (project / "main.mgo").write_text('borrow "hello-url"\nspill greeting\n', encoding="utf-8")
    return project


class MgoaTests(unittest.TestCase):
    def test_local_package_publish_install_and_borrow(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            project.mkdir()

            (project / "memingo.toml").write_text(
                '[package]\nname = "demo-app"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            (project / "main.mgo").write_text('borrow "hello-memes"\ngreet("Team")\n', encoding="utf-8")

            package = root / "hello-memes"
            package.mkdir()
            (package / "package.toml").write_text(
                '[package]\nname = "hello-memes"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text(
                'vibe meme_hello = "Hello from approved package"\nritual greet(name) { spill meme_hello + " " + name }\n',
                encoding="utf-8",
            )

            installed = add_package(project, str(package))
            output = execute((project / "main.mgo").read_text(encoding="utf-8"), project_directory=project)
            self.assertEqual(installed["name"], "hello-memes")
            self.assertEqual(output, ["Hello from approved package Team"])

            archive = publish_package(package, root / "dist")
            self.assertTrue(archive.exists())
            self.assertTrue(Path(str(archive) + ".sha256").exists())

    def test_publish_rejects_unsafe_names_and_excludes_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            package.mkdir()
            (package / "memingo.toml").write_text(
                '[package]\nname = "../../escape"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text('spill "nope"\n', encoding="utf-8")
            with self.assertRaises(PackageError):
                publish_package(package, root / "dist")

            (package / "memingo.toml").write_text(
                '[package]\nname = "safe"\nversion = "0.1.0"\nentry = "main.mgo"\ndescription = "kept"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            archive = publish_package(package, package / "dist")
            import zipfile
            names = zipfile.ZipFile(archive).namelist()
            self.assertIn("main.mgo", names)
            self.assertIn("memingo.toml", names)
            self.assertFalse(any(name.startswith("dist/") for name in names))

    def test_install_verifies_lockfile_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "app"
            project.mkdir()
            (project / "memingo.toml").write_text(
                '[package]\nname = "app"\nversion = "0.1.0"\nentry = "main.mgo"\n\n[dependencies]\n',
                encoding="utf-8",
            )
            package = root / "hello"
            package.mkdir()
            (package / "memingo.toml").write_text(
                '[package]\nname = "hello"\nversion = "0.1.0"\nentry = "main.mgo"\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text('spill "hello"\n', encoding="utf-8")
            installed = add_package(project, str(package))
            self.assertEqual(installed["name"], "hello")
            self.assertEqual(read_manifest(project)["dependencies"]["hello"], "0.1.0")

            lock_path = project / "memingo.lock.json"
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            lock["dependencies"]["hello"]["sha256"] = "0" * 64
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            with self.assertRaises(PackageError):
                install_package(project, str(package), expected_sha256="0" * 64)

    def test_direct_archive_url_records_source_and_reinstalls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = write_package(root, "hello-url")
            archive = publish_package(package, root / "dist")
            with serve_directory(root / "dist") as base:
                url = f"{base}/{archive.name}"
                project = write_project(root)
                installed = add_package(project, url)
                self.assertEqual(installed["name"], "hello-url")
                self.assertFalse(installed["approved"])

                lock = json.loads((project / "memingo.lock.json").read_text(encoding="utf-8"))
                record = lock["dependencies"]["hello-url"]
                self.assertEqual(record["source"], "url")
                self.assertEqual(record["url"], url)
                self.assertFalse(record["approved"])

                output = execute(
                    (project / "main.mgo").read_text(encoding="utf-8"),
                    project_directory=project,
                )
                self.assertEqual(output, ["hello from package"])

                shutil.rmtree(project / ".memingo" / "packages" / "hello-url")
                install_project(project)
                self.assertTrue(
                    (project / ".memingo" / "packages" / "hello-url" / "main.mgo").exists()
                )

    def test_unapproved_registry_packages_can_be_installed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = write_package(root, "community-hello")
            archive = publish_package(package, root / "dist")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with serve_directory(root) as base:
                registry_url = f"{base}/registry.json"
                (root / "registry.json").write_text(
                    json.dumps({
                        "schema": "memingo-registry/v1",
                        "packages": {
                            "community-hello": {
                                "description": "community package",
                                "latest": "0.1.0",
                                "versions": {
                                    "0.1.0": {
                                        "archive": f"{base}/dist/{archive.name}",
                                        "sha256": digest,
                                    }
                                },
                            }
                        },
                    }),
                    encoding="utf-8",
                )

                matches = search_registry("community", registry_url)
                self.assertEqual(len(matches), 1)
                self.assertFalse(matches[0]["approved"])
                self.assertEqual(matches[0]["source"], "community")

                project = write_project(root)
                installed = add_package(project, "community-hello", registry_url)
                self.assertEqual(installed["name"], "community-hello")
                self.assertFalse(installed["approved"])

                lock = json.loads((project / "memingo.lock.json").read_text(encoding="utf-8"))
                record = lock["dependencies"]["community-hello"]
                self.assertEqual(record["source"], "registry")
                self.assertEqual(record["registry"], registry_url)
                self.assertFalse(record["approved"])

                shutil.rmtree(project / ".memingo" / "packages" / "community-hello")
                install_project(project)
                self.assertTrue(
                    (project / ".memingo" / "packages" / "community-hello" / "main.mgo").exists()
                )

    def test_approved_registry_packages_keep_approval_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = write_package(root, "official-hello")
            archive = publish_package(package, root / "dist")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            registry_path = root / "index.json"
            registry_path.write_text(
                json.dumps({
                    "schema": "memingo-approved/v1",
                    "approved": {
                        "packages": {
                            "official-hello": {
                                "latest": "0.1.0",
                                "versions": {
                                    "0.1.0": {
                                        "archive": archive.as_uri(),
                                        "sha256": digest,
                                    }
                                },
                            }
                        }
                    },
                }),
                encoding="utf-8",
            )

            project = write_project(root)
            installed = add_package(project, "official-hello", registry_path.as_uri())
            self.assertTrue(installed["approved"])
            lock = json.loads((project / "memingo.lock.json").read_text(encoding="utf-8"))
            record = lock["dependencies"]["official-hello"]
            self.assertEqual(record["source"], "registry")
            self.assertTrue(record["approved"])

    def test_direct_url_checksum_fragment_is_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = write_package(root, "checksum-hello")
            archive = publish_package(package, root / "dist")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            with serve_directory(root / "dist") as base:
                url = f"{base}/{archive.name}"
                resolved = resolve_package(f"{url}#sha256={digest}")
                self.assertEqual(resolved.archive_sha256, digest)
                with self.assertRaises(PackageError):
                    resolve_package(f"{url}#sha256={'0' * 64}")

    def test_package_info_reads_registry_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root / "registry.json"
            registry.write_text(
                json.dumps({
                    "packages": {
                        "demo": {
                            "description": "demo package",
                            "latest": "1.0.0",
                            "versions": {
                                "0.9.0": {"archive": "https://example.com/old.zip"},
                                "1.0.0": {
                                    "archive": "https://example.com/demo.zip",
                                    "sha256": "abc123",
                                },
                            },
                        }
                    }
                }),
                encoding="utf-8",
            )
            details = package_info("demo", registry.as_uri())
            self.assertEqual(details["name"], "demo")
            self.assertEqual(details["latest"], "1.0.0")
            self.assertEqual(details["source"], "community")
            self.assertFalse(details["approved"])
            self.assertEqual([release["version"] for release in details["versions"]], ["0.9.0", "1.0.0"])
            self.assertEqual(details["versions"][1]["sha256"], "abc123")

            with self.assertRaises(PackageError):
                package_info("missing", registry.as_uri())

    def test_list_installed_reports_manifest_and_lock_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = write_project(root)
            package = write_package(root, "hello-url")
            installed = add_package(project, str(package))
            packages = list_installed(project)
            self.assertEqual(len(packages), 1)
            self.assertEqual(packages[0]["name"], installed["name"])
            self.assertEqual(packages[0]["source"], "local")
            self.assertTrue(packages[0]["installed"])


if __name__ == "__main__":
    unittest.main()
