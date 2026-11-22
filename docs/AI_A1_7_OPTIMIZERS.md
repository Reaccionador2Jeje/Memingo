# A1.7 — Native Tensor Optimizers

Status: implemented; cross-platform CI validation is pending.

## API

- `ai.sgd(parameters, learning_rate=0.01)` creates SGD.
- `ai.adam(parameters, learning_rate=0.001, beta1=0.9, beta2=0.999, epsilon=1e-8)` creates Adam.
- `ai.step(optimizer)` performs one update.
- `ai.zero_grad(optimizer)` clears parameter gradients.

## Contract

Optimizers accept a non-empty list of unique tensors with `requires_grad`
enabled. Parameter updates are validated for finite values before any parameter
storage is changed. Adam keeps first- and second-moment state in memory.

## Boundaries

CPU-only, dense rank-1/rank-2 tensors. Optimizer state is not serialized, and
there is no scheduler, weight decay, clipping, distributed training, or GPU backend.
