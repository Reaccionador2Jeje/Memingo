"""Dense CPU tensor runtime for Memingo's AI APIs.

A1.5 extends the initial vector/matrix foundation with broadcasting,
indexing, reductions, bounded serialization, and safer numeric checks.
The runtime remains dependency-free and intentionally rank-1/rank-2.
"""
from __future__ import annotations

import json
import math
import random


MAX_TENSOR_ELEMENTS = 1_000_000
MAX_TENSOR_DIMENSION = 4096
TENSOR_FORMAT = "memingo.tensor"
TENSOR_VERSION = 1


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
        shape = (len(rows), width)
        if any(size > MAX_TENSOR_DIMENSION for size in shape):
            raise TensorError("tensor dimensions cannot exceed 4096")
        if shape[0] * shape[1] > MAX_TENSOR_ELEMENTS:
            raise TensorError("tensor exceeds the 1,000,000 element limit")
        return shape, [row for _, row in rows]
    if any(isinstance(item, (list, tuple)) for item in data):
        raise TensorError("tensor dimensions must be rectangular")
    if len(data) > MAX_TENSOR_DIMENSION:
        raise TensorError("tensor dimensions cannot exceed 4096")
    return (len(data),), [_inspect(item) for item in data]


def _flat(data):
    if data and isinstance(data[0], list):
        return [value for row in data for value in row]
    return list(data)


def _reshape(values, dimensions):
    if len(dimensions) == 1:
        return list(values)
    rows, cols = dimensions
    return [list(values[row * cols:(row + 1) * cols]) for row in range(rows)]


def _coordinates(index, shape):
    if len(shape) == 1:
        if isinstance(index, bool) or not isinstance(index, int):
            raise TensorError("vector index must be an integer")
        if index < 0:
            index += shape[0]
        if not 0 <= index < shape[0]:
            raise TensorError("tensor index out of range")
        return (index,)
    if isinstance(index, int) and not isinstance(index, bool):
        row = index + shape[0] if index < 0 else index
        if not 0 <= row < shape[0]:
            raise TensorError("tensor index out of range")
        return (row,)
    if isinstance(index, (list, tuple)) and len(index) == 2:
        row, col = index
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (row, col)):
            raise TensorError("matrix indices must be integers")
        row = row + shape[0] if row < 0 else row
        col = col + shape[1] if col < 0 else col
        if not 0 <= row < shape[0] or not 0 <= col < shape[1]:
            raise TensorError("tensor index out of range")
        return row, col
    raise TensorError("matrix index must be a row integer or [row, column]")


