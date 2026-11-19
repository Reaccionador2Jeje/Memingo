import tempfile
import unittest
from pathlib import Path

from memingo.ai import AIError, create, dataset, load


class AITest(unittest.TestCase):
    def test_train_predict_evaluate_and_persist(self):
        model = create({"name": "XOR", "layers": [2, 4, 1], "activation": "sigmoid"})
        data = dataset([[0, 0], [0, 1], [1, 0], [1, 1]], [[0], [1], [1], [0]])
        result = model.train(data, {"epochs": 2500, "learning_rate": 0.5, "batch_size": 2})
        self.assertEqual(result["epochs"], 2500)
        self.assertEqual(result["batch_size"], 2)
        self.assertEqual(result["total_epochs"], 2500)
        self.assertGreaterEqual(result["loss"], 0)
        self.assertEqual(len(model.predict([0, 1])), 1)
        self.assertEqual(model.evaluate(data)["samples"], 4)
        with tempfile.TemporaryDirectory() as directory:
            model.save("models/xor.mgoai", directory)
            restored = load("models/xor.mgoai", directory)
            self.assertEqual(restored.layers, [2, 4, 1])
            self.assertEqual(restored.predict([0, 1]), model.predict([0, 1]))

    def test_rejects_invalid_dimensions(self):
        with self.assertRaises(AIError):
            create({"layers": [2]})
        with self.assertRaises(AIError):
            dataset([[1], [1, 2]], [[0], [1]])

    def test_model_path_cannot_escape_project(self):
        model = create({"layers": [1, 1]})
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(AIError):
                model.save("../outside.mgoai", directory)

    def test_memingo_script_api(self):
        from memingo.interpreter import execute
        source = '''
vibe model = ai.create({name: "Tiny", layers: [1, 1], activation: "sigmoid"})
vibe data = ai.dataset([[0], [1]], [[0], [1]])
vibe result = ai.train(model, data, {epochs: 5, learning_rate: 0.2})
spill result.epochs
spill headcount(ai.predict(model, [1]))
'''
        output = execute(source)
        self.assertEqual(output, ["5", "1"])


if __name__ == "__main__":
    unittest.main()
