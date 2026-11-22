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
