# A1.5 — Tensor Runtime & Performance

Status: implementation in progress on `feat/neural-tensor-foundation`.

## Goal

Turn the initial rank-1/rank-2 tensor helpers into a bounded, predictable CPU
runtime that can safely support later autograd and Transformer work. This stage
does not implement automatic differentiation or a Transformer.

## Runtime contract

- Backend: pure Python CPU; no mandatory third-party numerical dependency.
- Dtypes: finite Python floating-point values, normalized to `float`.
- Supported ranks: vectors (rank 1) and rectangular matrices (rank 2).
- Maximum dimension: 4,096.
- Maximum tensor size: 1,000,000 elements.
- Operations return new tensors; the initial API does not expose mutable storage.
- Invalid shapes, indices, non-finite values, overflowed results, and malformed
  serialized data raise `TensorError`.

## A1.5 feature set

### Elementwise operations and broadcasting

`ai.add(a, b)` and `ai.multiply(a, b)` support trailing-dimension
broadcasting across rank-1 and rank-2 inputs. A pair of dimensions is compatible
when they are equal or either dimension is one. The computed output shape is
checked against the element limit before allocation.

Examples:

- matrix `[2, 3]` plus vector `[3]` -> matrix `[2, 3]`
- matrix `[2, 1]` plus vector `[3]` -> matrix `[2, 3]`
- incompatible dimensions -> `TensorError`

### Reductions

- `ai.sum(tensor)`
- `ai.mean(tensor)`
- `ai.min(tensor)`
- `ai.max(tensor)`

These reduce all elements to one scalar. Summation uses `math.fsum` for
improved floating-point accumulation.

### Indexing and slicing

- `ai.get(tensor, integer)` reads a vector element or a matrix row.
- `ai.get(matrix, [row, column])` reads a matrix scalar.
- Negative indices count from the end.
- `ai.slice(tensor, axis, start, stop, step)` returns a non-empty slice.

Slices are independent copies in this release. Shared-storage views and
strided storage are deliberately deferred rather than being simulated.

### Serialization

`ai.serialize(tensor)` emits deterministic JSON with format identifier
`memingo.tensor`, version `1`, explicit shape, and data.
`ai.deserialize(text)` validates the format, version, shape, numeric values,
and runtime limits before constructing a tensor. Serialized input is limited
to 32 MB.

### CPU matrix multiplication

The rank-2 matrix multiplication kernel transposes the right-hand matrix before
computing dot products, improving access locality in the current list-backed
representation. Dot products use `math.fsum`; outputs are checked for finite
values.

## Public Memingo API

```mgo
vibe matrix = ai.tensor([[1, 2], [3, 4]])
vibe shifted = ai.add(matrix, [10, 20])
spill ai.to_list(shifted)

spill ai.mean(matrix)
spill ai.get(matrix, [1, 0])
spill ai.to_list(ai.slice(matrix, 1, 0, 1))

vibe saved = ai.serialize(matrix)
vibe restored = ai.deserialize(saved)
spill ai.to_list(restored)
```

## Explicit non-goals

A1.5 does not include arbitrary-rank tensors, shared-memory tensor views,
mutable indexing, autograd, GPU execution, native SIMD kernels, batch matmul,
or Transformer layers. Those features require separate designs and tests.

## Acceptance criteria

- Existing tensor APIs remain backwards compatible.
- Broadcasting and shape errors are covered by unit tests.
- Reductions, indexing, slicing, and serialization have deterministic tests.
- Serialization round-trips preserve shape and values.
- Resource limits are checked before large output allocations.
- The complete existing cross-platform CI suite remains green.