class Tensor:
    """A rank-1 or rank-2 dense tensor backed by Python floats."""

    def __init__(self, data, requires_grad=False):
        self.shape, normalized = _normalize(data)
        if not isinstance(requires_grad, bool):
            raise TensorError("requires_grad must be a boolean")
        self._data = normalized
        self.requires_grad = requires_grad
        self.grad = None
        self._parents = ()
        self._backward = lambda gradient: ()

    @property
    def ndim(self):
        return len(self.shape)

    @property
    def size(self):
        return math.prod(self.shape)

    def to_list(self):
        if self.ndim == 1:
            return list(self._data)
        return [list(row) for row in self._data]

    def grad_values(self):
        return None if self.grad is None else _reshape(self.grad, self.shape)

    def backward(self, gradient=None):
        if gradient is None:
            if self.size != 1:
                raise TensorError("backward requires an explicit gradient for non-scalar tensors")
            seed = [1.0]
        else:
            seed = [_inspect(value) for value in _flat(as_tensor(gradient)._data)]
            if len(seed) != self.size:
                raise TensorError("backward gradient shape does not match the tensor")
        order, visited = [], set()
        def visit(node):
            if id(node) in visited:
                return
            visited.add(id(node))
            for parent in node._parents:
                visit(parent)
            order.append(node)
        visit(self)
        for node in order:
            node.grad = None
        self.grad = list(seed)
        for node in reversed(order):
            if node.grad is None:
                continue
            for parent, contribution in node._backward(node.grad):
                if len(contribution) != parent.size:
                    raise TensorError("internal autograd gradient shape mismatch")
                if parent.grad is None:
                    parent.grad = [0.0] * parent.size
                for index, value in enumerate(contribution):
                    parent.grad[index] = _inspect(parent.grad[index] + _inspect(value))
        return self.grad_values()

    def transpose(self):
        if self.ndim != 2:
            raise TensorError("transpose expects a rank-2 matrix")
        result = Tensor([[self._data[row][col] for row in range(self.shape[0])]
                         for col in range(self.shape[1])])
        if self.requires_grad:
            result.requires_grad = True
            result._parents = (self,)
            def backward(gradient):
                matrix = _reshape(gradient, result.shape)
                transposed = [[matrix[col][row] for col in range(result.shape[0])]
                              for row in range(result.shape[1])]
                return ((self, _flat(transposed)),)
            result._backward = backward
        return result

    def add(self, other):
        return _elementwise(self, other, lambda a, b: a + b, "add")

    def multiply(self, other):
        return _elementwise(self, other, lambda a, b: a * b, "multiply")

    def scale(self, factor):
        factor = _inspect(factor)
        values = [_inspect(value * factor) for value in _flat(self._data)]
        result = Tensor(_reshape(values, self.shape))
        if self.requires_grad:
            result.requires_grad = True
            result._parents = (self,)
            result._backward = lambda gradient: ((self, [value * factor for value in gradient]),)
        return result

    def sum_tensor(self):
        result = Tensor([self.sum()])
        if self.requires_grad:
            result.requires_grad = True
            result._parents = (self,)
            result._backward = lambda gradient: ((self, [gradient[0]] * self.size),)
        return result

    def sum(self):
        return math.fsum(_flat(self._data))

    def mean(self):
        return self.sum() / self.size

    def min(self):
        return min(_flat(self._data))

    def max(self):
        return max(_flat(self._data))

    def get(self, index):
        coordinates = _coordinates(index, self.shape)
        if self.ndim == 1:
            return self._data[coordinates[0]]
        if len(coordinates) == 1:
            return Tensor(self._data[coordinates[0]])
        return self._data[coordinates[0]][coordinates[1]]

    def slice(self, axis=0, start=None, stop=None, step=1):
        if isinstance(axis, bool) or not isinstance(axis, int) or axis < 0 or axis >= self.ndim:
            raise TensorError("slice axis is out of range")
        if isinstance(step, bool) or not isinstance(step, int) or step == 0:
            raise TensorError("slice step must be a non-zero integer")
        if self.ndim == 1:
            result = self._data[slice(start, stop, step)]
            if not result:
                raise TensorError("tensor slices cannot be empty")
            return Tensor(result)
        if axis == 0:
            result = self._data[slice(start, stop, step)]
            if not result:
                raise TensorError("tensor slices cannot be empty")
            return Tensor(result)
        result = [row[slice(start, stop, step)] for row in self._data]
        if not result or not result[0]:
            raise TensorError("tensor slices cannot be empty")
        return Tensor(result)

    def softmax(self):
        """Numerically stable softmax over the last axis."""
        def normalize_row(row):
            peak = max(row)
            exps = [math.exp(value - peak) for value in row]
            total = math.fsum(exps)
            return [value / total for value in exps]
        data = normalize_row(self._data) if self.ndim == 1 else [normalize_row(row) for row in self._data]
        result = Tensor(data)
        if self.requires_grad:
            result.requires_grad = True
            result._parents = (self,)
            def backward(gradient):
                rows = [result._data] if result.ndim == 1 else result._data
                grad_rows = [gradient] if result.ndim == 1 else _reshape(gradient, result.shape)
                local = []
                for values, grad_row in zip(rows, grad_rows):
                    dot = math.fsum(g * value for g, value in zip(grad_row, values))
                    local.append([value * (g - dot) for g, value in zip(grad_row, values)])
                return ((self, local[0] if self.ndim == 1 else _flat(local)),)
            result._backward = backward
        return result


