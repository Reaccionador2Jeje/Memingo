"""Sequential dense neural models for Memingo's native CPU tensor engine.

Meme-sized API, real autograd underneath.
"""

from . import tensor as ops


class DenseLayer:
    """A trainable dense layer with an optional meme-approved activation."""

    def __init__(self, in_features, out_features, activation="relu", seed=None):
        for label, value in (("in_features", in_features), ("out_features", out_features)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ops.TensorError(f"dense {label} must be a positive integer")
            if value > ops.MAX_TENSOR_DIMENSION:
                raise ops.TensorError(f"dense {label} exceeds the tensor dimension limit")
        if activation not in ("relu", "sigmoid", "tanh", "linear"):
            raise ops.TensorError("dense activation must be relu, sigmoid, tanh, or linear")
        self.in_features = in_features
        self.out_features = out_features
        self.activation = activation
        self.weights = ops.random_tensor([in_features, out_features], seed=seed, low=-0.1, high=0.1)
        self.weights.requires_grad = True
        self.bias = ops.tensor([0.0] * out_features, requires_grad=True)

    def __call__(self, values):
        return self.forward(values)

    def forward(self, values):
        data = ops.as_tensor(values)
        if len(data.shape) != 2 or data.shape[1] != self.in_features:
            raise ops.TensorError(
                f"dense expected rank-2 input with {self.in_features} features"
            )
        output = ops.linear(data, self.weights, self.bias)
        if self.activation == "relu":
            return ops.relu(output)
        if self.activation == "sigmoid":
            return ops.sigmoid(output)
        if self.activation == "tanh":
            return ops.tanh(output)
        return output

    def parameters(self):
        return [self.weights, self.bias]


class Sequential:
    """A validated ordered list of dense layers."""

    def __init__(self, layers):
        if not isinstance(layers, (list, tuple)) or not layers:
            raise ops.TensorError("sequential expects a non-empty list of dense layers")
        if any(not isinstance(layer, DenseLayer) for layer in layers):
            raise ops.TensorError("sequential currently accepts dense layers only")
        for previous, current in zip(layers, layers[1:]):
            if previous.out_features != current.in_features:
                raise ops.TensorError("sequential layer sizes do not connect")
        self.layers = list(layers)
        self.in_features = self.layers[0].in_features
        self.out_features = self.layers[-1].out_features

    def forward(self, values):
        result = ops.as_tensor(values)
        if len(result.shape) != 2 or result.shape[1] != self.in_features:
            raise ops.TensorError(
                f"sequential expected rank-2 input with {self.in_features} features"
            )
        for layer in self.layers:
            result = layer.forward(result)
        return result

    def parameters(self):
        return [parameter for layer in self.layers for parameter in layer.parameters()]


def dense(in_features, out_features, activation="relu", seed=None):
    """Create a trainable dense layer."""
    return DenseLayer(in_features, out_features, activation=activation, seed=seed)


def sequential(layers):
    """Build a sequential model from dense layers."""
    return Sequential(layers)


def parameters(model):
    if not isinstance(model, Sequential):
        raise ops.TensorError("parameters expects a model created by ai.sequential")
    return model.parameters()


def forward(model, inputs):
    if not isinstance(model, Sequential):
        raise ops.TensorError("forward expects a model created by ai.sequential")
    return model.forward(inputs)


def train_loop(model, inputs, targets, epochs=100, learning_rate=0.01, optimizer="adam"):
    """Full-batch supervised training with native reverse-mode autograd."""
    if not isinstance(model, Sequential):
        raise ops.TensorError("train_loop expects a model created by ai.sequential")
    if isinstance(epochs, bool) or not isinstance(epochs, int) or not 1 <= epochs <= 10000:
        raise ops.TensorError("train_loop epochs must be an integer from 1 to 10000")
    if optimizer not in ("sgd", "adam"):
        raise ops.TensorError("train_loop optimizer must be sgd or adam")
    x, y = ops.as_tensor(inputs), ops.as_tensor(targets)
    if len(x.shape) != 2 or len(y.shape) != 2 or x.shape[0] != y.shape[0]:
        raise ops.TensorError("train_loop expects matching rank-2 input and target batches")
    if x.shape[1] != model.in_features or y.shape[1] != model.out_features:
        raise ops.TensorError("train_loop batch feature sizes do not match the model")
    if x.shape[0] < 1:
        raise ops.TensorError("train_loop requires at least one training sample")
    params = model.parameters()
    trainer = ops.sgd(params, learning_rate) if optimizer == "sgd" else ops.adam(params, learning_rate)
    loss_value = None
    for _ in range(epochs):
        trainer.zero_grad()
        prediction = model.forward(x)
        loss = ops.mse_loss(prediction, y)
        ops.backward(loss)
        trainer.step()
        loss_value = ops.to_list(loss)[0]
    # Report the loss after the final parameter update, not the stale pre-update value.
    final_loss = ops.to_list(ops.mse_loss(model.forward(x), y))[0]
    return {"epochs": epochs, "loss": final_loss, "initial_batch_loss": loss_value, "samples": x.shape[0]}

# A2: bounded, versioned persistence for sequential "meme brains".
MODEL_FORMAT = "memingo.sequential"
MODEL_VERSION = 1
MAX_MODEL_FILE_BYTES = 16 * 1024 * 1024
MAX_MODEL_LAYERS = 128
MAX_MODEL_PARAMETERS = ops.MAX_TENSOR_ELEMENTS


def _model_path(path, project_directory="."):
    from pathlib import Path
    if not isinstance(path, str) or not path.strip():
        raise ops.TensorError("brain path must be a non-empty string")
    root = Path(project_directory).resolve()
    candidate = (root / path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ops.TensorError("brain path must stay inside the project directory")
    return candidate


def save_brain(model, path, project_directory="."):
    """Atomically save a Sequential model as a versioned JSON .mgoai file."""
    import json
    from pathlib import Path
    if not isinstance(model, Sequential):
        raise ops.TensorError("save_brain expects a model created by ai.sequential")
    target = _model_path(path, project_directory)
    layers = []
    parameter_count = 0
    for layer in model.layers:
        weights = ops.to_list(layer.weights)
        bias = ops.to_list(layer.bias)
        parameter_count += layer.in_features * layer.out_features + layer.out_features
        layers.append({
            "in_features": layer.in_features,
            "out_features": layer.out_features,
            "activation": layer.activation,
            "weights": weights,
            "bias": bias,
        })
    if parameter_count > MAX_MODEL_PARAMETERS:
        raise ops.TensorError("brain exceeds the model parameter limit")
    payload = {
        "format": MODEL_FORMAT,
        "version": MODEL_VERSION,
        "name": "MemingoBrain",
        "layers": layers,
    }
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_MODEL_FILE_BYTES:
        raise ops.TensorError("brain file exceeds the 16 MB limit")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.replace(target)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ops.TensorError(f"could not save brain: {error}") from error
    return str(target)


def load_brain(path, project_directory="."):
    """Load and validate a versioned sequential model file."""
    import json
    target = _model_path(path, project_directory)
    try:
        if target.stat().st_size > MAX_MODEL_FILE_BYTES:
            raise ops.TensorError("brain file exceeds the 16 MB limit")
        encoded = target.read_text(encoding="utf-8")
        payload = json.loads(encoded)
    except ops.TensorError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ops.TensorError(f"could not load brain: {error}") from error
    if not isinstance(payload, dict) or payload.get("format") != MODEL_FORMAT or payload.get("version") != MODEL_VERSION:
        raise ops.TensorError("unsupported or invalid Memingo brain file")
    specs = payload.get("layers")
    if not isinstance(specs, list) or not 1 <= len(specs) <= MAX_MODEL_LAYERS:
        raise ops.TensorError("brain layer list is invalid")
    built = []
    total_parameters = 0
    expected_input = None
    for spec in specs:
        if not isinstance(spec, dict):
            raise ops.TensorError("brain layer entry must be an object")
        in_features, out_features = spec.get("in_features"), spec.get("out_features")
        for label, size in (("in_features", in_features), ("out_features", out_features)):
            if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= ops.MAX_TENSOR_DIMENSION:
                raise ops.TensorError(f"brain {label} must be between 1 and 4096")
        if expected_input is not None and in_features != expected_input:
            raise ops.TensorError("brain layer dimensions do not connect")
        expected_input = out_features
        total_parameters += in_features * out_features + out_features
        if total_parameters > MAX_MODEL_PARAMETERS:
            raise ops.TensorError("brain exceeds the model parameter limit")
        activation = spec.get("activation")
        if activation not in ("relu", "sigmoid", "tanh", "linear"):
            raise ops.TensorError("brain layer activation is invalid")
        weights = ops.tensor(spec.get("weights"), requires_grad=True)
        bias = ops.tensor(spec.get("bias"), requires_grad=True)
        if ops.shape(weights) != [in_features, out_features] or ops.shape(bias) != [out_features]:
            raise ops.TensorError("brain parameter dimensions do not match layer configuration")
        layer = DenseLayer(in_features, out_features, activation=activation, seed=0)
        layer.weights, layer.bias = weights, bias
        built.append(layer)
    return Sequential(built)
