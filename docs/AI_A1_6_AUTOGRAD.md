# A1.6 — Reverse-Mode Automatic Differentiation

Status: implemented on `feat/neural-tensor-foundation`.

## Goal

Add reverse-mode autodiff to the bounded rank-1/rank-2 CPU tensor runtime as a foundation for native optimizers and neural-network layers.

## API

- `ai.tensor(data, requires_grad?)` optionally records gradients.
- `ai.sum_tensor(tensor)` creates a one-element differentiable loss tensor.
- `ai.backward(loss, gradient?)` traverses the graph in reverse.
- `ai.grad(tensor)` returns the gradient in the original shape, or null before backward.

## Differentiable operations

Broadcasted addition, broadcasted elementwise multiplication, scalar scaling, matrix multiplication, transpose, stable softmax, and sum reduction. Broadcast gradients are accumulated back into each source tensor's original shape.

## Graph semantics

Each operation records differentiable parents and a local backward rule. Backward builds a topological order, clears gradients for nodes in that graph, seeds the output, then accumulates contributions in reverse order. A one-element tensor defaults to gradient 1; non-scalar outputs require an explicit gradient with matching element count.

## Boundaries

CPU-only, rank 1/rank 2, first-order gradients only. No optimizers, GPU kernels, higher-order differentiation, clipping, or persistent graph storage.