def _elementwise(left, right, operation, name):
    a, b = as_tensor(left), as_tensor(right)
    rank = max(a.ndim, b.ndim)
    a_shape = (1,) * (rank - a.ndim) + a.shape
    b_shape = (1,) * (rank - b.ndim) + b.shape
    output_shape = []
    for da, db in zip(a_shape, b_shape):
        if da != db and da != 1 and db != 1:
            raise TensorError(f"{name} broadcast mismatch: {a.shape} vs {b.shape}")
        output_shape.append(max(da, db))
    output_shape = tuple(output_shape)
    if math.prod(output_shape) > MAX_TENSOR_ELEMENTS:
        raise TensorError("broadcast result exceeds the 1,000,000 element limit")
    af, bf = _flat(a._data), _flat(b._data)
    a_cols, b_cols = a_shape[-1], b_shape[-1]
    values = []
    a_indices, b_indices = [], []
    if rank == 1:
        for i in range(output_shape[0]):
            ai = 0 if a_shape[0] == 1 else i
            bi = 0 if b_shape[0] == 1 else i
            a_indices.append(ai)
            b_indices.append(bi)
            values.append(_inspect(operation(af[ai], bf[bi])))
    else:
        rows, cols = output_shape
        for row in range(rows):
            for col in range(cols):
                ai = (0 if a_shape[0] == 1 else row) * a_cols + (0 if a_cols == 1 else col)
                bi = (0 if b_shape[0] == 1 else row) * b_cols + (0 if b_cols == 1 else col)
                a_indices.append(ai)
                b_indices.append(bi)
                values.append(_inspect(operation(af[ai], bf[bi])))
    result = Tensor(_reshape(values, output_shape))
    if a.requires_grad or b.requires_grad:
        result.requires_grad = True
        result._parents = tuple(parent for parent in (a, b) if parent.requires_grad)
        def backward(gradient):
            grad_a, grad_b = [0.0] * a.size, [0.0] * b.size
            for index, (ai, bi) in enumerate(zip(a_indices, b_indices)):
                if a.requires_grad:
                    grad_a[ai] += gradient[index] * (bf[bi] if name == "multiply" else 1.0)
                if b.requires_grad:
                    grad_b[bi] += gradient[index] * (af[ai] if name == "multiply" else 1.0)
            contributions = []
            if a.requires_grad:
                contributions.append((a, grad_a))
            if b.requires_grad:
                contributions.append((b, grad_b))
            return tuple(contributions)
        result._backward = backward
    return result


def as_tensor(value):
    return value if isinstance(value, Tensor) else Tensor(value)


def tensor(data, requires_grad=False):
    return Tensor(data, requires_grad=requires_grad)


def backward(value, gradient=None):
    return as_tensor(value).backward(gradient)


def grad(value):
    return as_tensor(value).grad_values()


def sum_tensor(value):
    return as_tensor(value).sum_tensor()


def shape(value):
    return list(as_tensor(value).shape)


def to_list(value):
    return as_tensor(value).to_list()


def transpose(value):
    return as_tensor(value).transpose()


def add(left, right):
    return as_tensor(left).add(right)


def multiply(left, right):
    return as_tensor(left).multiply(right)


def scale(value, factor):
    return as_tensor(value).scale(factor)


def sum_values(value):
    return as_tensor(value).sum()


def mean(value):
    return as_tensor(value).mean()


def min_value(value):
    return as_tensor(value).min()


def max_value(value):
    return as_tensor(value).max()


def get(value, index):
    return as_tensor(value).get(index)


def slice_tensor(value, axis=0, start=None, stop=None, step=1):
    return as_tensor(value).slice(axis, start, stop, step)


