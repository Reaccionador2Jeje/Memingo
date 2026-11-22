"""Small, dependency-free tensor primitives for Memingo's AI runtime.

The initial engine deliberately supports rank-1 vectors and rank-2 matrices.
It is a deterministic CPU foundation, not yet an autograd or GPU backend.
"""
from __future__ import annotations

import math
import random


class TensorError(ValueError):
    """Raised when tensor values or dimensions are invalid."""


def _inspect(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TensorError("tensor values must be finite numbers")
    number = float(value)
    if not math.isfinite(number):
        raise TensorError("tensor values must be finite numbers")
    return number


def _normalize(data):
    if not isinstance(data, (list, tuple)) or not data:
        raise TensorError("tensor data must be a non-empty list")
    if isinstance(data[0], (list, tuple)):
        rows = [_normalize(row) for row in data]
        width = len(rows[0][1])
        if any(shape != (width,) for shape, _ in rows):
            raise TensorError("tensor rows must have identical dimensions")
        return (len(rows), width), [row for _, row in rows]
    if any(isinstance(item, (list, tuple)) for item in data):
        raise TensorError("tensor dimensions must be rectangular")
    return (len(data),), [_inspect(item) for item in data]


class Tensor:
    """A rank-1 or rank-2 dense tensor backed by Python floats."""

    def __init__(self, data):
        self.shape, normalized = _normalize(data)
        self._data = normalized

    @property
    def ndim(self):
        return len(self.shape)

    def to_list(self):
        if self.ndim == 1:
            return list(self._data)
        return [list(row) for row in self._data]

    def transpose(self):
        if self.ndim != 2:
            raise TensorError("transpose expects a rank-2 matrix")
        return Tensor([[self._data[row][col] for row in range(self.shape[0])]
                       for col in range(self.shape[1])])

    def add(self, other):
        other = as_tensor(other)
        if self.shape != other.shape:
            raise TensorError(f"add shape mismatch: {self.shape} vs {other.shape}")
        if self.ndim == 1:
            return Tensor([a + b for a, b in zip(self._data, other._data)])
        return Tensor([[a + b for a, b in zip(arow, brow)]
                       for arow, brow in zip(self._data, other._data)])

    def scale(self, factor):
        factor = _inspect(factor)
        if self.ndim == 1:
            return Tensor([value * factor for value in self._data])
        return Tensor([[value * factor for value in row] for row in self._data])

    def sum(self):
        if self.ndim == 1:
            return sum(self._data)
        return sum(sum(row) for row in self._data)

    def softmax(self):
        """Numerically stable softmax over the last axis."""
        def normalize_row(row):
            peak = max(row)
            exps = [math.exp(value - peak) for value in row]
            total = sum(exps)
            return [value / total for value in exps]
        if self.ndim == 1:
            return Tensor(normalize_row(self._data))
        return Tensor([normalize_row(row) for row in self._data])


def as_tensor(value):
    return value if isinstance(value, Tensor) else Tensor(value)


def tensor(data):
    return Tensor(data)


def shape(value):
    return list(as_tensor(value).shape)


def to_list(value):
    return as_tensor(value).to_list()


def transpose(value):
    return as_tensor(value).transpose()


def add(left, right):
    return as_tensor(left).add(right)


def scale(value, factor):
    return as_tensor(value).scale(factor)


def sum_values(value):
    return as_tensor(value).sum()


def softmax(value):
    return as_tensor(value).softmax()


def matmul(left, right):
    """Multiply two rank-2 matrices using a straightforward CPU kernel."""
    a, b = as_tensor(left), as_tensor(right)
    if a.ndim != 2 or b.ndim != 2:
        raise TensorError("matmul expects two rank-2 matrices")
    rows, inner = a.shape
    other_inner, cols = b.shape
    if inner != other_inner:
        raise TensorError(f"matmul shape mismatch: {a.shape} x {b.shape}")
    result = []
    for row in range(rows):
        output_row = []
        for col in range(cols):
            output_row.append(sum(a._data[row][k] * b._data[k][col]
                                  for k in range(inner)))
        result.append(output_row)
    return Tensor(result)


def random_tensor(dimensions, seed=None, low=-0.1, high=0.1):
    """Create a reproducible rank-1 or rank-2 tensor with uniform values."""
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) not in (1, 2):
        raise TensorError("dimensions must contain one or two positive integers")
    if any(isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 4096
           for size in dimensions):
        raise TensorError("tensor dimensions must be integers between 1 and 4096")
    low, high = _inspect(low), _inspect(high)
    if low > high:
        raise TensorError("low must not be greater than high")
    rng = random.Random(seed)
    if len(dimensions) == 1:
        return Tensor([rng.uniform(low, high) for _ in range(dimensions[0])])
    rows, cols = dimensions
    return Tensor([[rng.uniform(low, high) for _ in range(cols)] for _ in range(rows)])
