import unittest

from memingo.compiler import compile_source


class OwnershipAnalysisTests(unittest.TestCase):
    def test_collection_binding_transfers_ownership(self):
        result = compile_source(
            'vibe first = [1, 2]\n'
            'vibe second = first\n'
            'spill first'
        )
        self.assertFalse(result.succeeded)
        self.assertTrue(any(item.code == "M2001" for item in result.diagnostics))

    def test_moved_collection_can_be_rebound(self):
        result = compile_source(
            'vibe first = [1, 2]\n'
            'vibe second = first\n'
            'first = [3, 4]\n'
            'spill first'
        )
        self.assertFalse(any(item.code == "M2001" for item in result.diagnostics))

    def test_scalar_binding_is_not_moved(self):
        result = compile_source(
            'vibe first = 42\n'
            'vibe second = first\n'
            'spill first'
        )
        self.assertFalse(any(item.code == "M2001" for item in result.diagnostics))

    def test_move_diagnostics_have_source_location(self):
        result = compile_source(
            'vibe first = [1]\n'
            'vibe second = first\n'
            'spill first',
            source_id="ownership.mgo",
        )
        diagnostic = next(item for item in result.diagnostics if item.code == "M2001")
        self.assertTrue(diagnostic.labels)
        self.assertEqual(diagnostic.labels[0].span.source_id, "ownership.mgo")


if __name__ == "__main__":
    unittest.main()
