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
