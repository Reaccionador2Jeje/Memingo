import json
import tempfile
import unittest
from pathlib import Path

from memingo import ai, nn, studio


class AIStudioTests(unittest.TestCase):
    def test_dataset_round_trip_and_summary(self):
        data = ai.dataset([[0, 1], [1, 0]], [[1], [0]])
        with tempfile.TemporaryDirectory() as directory:
            saved = studio.save_dataset(data, "datasets/sample.mgodata", directory)
            restored = studio.load_dataset("datasets/sample.mgodata", directory)
            self.assertEqual(Path(saved).name, "sample.mgodata")
            self.assertEqual(restored.inputs, data.inputs)
            self.assertEqual(restored.outputs, data.outputs)
            self.assertEqual(studio.dataset_summary(restored)["input_shape"], [2, 2])

    def test_dataset_rejects_invalid_format_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.mgodata"
            bad.write_text(json.dumps({"format": "wrong", "version": 1}))
            with self.assertRaisesRegex(ai.AIError, "unsupported or invalid"):
                studio.load_dataset("bad.mgodata", directory)
            with self.assertRaisesRegex(ai.AIError, "inside the project"):
                studio.save_dataset(ai.dataset([[1]], [[0]]), "../escape.mgodata", directory)

    def test_workspace_indexes_models_and_datasets_without_running_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = nn.sequential([nn.dense(2, 3, seed=1), nn.dense(3, 1, activation="sigmoid", seed=2)])
            nn.save_brain(model, "models/demo.mgoai", root)
            data = ai.dataset([[0, 1], [1, 0]], [[1], [0]])
            studio.save_dataset(data, "datasets/demo.mgodata", root)
            (root / "broken.mgoai").write_text("{broken")
            (root / "ignored").mkdir()
            (root / "ignored" / "not-indexed.mgodata").write_text("{}")

            result = studio.workspace(root)
            self.assertEqual(result["counts"]["models"], 2)
            self.assertEqual(result["counts"]["datasets"], 1)
            valid = next(item for item in result["models"] if item["name"] == "demo.mgoai")
            invalid = next(item for item in result["models"] if item["name"] == "broken.mgoai")
            self.assertTrue(valid["valid"])
            self.assertFalse(invalid["valid"])
            self.assertEqual(result["datasets"][0]["summary"]["samples"], 2)

    def test_interpreter_dataset_studio_api(self):
        from memingo.interpreter import execute
        source = '''
vibe data = ai.dataset([[0], [1]], [[1], [0]])
ai.save_dataset(data, "data/sample.mgodata")
vibe loaded = ai.load_dataset("data/sample.mgodata")
spill ai.dataset_summary(loaded).samples
'''
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(execute(source, project_directory=directory), ["2"])


if __name__ == "__main__":
    unittest.main()
