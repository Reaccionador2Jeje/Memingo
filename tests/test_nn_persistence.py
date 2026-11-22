"""A2 sequential model persistence tests."""
import json
import tempfile
import unittest
from pathlib import Path

from memingo.nn import dense, sequential, save_brain, load_brain
from memingo.tensor import TensorError, to_list


class BrainPersistenceTests(unittest.TestCase):
    def make_model(self):
        return sequential([
            dense(2, 3, "tanh", seed=31),
            dense(3, 1, "sigmoid", seed=32),
        ])

    def test_save_load_preserves_prediction_and_architecture(self):
        model = self.make_model()
        sample = [[0.25, -0.75], [1.0, 0.5]]
        before = to_list(model.forward(sample))
        with tempfile.TemporaryDirectory() as directory:
            saved = save_brain(model, "models/brain.mgoai", directory)
            restored = load_brain("models/brain.mgoai", directory)
            self.assertTrue(Path(saved).is_file())
            self.assertEqual([layer.activation for layer in restored.layers],
                             [layer.activation for layer in model.layers])
            self.assertEqual([layer.in_features for layer in restored.layers],
                             [layer.in_features for layer in model.layers])
            self.assertEqual(to_list(restored.forward(sample)), before)

    def test_concurrent_saves_leave_a_valid_brain(self):
        from concurrent.futures import ThreadPoolExecutor
        first = self.make_model()
        second = sequential([
            dense(2, 3, "relu", seed=41),
            dense(3, 1, "linear", seed=42),
        ])
        with tempfile.TemporaryDirectory() as directory:
            def save(model):
                return save_brain(model, "shared.mgoai", directory)
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(save, (first, second)))
            self.assertEqual(len(set(results)), 1)
            restored = load_brain("shared.mgoai", directory)
            self.assertEqual(len(restored.layers), 2)
            self.assertEqual(restored.in_features, 2)
            self.assertEqual(restored.out_features, 1)
            self.assertEqual(len(restored.parameters()), 4)

    def test_memingo_script_save_load_api(self):
        from memingo.interpreter import execute
        with tempfile.TemporaryDirectory() as directory:
            source = '''
vibe first = ai.dense(2, 3, "tanh", 31)
vibe last = ai.dense(3, 1, "sigmoid", 32)
vibe brain = ai.sequential([first, last])
ai.save_brain(brain, "saved.mgoai")
vibe restored = ai.load_brain("saved.mgoai")
spill ai.shape(ai.forward(restored, [[1, 0]]))
'''
            self.assertEqual(execute(source, project_directory=directory), ["[1, 1]"])

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(TensorError):
                save_brain(self.make_model(), "../outside.mgoai", directory)
            with self.assertRaises(TensorError):
                load_brain("../outside.mgoai", directory)

    def test_rejects_wrong_format_and_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.mgoai"
            path.write_text(json.dumps({
                "format": "memingo.sequential", "version": 77,
                "layers": [],
            }), encoding="utf-8")
            with self.assertRaises(TensorError):
                load_brain("bad.mgoai", directory)

    def test_rejects_corrupt_parameter_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.mgoai"
            path.write_text(json.dumps({
                "format": "memingo.sequential", "version": 1,
                "layers": [{
                    "in_features": 2, "out_features": 1,
                    "activation": "linear", "weights": [[0.1, 0.2]],
                    "bias": [0.0],
                }],
            }), encoding="utf-8")
            with self.assertRaises(TensorError):
                load_brain("bad.mgoai", directory)


if __name__ == "__main__":
    unittest.main()
