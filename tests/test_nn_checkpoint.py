import json

import pytest

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


def test_adam_checkpoint_restores_moments_and_resumes_identically(tmp_path):
    model = _model()
    optimizer = ops.adam(model.parameters(), 0.03, 0.8, 0.95, 1e-7)
    _step(model, optimizer)
    path = checkpoint.save_checkpoint(model, optimizer, "resume.mgochk", tmp_path)

    restored = checkpoint.load_checkpoint("resume.mgochk", tmp_path)
    assert restored["optimizer"]._step == optimizer._step
    assert restored["optimizer"].beta1 == optimizer.beta1
    assert restored["optimizer"]._first == {
        id(parameter): optimizer._first[id(original)]
        for parameter, original in zip(restored["model"].parameters(), model.parameters())
    }

    _step(model, optimizer)
    _step(restored["model"], restored["optimizer"])
    for expected, actual in zip(model.parameters(), restored["model"].parameters()):
        assert ops._flat(expected._data) == pytest.approx(ops._flat(actual._data))


def test_sgd_checkpoint_round_trip(tmp_path):
    model = _model()
    optimizer = ops.sgd(model.parameters(), 0.05)
    _step(model, optimizer)
    checkpoint.save_checkpoint(model, optimizer, "sgd.mgochk", tmp_path)
    restored = checkpoint.load_checkpoint("sgd.mgochk", tmp_path)
    assert restored["optimizer"].learning_rate == 0.05
    for expected, actual in zip(model.parameters(), restored["model"].parameters()):
        assert ops.to_list(expected) == pytest.approx(ops.to_list(actual))


def test_checkpoint_rejects_path_escape_and_bad_format(tmp_path):
    model = _model()
    optimizer = ops.adam(model.parameters())
    with pytest.raises(ops.TensorError, match="inside the project"):
        checkpoint.save_checkpoint(model, optimizer, "../escape.mgochk", tmp_path)
    bad = tmp_path / "bad.mgochk"
    bad.write_text(json.dumps({"format": "wrong", "version": 1}))
    with pytest.raises(ops.TensorError, match="unsupported or invalid"):
        checkpoint.load_checkpoint("bad.mgochk", tmp_path)
