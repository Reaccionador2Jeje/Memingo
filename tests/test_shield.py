import unittest

from memingo.shield import MemingoShield, ShieldLimits, ShieldViolation
from memingo.interpreter import Interpreter, RuntimeErrorMemingo
from memingo.parser import parse


class HybridShieldTests(unittest.TestCase):
    def test_step_budget_stops_endless_loop(self):
        interpreter = Interpreter(
            shield_limits=ShieldLimits(max_steps=12, max_call_depth=20)
        )
        with self.assertRaisesRegex(RuntimeErrorMemingo, "Shield blocked execution"):
            interpreter.run(parse("grind based { }"))

    def test_call_depth_is_bounded(self):
        interpreter = Interpreter(
            shield_limits=ShieldLimits(max_steps=1000, max_call_depth=8)
        )
        program = parse(
            "ritual recurse() { drop recurse() }\n"
            "recurse()"
        )
        with self.assertRaisesRegex(RuntimeErrorMemingo, "Shield blocked execution"):
            interpreter.run(program)

    def test_large_collection_is_rejected(self):
        shield = MemingoShield(ShieldLimits(max_collection_items=2))
        with self.assertRaises(ShieldViolation):
            shield.validate([1, 2, 3])

    def test_oversized_string_is_rejected(self):
        shield = MemingoShield(ShieldLimits(max_string_chars=4))
        with self.assertRaises(ShieldViolation):
            shield.validate("memingo")

    def test_non_finite_float_is_rejected(self):
        shield = MemingoShield()
        with self.assertRaises(ShieldViolation):
            shield.validate(float("inf"))


    def test_memory_budget_rejects_large_reachable_values(self):
        shield = MemingoShield(ShieldLimits(max_memory_bytes=256))
        with self.assertRaisesRegex(ShieldViolation, "memory budget exceeded"):
            shield.check_memory({"payload": ["memingo"] * 20})

    def test_memory_estimate_counts_shared_objects_once(self):
        shield = MemingoShield()
        shared = ["same"]
        combined = [shared, shared]
        self.assertEqual(
            shield.estimate_size(combined),
            shield.estimate_size([shared]),
        )

    def test_interpreter_enforces_memory_budget(self):
        interpreter = Interpreter(
            shield_limits=ShieldLimits(max_steps=1000, max_memory_bytes=512)
        )
        program = parse("vibe data = [" + ", ".join(str(i) for i in range(100)) + "]")
        with self.assertRaisesRegex(RuntimeErrorMemingo, "memory budget exceeded"):
            interpreter.run(program)

    def test_normal_program_still_runs(self):
        interpreter = Interpreter()
        interpreter.run(parse('spill "Hybrid Shield"'))
        self.assertEqual(interpreter.output, ["Hybrid Shield"])


if __name__ == "__main__":
    unittest.main()