def serialize(value):
    """Return a deterministic, versioned JSON representation of a tensor."""
    item = as_tensor(value)
    payload = {"format": TENSOR_FORMAT, "version": TENSOR_VERSION,
               "shape": list(item.shape), "data": item.to_list()}
    return json.dumps(payload, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":"), sort_keys=True)


def deserialize(source):
    """Restore a tensor from its versioned JSON representation."""
    if not isinstance(source, str):
        raise TensorError("serialized tensor must be a string")
    if len(source) > 32_000_000:
        raise TensorError("serialized tensor exceeds the 32 MB input limit")
    try:
        payload = json.loads(source)
    except (json.JSONDecodeError, TypeError) as error:
        raise TensorError(f"invalid tensor JSON: {error}") from error
    if not isinstance(payload, dict) or payload.get("format") != TENSOR_FORMAT:
        raise TensorError("unsupported tensor serialization format")
    if payload.get("version") != TENSOR_VERSION:
        raise TensorError("unsupported tensor serialization version")
    result = Tensor(payload.get("data"))
    if payload.get("shape") != list(result.shape):
        raise TensorError("serialized tensor shape does not match its data")
    return result


def softmax(value):
    return as_tensor(value).softmax()


def matmul(left, right):
    """Multiply two rank-2 matrices using a cache-friendlier CPU kernel."""
    a, b = as_tensor(left), as_tensor(right)
    if a.ndim != 2 or b.ndim != 2:
        raise TensorError("matmul expects two rank-2 matrices")
    rows, inner = a.shape
    other_inner, cols = b.shape
    if inner != other_inner:
        raise TensorError(f"matmul shape mismatch: {a.shape} x {b.shape}")
    if rows * cols > MAX_TENSOR_ELEMENTS:
        raise TensorError("matmul result exceeds the 1,000,000 element limit")
    bt = b.transpose()._data
    result = []
    for row in range(rows):
        output_row = []
        for col in range(cols):
            output_row.append(_inspect(math.fsum(
                a._data[row][k] * bt[col][k] for k in range(inner)
            )))
        result.append(output_row)
    output = Tensor(result)
    if a.requires_grad or b.requires_grad:
        output.requires_grad = True
        output._parents = tuple(parent for parent in (a, b) if parent.requires_grad)
        def backward(gradient):
            grad_matrix = _reshape(gradient, output.shape)
            contributions = []
            if a.requires_grad:
                da = [[math.fsum(grad_matrix[i][j] * b._data[k][j] for j in range(cols))
                       for k in range(inner)] for i in range(rows)]
                contributions.append((a, _flat(da)))
            if b.requires_grad:
                db = [[math.fsum(a._data[i][k] * grad_matrix[i][j] for i in range(rows))
                       for j in range(cols)] for k in range(inner)]
                contributions.append((b, _flat(db)))
            return tuple(contributions)
        output._backward = backward
    return output


class Optimizer:
    """Base optimizer for explicitly registered trainable tensors."""

    def __init__(self, parameters, learning_rate):
        if not isinstance(parameters, (list, tuple)) or not parameters:
            raise TensorError("optimizer parameters must be a non-empty list")
        if len({id(parameter) for parameter in parameters}) != len(parameters):
            raise TensorError("optimizer parameters cannot contain duplicates")
        if any(not isinstance(parameter, Tensor) or not parameter.requires_grad
               for parameter in parameters):
            raise TensorError("optimizer parameters must be tensors with requires_grad enabled")
        self.parameters = list(parameters)
        self.learning_rate = _inspect(learning_rate)
        if not 0 < self.learning_rate <= 1:
            raise TensorError("learning_rate must be greater than 0 and at most 1")

    def zero_grad(self):
        for parameter in self.parameters:
            parameter.grad = None

    def _apply(self, updates):
        # Validate every parameter update before mutating any parameter.
        candidates = []
        for parameter, values in zip(self.parameters, updates):
            if len(values) != parameter.size:
                raise TensorError("optimizer gradient shape mismatch")
            candidates.append([_inspect(value) for value in values])
        for parameter, values in zip(self.parameters, candidates):
            parameter._data = _reshape(values, parameter.shape)


