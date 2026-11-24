import unittest

from memingo.shield import AllocationTracker, MemingoShield, ShieldLimits, ShieldViolation
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

    def test_allocation_tracker_counts_shared_objects_once(self):
        tracker = AllocationTracker()
        shared = ["same"]
        tracker.snapshot([[shared, shared]])
        first = tracker.stats()
        tracker.snapshot([[shared]])
        second = tracker.stats()
        self.assertEqual(first["active_objects"], second["active_objects"])

    def test_interpreter_enforces_memory_budget(self):
        interpreter = Interpreter(
            shield_limits=ShieldLimits(max_steps=1000, max_memory_bytes=512)
        )
        program = parse("vibe data = [" + ", ".join(str(i) for i in range(100)) + "]")
        with self.assertRaisesRegex(RuntimeErrorMemingo, "memory budget exceeded"):
            interpreter.run(program)

    def test_allocation_tracker_observes_new_and_released_objects(self):
        tracker = AllocationTracker()
        values = {"items": ["first"]}
        initial = tracker.snapshot([values])
        values["items"].append("second")
        grown = tracker.snapshot([values])
        self.assertGreater(grown["total_allocations"], initial["total_allocations"])
        values.clear()
        released = tracker.snapshot([values])
        self.assertGreater(released["total_releases"], grown["total_releases"])
        self.assertGreaterEqual(grown["peak_bytes"], grown["active_bytes"])

    def test_interpreter_exposes_memory_statistics(self):
        interpreter = Interpreter()
        interpreter.run(parse('vibe items = ["one", "two"]'))
        self.assertGreater(interpreter.memory_stats["active_objects"], 0)
        self.assertGreater(interpreter.memory_stats["snapshots"], 0)

    def test_normal_program_still_runs(self):
        interpreter = Interpreter()
        interpreter.run(parse('spill "Hybrid Shield"'))
        self.assertEqual(interpreter.output, ["Hybrid Shield"])


if __name__ == "__main__":
    unittest.main()
