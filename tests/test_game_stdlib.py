import unittest

from memingo.interpreter import Interpreter, RuntimeErrorMemingo


class GameAndAppStandardLibraryTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = Interpreter()

    def call_builtin(self, name, *arguments):
        return self.interpreter.global_environment.get(name)(*arguments)

    def test_vector_constructors_and_distances(self):
        self.assertEqual(self.call_builtin("vec2", 3, 4), {"x": 3, "y": 4})
        self.assertEqual(self.call_builtin("vec3", 1, 2, 2), {"x": 1, "y": 2, "z": 2})
        self.assertEqual(self.call_builtin("distance2", [0, 0], [3, 4]), 5)
        self.assertEqual(self.call_builtin("distance3", {"x": 0, "y": 0, "z": 0}, {"x": 2, "y": 3, "z": 6}), 7)

    def test_vector_normalization_and_zero_vector(self):
        normalized = self.call_builtin("normalize2", {"x": 3, "y": 4})
        self.assertAlmostEqual(normalized["x"], 0.6)
        self.assertAlmostEqual(normalized["y"], 0.8)
        self.assertEqual(self.call_builtin("normalize3", [0, 0, 0]), {"x": 0, "y": 0, "z": 0})

    def test_interpolation_and_move_toward(self):
        self.assertEqual(self.call_builtin("lerp", 10, 20, 0.25), 12.5)
        self.assertEqual(self.call_builtin("move_toward", 2, 10, 3), 5)
        self.assertEqual(self.call_builtin("move_toward", 8, 10, 5), 10)
        self.assertEqual(self.call_builtin("move_toward", 8, 10, 0), 8)

    def test_random_helpers_respect_contracts(self):
        self.assertIs(self.call_builtin("chance", 1), True)
        self.assertIs(self.call_builtin("chance", 0), False)
        self.assertIn(self.call_builtin("pick", ["a", "b"]), ["a", "b"])
        self.assertIn(self.call_builtin("weighted_pick", ["common", "rare"], [1, 0]), ["common"])

    def test_invalid_arguments_raise_language_errors(self):
        with self.assertRaisesRegex(RuntimeErrorMemingo, "2D vector"):
            self.call_builtin("distance2", [1], [2, 3])
        with self.assertRaisesRegex(RuntimeErrorMemingo, "between 0 and 1"):
            self.call_builtin("chance", 2)
        with self.assertRaisesRegex(RuntimeErrorMemingo, "non-negative"):
            self.call_builtin("move_toward", 1, 2, -1)
        with self.assertRaisesRegex(RuntimeErrorMemingo, "empty list"):
            self.call_builtin("pick", [])
        with self.assertRaisesRegex(RuntimeErrorMemingo, "positive total weight"):
            self.call_builtin("weighted_pick", ["a", "b"], [0, 0])

    def test_language_program_can_use_game_helpers(self):
        from memingo.parser import parse

        self.interpreter.run(parse(
            'vibe spawn = vec2(0, 0)\n'
            'vibe target = vec2(3, 4)\n'
            'spill distance2(spawn, target)\n'
            'spill lerp(0, 100, 0.5)\n'
        ))
        self.assertEqual(self.interpreter.output, ["5.0", "50.0"])


if __name__ == "__main__":
    unittest.main()
