"""Pure-Python neural-network training engine for Memingo.

The first release intentionally focuses on small dense neural networks. It has
no mandatory third-party dependencies and is suitable for CPU training.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path


class AIError(ValueError):
    pass


class Dataset:
    def __init__(self, inputs, outputs):
        if not isinstance(inputs, list) or not isinstance(outputs, list):
            raise AIError("dataset inputs and outputs must be lists")
        if not inputs or len(inputs) != len(outputs):
            raise AIError("dataset needs equally sized, non-empty inputs and outputs")
        self.inputs = [self._vector(row, "input") for row in inputs]
        self.outputs = [self._vector(row, "output") for row in outputs]
        if len({len(row) for row in self.inputs}) != 1:
            raise AIError("all input rows must have the same width")
        if len({len(row) for row in self.outputs}) != 1:
            raise AIError("all output rows must have the same width")

    @staticmethod
    def _vector(row, label):
        if not isinstance(row, (list, tuple)) or not row:
            raise AIError(f"each {label} row must be a non-empty list")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in row):
            raise AIError(f"{label} values must be finite numbers")
        return [float(value) for value in row]

    def __len__(self):
        return len(self.inputs)


class DenseNetwork:
    FORMAT = "MGOAI"
    VERSION = 1

    def __init__(self, config):
        if not isinstance(config, dict):
            raise AIError("model configuration must be an object")
        self.name = str(config.get("name", "MemingoModel"))
        layers = config.get("layers")
        if layers is None:
            layers = [config.get("inputs", 1), config.get("outputs", 1)]
        if not isinstance(layers, list) or len(layers) < 2:
            raise AIError("layers must contain at least input and output sizes")
        if any(isinstance(n, bool) or not isinstance(n, int) or n < 1 or n > 4096 for n in layers):
            raise AIError("layer sizes must be integers between 1 and 4096")
        if sum(layers) > 8192:
            raise AIError("model is too large for the built-in CPU engine")
        self.layers = list(layers)
        self.activation = config.get("activation", "relu")
        if self.activation not in ("relu", "sigmoid", "tanh"):
            raise AIError("activation must be relu, sigmoid, or tanh")
        self.weights = []
        self.biases = []
        for fan_in, fan_out in zip(self.layers, self.layers[1:]):
            limit = math.sqrt(6 / (fan_in + fan_out))
            self.weights.append([[random.uniform(-limit, limit) for _ in range(fan_in)] for _ in range(fan_out)])
            self.biases.append([0.0 for _ in range(fan_out)])
        self.history = []

    def _activate(self, value):
        if self.activation == "relu":
            return max(0.0, value)
        if self.activation == "tanh":
            return math.tanh(value)
        value = max(-60.0, min(60.0, value))
        return 1.0 / (1.0 + math.exp(-value))

    def _derivative(self, activated):
        if self.activation == "relu":
            return 1.0 if activated > 0 else 0.0
        if self.activation == "tanh":
            return 1.0 - activated * activated
        return activated * (1.0 - activated)

    def _forward(self, inputs):
        if len(inputs) != self.layers[0]:
            raise AIError(f"model expects {self.layers[0]} inputs, got {len(inputs)}")
        activations = [[float(value) for value in inputs]]
        for weights, biases in zip(self.weights, self.biases):
            current = []
            for row, bias in zip(weights, biases):
                current.append(self._activate(sum(w * x for w, x in zip(row, activations[-1])) + bias))
            activations.append(current)
        return activations

    def predict(self, inputs):
        row = Dataset._vector(inputs, "prediction input")
        return self._forward(row)[-1]

    def train(self, dataset, options=None):
        if not isinstance(dataset, Dataset):
            raise AIError("ai.train expects a dataset created with ai.dataset")
        options = options or {}
        if not isinstance(options, dict):
            raise AIError("training options must be an object")
        epochs = options.get("epochs", 100)
        learning_rate = options.get("learning_rate", 0.01)
        batch_size = options.get("batch_size", 1)
        if isinstance(epochs, bool) or not isinstance(epochs, int) or not 1 <= epochs <= 100000:
            raise AIError("epochs must be an integer between 1 and 100000")
        if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)) or not math.isfinite(learning_rate) or not 0 < learning_rate <= 1:
            raise AIError("learning_rate must be greater than 0 and at most 1")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= len(dataset):
            raise AIError("batch_size must be an integer between 1 and the dataset size")
        if len(dataset.inputs[0]) != self.layers[0] or len(dataset.outputs[0]) != self.layers[-1]:
            raise AIError("dataset dimensions do not match model input/output sizes")
        shuffle = options.get("shuffle", True)
        if not isinstance(shuffle, bool):
            raise AIError("shuffle must be based or cringe")

        indices = list(range(len(dataset)))
        for _ in range(epochs):
            if shuffle:
                random.shuffle(indices)
            total_loss = 0.0
            for offset in range(0, len(indices), batch_size):
                batch = indices[offset:offset + batch_size]
                weight_gradients = [
                    [[0.0 for _ in row] for row in layer]
                    for layer in self.weights
                ]
                bias_gradients = [[0.0 for _ in layer] for layer in self.biases]
                for index in batch:
                    activations = self._forward(dataset.inputs[index])
                    expected = dataset.outputs[index]
                    output = activations[-1]
                    deltas = [[0.0] * size for size in self.layers[1:]]
                    last = len(deltas) - 1
                    deltas[last] = [
                        (actual - target) * self._derivative(actual)
                        for actual, target in zip(output, expected)
                    ]
                    for layer_index in range(last - 1, -1, -1):
                        deltas[layer_index] = [
                            sum(
                                self.weights[layer_index + 1][next_index][neuron]
                                * deltas[layer_index + 1][next_index]
                                for next_index in range(len(deltas[layer_index + 1]))
                            ) * self._derivative(activations[layer_index + 1][neuron])
                            for neuron in range(self.layers[layer_index + 1])
                        ]
                    for layer_index, layer_deltas in enumerate(deltas):
                        previous = activations[layer_index]
                        for neuron, delta in enumerate(layer_deltas):
                            bias_gradients[layer_index][neuron] += delta
                            for weight_index in range(len(previous)):
                                weight_gradients[layer_index][neuron][weight_index] += delta * previous[weight_index]
                    total_loss += sum(
                        (actual - target) ** 2 for actual, target in zip(output, expected)
                    ) / len(output)
                scale = float(learning_rate) / len(batch)
                for layer_index, layer in enumerate(self.weights):
                    for neuron, row in enumerate(layer):
                        for weight_index in range(len(row)):
                            row[weight_index] -= scale * weight_gradients[layer_index][neuron][weight_index]
                        self.biases[layer_index][neuron] -= scale * bias_gradients[layer_index][neuron]
            self.history.append({"epoch": len(self.history) + 1, "loss": total_loss / len(dataset)})
        return {
            "epochs": epochs,
            "total_epochs": len(self.history),
            "loss": self.history[-1]["loss"],
            "samples": len(dataset),
            "batch_size": batch_size,
        }

    def evaluate(self, dataset):
        if not isinstance(dataset, Dataset):
            raise AIError("ai.evaluate expects a dataset")
        if len(dataset.inputs[0]) != self.layers[0] or len(dataset.outputs[0]) != self.layers[-1]:
            raise AIError("dataset dimensions do not match model")
        loss = 0.0
        for inputs, expected in zip(dataset.inputs, dataset.outputs):
            actual = self.predict(inputs)
            loss += sum((a - b) ** 2 for a, b in zip(actual, expected)) / len(actual)
        return {"loss": loss / len(dataset), "samples": len(dataset)}

    def save(self, path, project_directory="."):
        target = _safe_path(path, project_directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": self.FORMAT, "version": self.VERSION, "name": self.name,
            "layers": self.layers, "activation": self.activation,
            "weights": self.weights, "biases": self.biases, "history": self.history,
        }
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        temporary.replace(target)
        return str(target)

    @classmethod
    def load(cls, path, project_directory="."):
        target = _safe_path(path, project_directory)
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise AIError(f"could not load model: {error}") from error
        if payload.get("format") != cls.FORMAT or payload.get("version") != cls.VERSION:
            raise AIError("unsupported or invalid MGOAI model file")
        model = cls({"name": payload.get("name"), "layers": payload.get("layers"), "activation": payload.get("activation")})
        weights, biases = payload.get("weights"), payload.get("biases")
        if len(weights) != len(model.weights) or len(biases) != len(model.biases):
            raise AIError("model parameter dimensions are invalid")
        for i, layer in enumerate(weights):
            if len(layer) != len(model.weights[i]) or any(len(row) != len(model.weights[i][0]) for row in layer):
                raise AIError("model weight dimensions are invalid")
        model.weights = weights
        model.biases = biases
        model.history = payload.get("history", [])
        return model


def _safe_path(path, project_directory):
    if not isinstance(path, str) or not path:
        raise AIError("model path must be a non-empty string")
    root = Path(project_directory).resolve()
    candidate = (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise AIError("model path must stay inside the project directory")
    return candidate


def create(config):
    return DenseNetwork(config)


def dataset(inputs, outputs):
    return Dataset(inputs, outputs)


def load(path, project_directory="."):
    return DenseNetwork.load(path, project_directory)
