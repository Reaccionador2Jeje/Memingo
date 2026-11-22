import json
import unittest

from memingo import checkpoint, nn, tensor as ops


def _model():
    return nn.sequential([
        nn.dense(2, 3, "tanh", seed=10),
        nn.dense(3, 1, "sigmoid", seed=11),
    ])


def _step(model, optimizer):
    optimizer.zero_grad()
    loss = ops.mse_loss(model.forward([[0.0, 1.0], [1.0, 0.0]]), [[1.0], [0.0]])
    ops.backward(loss)
    optimizer.step()


class NNCheckpointTests(unittest.TestCase):
    def test_adam_checkpoint_restores_moments_and_resumes_identically(self):
        with self.subTest("checkpoint continuation"):
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as directory:
                project = Path(directory)
                model = _model()
                optimizer = ops.adam(model.parameters(), 0.03, 0.8, 0.95, 1e-7)
                _step(model, optimizer)
                checkpoint.save_checkpoint(model, optimizer, "resume.mgochk", project)

                restored = checkpoint.load_checkpoint("resume.mgochk", project)
                self.assertEqual(restored["optimizer"]._step, optimizer._step)
                self.assertEqual(restored["optimizer"].beta1, optimizer.beta1)
                self.assertEqual(
                    restored["optimizer"]._first,
                    {
                        id(parameter): optimizer._first[id(original)]
                        for parameter, original in zip(
                            restored["model"].parameters(), model.parameters()
                        )
                    },
                )

                _step(model, optimizer)
                _step(restored["model"], restored["optimizer"])
                for expected, actual in zip(
                    model.parameters(), restored["model"].parameters()
                ):
                    for left, right in zip(ops._flat(expected._data), ops._flat(actual._data)):
                        self.assertAlmostEqual(left, right, places=12)

    def test_sgd_checkpoint_round_trip(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            model = _model()
            optimizer = ops.sgd(model.parameters(), 0.05)
            _step(model, optimizer)
            checkpoint.save_checkpoint(model, optimizer, "sgd.mgochk", project)
            restored = checkpoint.load_checkpoint("sgd.mgochk", project)
            self.assertEqual(restored["optimizer"].learning_rate, 0.05)
            for expected, actual in zip(
                model.parameters(), restored["model"].parameters()
            ):
                for left, right in zip(ops._flat(ops.to_list(expected)), ops._flat(ops.to_list(actual))):
                    self.assertAlmostEqual(left, right, places=12)

    def test_checkpoint_rejects_path_escape_and_bad_format(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            model = _model()
            optimizer = ops.adam(model.parameters())
            with self.assertRaisesRegex(ops.TensorError, "inside the project"):
                checkpoint.save_checkpoint(model, optimizer, "../escape.mgochk", project)
            bad = project / "bad.mgochk"
            bad.write_text(json.dumps({"format": "wrong", "version": 1}))
            with self.assertRaisesRegex(ops.TensorError, "unsupported or invalid"):
                checkpoint.load_checkpoint("bad.mgochk", project)


if __name__ == "__main__":
    unittest.main()