class SGDOptimizer(Optimizer):
    def step(self):
        updates = []
        for parameter in self.parameters:
            if parameter.grad is None:
                updates.append(_flat(parameter._data))
            else:
                updates.append([
                    value - self.learning_rate * gradient
                    for value, gradient in zip(_flat(parameter._data), parameter.grad)
                ])
        self._apply(updates)
        return True


class AdamOptimizer(Optimizer):
    def __init__(self, parameters, learning_rate=0.001,
                 beta1=0.9, beta2=0.999, epsilon=1e-8):
        super().__init__(parameters, learning_rate)
        self.beta1, self.beta2 = _inspect(beta1), _inspect(beta2)
        self.epsilon = _inspect(epsilon)
        if not 0 <= self.beta1 < 1 or not 0 <= self.beta2 < 1:
            raise TensorError("Adam beta values must be in the range [0, 1)")
        if self.epsilon <= 0:
            raise TensorError("Adam epsilon must be greater than zero")
        self._step = 0
        self._first = {id(parameter): [0.0] * parameter.size for parameter in self.parameters}
        self._second = {id(parameter): [0.0] * parameter.size for parameter in self.parameters}

    def step(self):
        self._step += 1
        updates = []
        for parameter in self.parameters:
            values = _flat(parameter._data)
            gradients = parameter.grad or [0.0] * parameter.size
            first = self._first[id(parameter)]
            second = self._second[id(parameter)]
            next_values = []
            for index, (value, gradient) in enumerate(zip(values, gradients)):
                first[index] = self.beta1 * first[index] + (1 - self.beta1) * gradient
                second[index] = self.beta2 * second[index] + (1 - self.beta2) * gradient * gradient
                corrected_first = first[index] / (1 - self.beta1 ** self._step)
                corrected_second = second[index] / (1 - self.beta2 ** self._step)
                next_values.append(value - self.learning_rate * corrected_first /
                                   (math.sqrt(corrected_second) + self.epsilon))
            updates.append(next_values)
        self._apply(updates)
        return True


def sgd(parameters, learning_rate=0.01):
    return SGDOptimizer(parameters, learning_rate)


def adam(parameters, learning_rate=0.001, beta1=0.9, beta2=0.999, epsilon=1e-8):
    return AdamOptimizer(parameters, learning_rate, beta1, beta2, epsilon)


def optimizer_step(optimizer):
    if not isinstance(optimizer, Optimizer):
        raise TensorError("step expects an optimizer created by ai.sgd or ai.adam")
    return optimizer.step()


def optimizer_zero_grad(optimizer):
    if not isinstance(optimizer, Optimizer):
        raise TensorError("zero_grad expects an optimizer created by ai.sgd or ai.adam")
    optimizer.zero_grad()
    return True


def random_tensor(dimensions, seed=None, low=-0.1, high=0.1):
    """Create a reproducible rank-1 or rank-2 tensor with uniform values."""
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) not in (1, 2):
        raise TensorError("dimensions must contain one or two positive integers")
    if any(isinstance(size, bool) or not isinstance(size, int)
           or not 1 <= size <= MAX_TENSOR_DIMENSION for size in dimensions):
        raise TensorError("tensor dimensions must be integers between 1 and 4096")
    if math.prod(dimensions) > MAX_TENSOR_ELEMENTS:
        raise TensorError("tensor exceeds the 1,000,000 element limit")
    low, high = _inspect(low), _inspect(high)
    if low > high:
        raise TensorError("low must not be greater than high")
    rng = random.Random(seed)
    if len(dimensions) == 1:
        return Tensor([rng.uniform(low, high) for _ in range(dimensions[0])])
    rows, cols = dimensions
    return Tensor([[rng.uniform(low, high) for _ in range(cols)] for _ in range(rows)])
