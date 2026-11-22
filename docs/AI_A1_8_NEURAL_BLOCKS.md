# A1.8 — Neural-Network Building Blocks

Status: implemented; cross-platform CI validation is pending.

## Differentiable operations

- Elementwise ReLU, sigmoid, and tanh.
- Dense linear layer: `ai.linear(inputs, weights, bias)` computes matrix multiplication followed by broadcast bias addition.
- Differentiable mean reduction: `ai.mean_tensor(tensor)`.
- Mean squared error: `ai.mse_loss(prediction, target)`; prediction and target shapes must match.

All operations compose with the A1.6 reverse-mode graph and A1.7 optimizers. A typical flow creates trainable weights, calculates a prediction and loss, calls `ai.backward(loss)`, then updates the weights with an optimizer.

## Boundaries

CPU-only, rank 1/rank 2 tensor runtime. No sequential model container, dataset batching helper, GPU backend, or automatic optimizer registration.
