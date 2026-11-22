"""Versioned model + optimizer checkpoints for resumable CPU training."""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path

from . import nn, tensor as ops

CHECKPOINT_FORMAT = "memingo.training_checkpoint"
CHECKPOINT_VERSION = 1
MAX_CHECKPOINT_BYTES = 32 * 1024 * 1024


def _path(path, project_directory):
    if not isinstance(path, str) or not path.strip():
        raise ops.TensorError("checkpoint path must be a non-empty string")
    root = Path(project_directory).resolve()
    target = (root / path).resolve()
    if target != root and root not in target.parents:
        raise ops.TensorError("checkpoint path must stay inside the project directory")
    return target


def _optimizer_payload(optimizer, model):
    if not isinstance(optimizer, ops.Optimizer):
        raise ops.TensorError("checkpoint expects an optimizer created by ai.sgd or ai.adam")
    params = model.parameters()
    if optimizer.parameters != params:
        raise ops.TensorError("optimizer parameters must match model parameters in order")
    common = {
        "learning_rate": optimizer.learning_rate,
        "parameter_shapes": [list(parameter.shape) for parameter in params],
    }
    if isinstance(optimizer, ops.AdamOptimizer):
        common.update({
            "type": "adam", "beta1": optimizer.beta1, "beta2": optimizer.beta2,
            "epsilon": optimizer.epsilon, "step": optimizer._step,
            "first": [list(optimizer._first[id(parameter)]) for parameter in params],
            "second": [list(optimizer._second[id(parameter)]) for parameter in params],
        })
    elif isinstance(optimizer, ops.SGDOptimizer):
        common["type"] = "sgd"
    else:
        raise ops.TensorError("unsupported optimizer type for checkpoint")
    return common


def save_checkpoint(model, optimizer, path, project_directory="."):
    """Atomically save model weights and optimizer state for resume-training."""
    if not isinstance(model, nn.Sequential):
        raise ops.TensorError("save_checkpoint expects a model created by ai.sequential")
    target = _path(path, project_directory)
    optimizer_state = _optimizer_payload(optimizer, model)
    try:
        with tempfile.TemporaryDirectory(dir=str(Path(project_directory).resolve())) as directory:
            model_file = Path(directory) / "brain.mgoai"
            nn.save_brain(model, str(model_file), directory)
            model_payload = json.loads(model_file.read_text(encoding="utf-8"))
    except OSError as error:
        raise ops.TensorError(f"could not prepare checkpoint: {error}") from error
    payload = {
        "format": CHECKPOINT_FORMAT, "version": CHECKPOINT_VERSION,
        "model": model_payload, "optimizer": optimizer_state,
    }
    encoded = json.dumps(payload, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_CHECKPOINT_BYTES:
        raise ops.TensorError("checkpoint exceeds the 32 MB limit")
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(target.parent),
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temporary = stream.name
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    except OSError as error:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        raise ops.TensorError(f"could not save checkpoint: {error}") from error
    return str(target)


def load_checkpoint(path, project_directory="."):
    """Load a validated checkpoint and return {model, optimizer}."""
    target = _path(path, project_directory)
    try:
        if target.stat().st_size > MAX_CHECKPOINT_BYTES:
            raise ops.TensorError("checkpoint exceeds the 32 MB limit")
        payload = json.loads(target.read_text(encoding="utf-8"))
    except ops.TensorError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ops.TensorError(f"could not load checkpoint: {error}") from error
    if not isinstance(payload, dict) or payload.get("format") != CHECKPOINT_FORMAT or payload.get("version") != CHECKPOINT_VERSION:
        raise ops.TensorError("unsupported or invalid Memingo checkpoint")
    model_payload, state = payload.get("model"), payload.get("optimizer")
    if not isinstance(model_payload, dict) or not isinstance(state, dict):
        raise ops.TensorError("checkpoint model or optimizer state is invalid")
    # Reuse the model loader's full shape, activation, and finite-value validation.
    try:
        with tempfile.TemporaryDirectory(dir=str(Path(project_directory).resolve())) as directory:
            model_file = Path(directory) / "brain.mgoai"
            model_file.write_text(json.dumps(model_payload, allow_nan=False), encoding="utf-8")
            model = nn.load_brain(str(model_file), directory)
    except ops.TensorError:
        raise
    except (OSError, ValueError) as error:
        raise ops.TensorError(f"could not restore checkpoint model: {error}") from error
    params = model.parameters()
    shapes = state.get("parameter_shapes")
    if shapes != [list(parameter.shape) for parameter in params]:
        raise ops.TensorError("checkpoint optimizer parameter shapes do not match model")
    kind = state.get("type")
    learning_rate = state.get("learning_rate")
    if kind == "sgd":
        optimizer = ops.sgd(params, learning_rate)
    elif kind == "adam":
        optimizer = ops.adam(
            params, learning_rate, state.get("beta1"), state.get("beta2"), state.get("epsilon")
        )
        step = state.get("step")
        first, second = state.get("first"), state.get("second")
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise ops.TensorError("checkpoint Adam step must be a non-negative integer")
        if not isinstance(first, list) or not isinstance(second, list) or len(first) != len(params) or len(second) != len(params):
            raise ops.TensorError("checkpoint Adam moments are invalid")
        validated_first, validated_second = {}, {}
        for index, parameter in enumerate(params):
            if not isinstance(first[index], list) or not isinstance(second[index], list) or len(first[index]) != parameter.size or len(second[index]) != parameter.size:
                raise ops.TensorError("checkpoint Adam moment shape mismatch")
            validated_first[id(parameter)] = [ops._inspect(value) for value in first[index]]
            validated_second[id(parameter)] = [ops._inspect(value) for value in second[index]]
        optimizer._step = step
        optimizer._first = validated_first
        optimizer._second = validated_second
    else:
        raise ops.TensorError("checkpoint optimizer type must be sgd or adam")
    return {"model": model, "optimizer": optimizer}
