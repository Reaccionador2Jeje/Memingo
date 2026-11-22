import math
import unittest

from memingo.tensor import (
    TensorError, add, matmul, random_tensor, shape, softmax, tensor,
    to_list, transpose,
)


class TensorTests(unittest.TestCase):
    def test_vector_and_matrix_shapes(self):
        self.assertEqual(shape(tensor([1, 2, 3])), [3])
        self.assertEqual(shape(tensor([[1, 2], [3, 4]])), [2, 2])

    def test_matrix_multiplication(self):
        result = matmul([[1, 2, 3], [4, 5, 6]], [[7, 8], [9, 10], [11, 12]])
        self.assertEqual(to_list(result), [[58.0, 64.0], [139.0, 154.0]])

    def test_transpose(self):
        self.assertEqual(to_list(transpose([[1, 2, 3], [4, 5, 6]])),
                         [[1.0, 4.0], [2.0, 5.0], [3.0, 6.0]])

    def test_elementwise_add(self):
        self.assertEqual(to_list(add([[1, 2]], [[3, 4]])), [[4.0, 6.0]])

    def test_stable_softmax(self):
        result = to_list(softmax([1000, 1001, 1002]))
        self.assertAlmostEqual(sum(result), 1.0)
        self.assertTrue(all(math.isfinite(value) for value in result))
        self.assertGreater(result[2], result[1])

    def test_seeded_initialization_is_reproducible(self):
        self.assertEqual(to_list(random_tensor([2, 3], seed=42)),
                         to_list(random_tensor([2, 3], seed=42)))
        self.assertNotEqual(to_list(random_tensor([2, 3], seed=42)),
                            to_list(random_tensor([2, 3], seed=43)))

    def test_rejects_ragged_and_non_finite_values(self):
        with self.assertRaises(TensorError):
            tensor([[1, 2], [3]])
        with self.assertRaises(TensorError):
            tensor([1, float("nan")])

    def test_rejects_invalid_matmul_dimensions(self):
        with self.assertRaises(TensorError):
            matmul([[1, 2]], [[1, 2]])
        with self.assertRaises(TensorError):
            matmul([1, 2], [[1], [2]])

    def test_broadcast_vector_over_matrix(self):
        self.assertEqual(to_list(add([[1, 2], [3, 4]], [10, 20])),
                         [[11.0, 22.0], [13.0, 24.0]])

    def test_broadcast_singleton_dimensions(self):
        self.assertEqual(to_list(add([[1], [2]], [10, 20, 30])),
                         [[11.0, 21.0, 31.0], [12.0, 22.0, 32.0]])

    def test_rejects_incompatible_broadcast(self):
        with self.assertRaises(TensorError):
            add([[1, 2, 3]], [1, 2])

    def test_elementwise_multiply(self):
        from memingo.tensor import multiply
        self.assertEqual(to_list(multiply([[1, 2], [3, 4]], [2, 3])),
                         [[2.0, 6.0], [6.0, 12.0]])

    def test_reductions(self):
        from memingo.tensor import mean, min_value, max_value
        matrix = [[1, 2], [3, 8]]
        self.assertEqual(mean(matrix), 3.5)
        self.assertEqual(min_value(matrix), 1.0)
        self.assertEqual(max_value(matrix), 8.0)

    def test_indexing_and_slicing(self):
        from memingo.tensor import get, slice_tensor
        matrix = tensor([[1, 2, 3], [4, 5, 6]])
        self.assertEqual(to_list(get(matrix, 1)), [4.0, 5.0, 6.0])
        self.assertEqual(get(matrix, [1, 2]), 6.0)
        self.assertEqual(get(tensor([7, 8, 9]), -1), 9.0)
        self.assertEqual(to_list(slice_tensor(matrix, axis=1, start=0, stop=2)),
                         [[1.0, 2.0], [4.0, 5.0]])

    def test_versioned_serialization_round_trip(self):
        from memingo.tensor import serialize, deserialize
        original = tensor([[1, 2], [3.5, 4]])
        encoded = serialize(original)
        self.assertEqual(serialize(deserialize(encoded)), encoded)
        self.assertEqual(to_list(deserialize(encoded)), to_list(original))

    def test_serialization_rejects_unknown_version_and_bad_shape(self):
        from memingo.tensor import deserialize
        with self.assertRaises(TensorError):
            deserialize('{"format":"memingo.tensor","version":99,"shape":[1],"data":[1]}')
        with self.assertRaises(TensorError):
            deserialize('{"format":"memingo.tensor","version":1,"shape":[2],"data":[1]}')

    def test_numeric_overflow_is_rejected(self):
        with self.assertRaises(TensorError):
            add([1e308], [1e308])

    def test_runtime_limits(self):
        with self.assertRaises(TensorError):
            random_tensor([4096, 4096])

    def test_memingo_a15_api(self):
        from memingo.interpreter import execute
        source = '''
vibe matrix = ai.tensor([[1, 2], [3, 4]])
vibe shifted = ai.add(matrix, [10, 20])
spill ai.to_list(shifted)
spill ai.mean(matrix)
spill ai.get(matrix, [1, 0])
spill ai.to_list(ai.slice(matrix, 1, 0, 1))
vibe restored = ai.deserialize(ai.serialize(matrix))
spill ai.to_list(restored)
'''
        self.assertEqual(execute(source), [
            "[[11.0, 22.0], [13.0, 24.0]]",
            "2.5",
            "3.0",
            "[[1.0], [3.0]]",
            "[[1.0, 2.0], [3.0, 4.0]]",
        ])

    def test_autograd_broadcast_and_multiply(self):
        from memingo.tensor import backward, grad, multiply, sum_tensor
        left = tensor([[1, 2], [3, 4]], requires_grad=True)
        right = tensor([2, 3], requires_grad=True)
        backward(sum_tensor(multiply(left, right)))
        self.assertEqual(grad(left), [[2.0, 3.0], [2.0, 3.0]])
        self.assertEqual(grad(right), [4.0, 6.0])

    def test_autograd_matmul(self):
        from memingo.tensor import backward, grad, sum_tensor
        left = tensor([[1, 2], [3, 4]], requires_grad=True)
        right = tensor([[5, 6], [7, 8]], requires_grad=True)
        backward(sum_tensor(matmul(left, right)))
        self.assertEqual(grad(left), [[11.0, 15.0], [11.0, 15.0]])
        self.assertEqual(grad(right), [[4.0, 4.0], [6.0, 6.0]])

    def test_autograd_softmax_transpose_and_scalar(self):
        from memingo.tensor import backward, grad, sum_tensor
        vector = tensor([1, 2, 3], requires_grad=True)
        backward(sum_tensor(softmax(vector)))
        self.assertTrue(all(abs(value) < 1e-12 for value in grad(vector)))
        matrix = tensor([[1, 2], [3, 4]], requires_grad=True)
        backward(sum_tensor(transpose(matrix)))
        self.assertEqual(grad(matrix), [[1.0, 1.0], [1.0, 1.0]])

    def test_autograd_requires_seed_for_non_scalar(self):
        from memingo.tensor import backward
        with self.assertRaises(TensorError):
            backward(tensor([1, 2], requires_grad=True))

    def test_memingo_autograd_api(self):
        from memingo.interpreter import execute
        source = '''
vibe x = ai.tensor([2, 3], based)
vibe loss = ai.sum_tensor(ai.multiply(x, [4, 5]))
ai.backward(loss)
spill ai.grad(x)
'''
        self.assertEqual(execute(source), ["[4.0, 5.0]"])

    def test_sgd_optimizer_updates_parameters(self):
        from memingo.tensor import backward, grad, sgd, sum_tensor
        weights = tensor([2, 3], requires_grad=True)
        loss = sum_tensor(multiply(weights, [4, 5]))
        backward(loss)
        optimizer = sgd([weights], learning_rate=0.1)
        optimizer.step()
        self.assertEqual(to_list(weights), [1.6, 2.5])
        optimizer.zero_grad()
        self.assertIsNone(grad(weights))

    def test_adam_optimizer_updates_parameters(self):
        from memingo.tensor import adam, backward, sum_tensor
        weights = tensor([1.0, -1.0], requires_grad=True)
        backward(sum_tensor(multiply(weights, [2.0, -3.0])))
        optimizer = adam([weights], learning_rate=0.01)
        optimizer.step()
        self.assertAlmostEqual(to_list(weights)[0], 0.99, places=6)
        self.assertAlmostEqual(to_list(weights)[1], -0.99, places=6)

    def test_optimizer_rejects_invalid_parameters(self):
        from memingo.tensor import sgd
        with self.assertRaises(TensorError):
            sgd([tensor([1, 2])], learning_rate=0.1)
        with self.assertRaises(TensorError):
            sgd([tensor([1, 2], requires_grad=True)], learning_rate=0)

    def test_memingo_optimizer_api(self):
        from memingo.interpreter import execute
        source = '''
vibe weights = ai.tensor([2, 3], based)
vibe loss = ai.sum_tensor(ai.multiply(weights, [4, 5]))
ai.backward(loss)
vibe optimizer = ai.sgd([weights], 0.1)
ai.step(optimizer)
spill ai.to_list(weights)
'''
        self.assertEqual(execute(source), ["[1.6, 2.5]"])

    def test_autograd_activations_and_mean(self):
        from memingo.tensor import backward, grad, mean_tensor, relu, sigmoid, sum_tensor, tanh
        values = tensor([-2, 0, 2], requires_grad=True)
        backward(mean_tensor(relu(values)))
        self.assertEqual(grad(values), [0.0, 0.0, 1.0 / 3.0])
        for activation in (sigmoid, tanh):
            sample = tensor([0.5, -0.5], requires_grad=True)
            output = activation(sample)
            backward(sum_tensor(output))
            self.assertTrue(all(math.isfinite(value) for value in grad(sample)))

    def test_mse_loss_gradient(self):
        from memingo.tensor import backward, grad, mse_loss
        prediction = tensor([1, 2], requires_grad=True)
        loss = mse_loss(prediction, [0, 0])
        self.assertAlmostEqual(to_list(loss)[0], 2.5)
        backward(loss)
        self.assertEqual(grad(prediction), [1.0, 2.0])

    def test_linear_layer(self):
        from memingo.tensor import linear
        result = linear([[1, 2]], [[1, 2], [3, 4]], [0, 1])
        self.assertEqual(to_list(result), [[7.0, 11.0]])

    def test_memingo_linear_and_loss_api(self):
        from memingo.interpreter import execute
        source = '''
vibe input = ai.tensor([[1, 2]])
vibe weights = ai.tensor([[1, 2], [3, 4]], based)
vibe bias = ai.tensor([0, 1], based)
vibe prediction = ai.linear(input, weights, bias)
vibe loss = ai.mse_loss(prediction, [[0, 0]])
spill ai.to_list(prediction)
spill ai.to_list(loss)
'''
        self.assertEqual(execute(source), ["[[7.0, 11.0]]", "[85.0]"])

    def test_memingo_script_api(self):
        from memingo.interpreter import execute
        source = '''
vibe left = ai.tensor([[1, 2], [3, 4]])
vibe right = ai.tensor([[5, 6], [7, 8]])
vibe product = ai.matmul(left, right)
spill ai.shape(product)
spill ai.to_list(product)
spill ai.to_list(ai.softmax([1, 2, 3]))
'''
        self.assertEqual(execute(source), [
            "[2, 2]",
            "[[19.0, 22.0], [43.0, 50.0]]",
            "[0.09003057317038046, 0.24472847105479764, 0.6652409557748218]",
        ])


if __name__ == "__main__":
    unittest.main()
