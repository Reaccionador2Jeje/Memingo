import unittest

from memingo.compiler import compile_source
from memingo.compiler.hir import HIRProgram, lower
from memingo.parser import parse


class HIRTests(unittest.TestCase):
    def test_lowering_preserves_statement_structure_and_spans(self):
        program = parse('vibe answer = 6 * 7\nspill answer', source_id="main.mgo")
        hir = lower(program)
        self.assertIsInstance(hir, HIRProgram)
        self.assertEqual([node.kind for node in hir.statements], ["Let", "Say"])
        self.assertEqual(hir.statements[0].span.source_id, "main.mgo")
        self.assertEqual(hir.statements[0].children[0].kind, "Binary")
        self.assertEqual(hir.statements[0].children[0].value, "*")

    def test_lowering_covers_functions_lists_maps_and_control_flow(self):
        program = parse('''
ritual greet(name) { spill name }
vibe values = [1, 2]
vibe config = {mode: "fast"}
when based { greet("hi") } nah { grind cringe { spill ghost } }
''')
        hir = lower(program)
        self.assertEqual(hir.statements[0].kind, "Function")
        self.assertEqual(hir.statements[1].children[0].kind, "ListExpression")
        self.assertEqual(hir.statements[2].children[0].kind, "MapExpression")
        self.assertEqual(hir.statements[3].kind, "If")


class CompilationPipelineTests(unittest.TestCase):
    def test_successful_source_produces_typed_hir(self):
        result = compile_source("vibe answer = 40 + 2\nspill answer", "main.mgo")
        self.assertTrue(result.succeeded)
        self.assertIsNotNone(result.hir)
        declaration = result.hir.statements[0]
        self.assertEqual(str(declaration.children[0].type), "whole")

    def test_semantic_errors_keep_hir_for_tooling(self):
        result = compile_source("spill unknown_name", "bad.mgo")
        self.assertFalse(result.succeeded)
        self.assertIsNotNone(result.hir)
        self.assertTrue(any(item.code == "M1002" for item in result.diagnostics))

    def test_syntax_errors_stop_before_hir(self):
        result = compile_source('spill "unfinished', "bad.mgo")
        self.assertFalse(result.succeeded)
        self.assertIsNone(result.hir)
        self.assertEqual(result.diagnostics[0].code, "M0001")

    def test_empty_program_is_valid(self):
        result = compile_source("")
        self.assertTrue(result.succeeded)
        self.assertEqual(result.hir.statements, ())


if __name__ == "__main__":
    unittest.main()
