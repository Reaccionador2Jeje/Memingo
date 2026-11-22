import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memingo.mgoa import _registry_packages, publish_to_mirror


class MgoaPublishingTests(unittest.TestCase):
    def test_approved_and_community_packages_are_merged(self):
        packages, registry_is_approved = _registry_packages({
            "approved": {"packages": {"official": {"latest": "1.0.0"}}},
            "packages": {"community": {"latest": "0.2.0", "approved": False}},
        })
        self.assertFalse(registry_is_approved)
        self.assertTrue(packages["official"]["approved"])
        self.assertFalse(packages["community"]["approved"])

    def test_publish_commits_archive_checksum_and_index_to_pages_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "cool-kit"
            package.mkdir()
            (package / "memingo.toml").write_text(
                '[package]\nname = "cool-kit"\nversion = "1.2.0"\n'
                'entry = "main.mgo"\ndescription = "A cool package"\n',
                encoding="utf-8",
            )
            (package / "main.mgo").write_text('spill "based"\n', encoding="utf-8")
            original_index = {
                "schema": "memingo-approved/v1",
                "approved": {"packages": {"official": {"latest": "1.0.0", "versions": {}}}},
            }
            calls = []
            blob_count = 0

            def fake_api(method, endpoint, token, payload=None):
                nonlocal blob_count
                calls.append((method, endpoint, payload))
                if method == "GET" and "/contents/site/mgoa/index.json" in endpoint:
                    return {
                        "content": base64.b64encode(
                            json.dumps(original_index).encode("utf-8")
                        ).decode("ascii")
                    }
                if method == "GET" and "/git/ref/heads/" in endpoint:
                    return {"object": {"sha": "parent-sha"}}
                if method == "GET" and "/git/commits/parent-sha" in endpoint:
                    return {"tree": {"sha": "base-tree"}}
                if method == "POST" and endpoint.endswith("/git/blobs"):
                    blob_count += 1
                    return {"sha": f"blob-{blob_count}"}
                if method == "POST" and endpoint.endswith("/git/trees"):
                    return {"sha": "new-tree"}
                if method == "POST" and endpoint.endswith("/git/commits"):
                    return {"sha": "new-commit"}
                if method == "PATCH" and "/git/refs/heads/" in endpoint:
                    return {}
                self.fail(f"Unexpected GitHub API call: {method} {endpoint}")

            with patch("memingo.mgoa._github_api_request", side_effect=fake_api):
                result = publish_to_mirror(
                    package,
                    output=root / "dist",
                    token="test-token",
                    repository="owner/repo",
                    branch="main",
                )

            self.assertEqual(result["name"], "cool-kit")
            self.assertEqual(result["version"], "1.2.0")
            self.assertEqual(result["commit"], "new-commit")
            self.assertTrue(result["archive"].is_file())
            tree_call = next(call for call in calls if call[1].endswith("/git/trees"))
            paths = {entry["path"] for entry in tree_call[2]["tree"]}
            self.assertEqual(paths, {
                f"site/mgoa/packages/{result['archive'].name}",
                f"site/mgoa/packages/{result['archive'].name}.sha256",
                "site/mgoa/index.json",
            })
            index_blob_call = [
                call for call in calls
                if call[0] == "POST" and call[1].endswith("/git/blobs")
            ][-1]
            published_index = json.loads(index_blob_call[2]["content"])
            self.assertIn("official", published_index["approved"]["packages"])
            self.assertFalse(published_index["packages"]["cool-kit"]["approved"])
            self.assertEqual(
                published_index["packages"]["cool-kit"]["versions"]["1.2.0"]["sha256"],
                result["sha256"],
            )
            self.assertTrue(any(call[0] == "PATCH" for call in calls))


if __name__ == "__main__":
    unittest.main()
