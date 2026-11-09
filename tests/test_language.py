import json
import tempfile
import unittest
from pathlib import Path

from memingo.interpreter import Interpreter, RuntimeErrorMemingo, execute
from memingo.parser import parse
from memingo.http_api import MemingoAPIServer
from memingo.parser import ParseError




def api_server_dispatch(api, method, path, body=b"", headers=None):
    return api["get"].__self__._dispatch(method, path, headers or {}, body)


class MemingoLanguageTests(unittest.TestCase):
    def test_variables_and_output(self):
        output = execute('vibe name = "Memingo"\nspill "Hola " + name')
        self.assertEqual(output, ["Hola Memingo"])

    def test_condition(self):
        output = execute('when 8 > 3 { spill "based" } nah { spill "cringe" }')
        self.assertEqual(output, ["based"])

    def test_while_loop_and_assignment(self):
        output = execute('vibe i = 0\ngrind i < 3 { spill i\ni = i + 1 }')
        self.assertEqual(output, ["0", "1", "2"])

    def test_function_and_recursion(self):
        output = execute('ritual factorial(n) { when n <= 1 { drop 1 } drop n * factorial(n - 1) }\nspill factorial(5)')
        self.assertEqual(output, ["120"])

    def test_lists_and_builtin(self):
        output = execute('vibe values = [1, 2, 3]\nspill headcount(values)')
        self.assertEqual(output, ["3"])

    def test_division_by_zero(self):
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill 10 / 0')

    def test_invalid_syntax(self):
        with self.assertRaises(ParseError):
            execute('vibe = 4')

    def test_objects_lists_and_json(self):
        output = execute('vibe user = {name: "Ana", role: "dev"}\nvibe users = [user]\nspill user.name\nspill json_stringify(users)')
        self.assertEqual(output, ['Ana', '[{"name":"Ana","role":"dev"}]'])

    def test_mutable_collections(self):
        output = execute('vibe values = []\npush(values, "based")\nset_value(values, 0, "cringe")\nspill values[0]')
        self.assertEqual(output, ["cringe"])

    def test_multiline_lists_and_objects(self):
        source = (
            'vibe world = {\n  name: "MemeCraft",\n  day: based,\n  size: 30\n}\n'
            'vibe materials = [\n  {name: "grass", solid: based},\n  {name: "stone", solid: cringe},\n]\n'
            'spill world.name\n'
            'spill headcount(materials)\n'
            'spill materials[1].name'
        )
        self.assertEqual(execute(source), ["MemeCraft", "2", "stone"])

    def test_multiline_parameters(self):
        source = (
            'ritual add(\n  a,\n  b,\n) {\n  drop a + b\n}\n'
            'spill add(\n  1,\n  2,\n)'
        )
        self.assertEqual(execute(source), ["3"])

    def test_builtin_errors_are_wrapped(self):
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute("spill headcount(1)")
        self.assertIn("headcount", str(context.exception))

    def test_whatkind_and_borrow_validation(self):
        output = execute('spill whatkind(based)\nspill whatkind(1)\nspill whatkind("x")\nspill whatkind(ghost)')
        self.assertEqual(output, ["based-or-cringe", "whole", "caption", "ghost"])
        with self.assertRaises(RuntimeErrorMemingo):
            execute('borrow "../escape"')

    def test_json_round_trip(self):
        output = execute('vibe value = json_parse("{\\\"meme\\\":\\\"based\\\"}")\nspill value["meme"]')
        self.assertEqual(output, ["based"])

    def test_string_builtins(self):
        source = (
            'vibe text = "  Memingo Rocks  "\n'
            'spill trim(text)\n'
            'spill upper("meme")\n'
            'spill lower("MEME")\n'
            'spill replace("meme life", "meme", "based")\n'
            'spill join(split("a,b,c", ","), "-")\n'
            'spill contains("memingo", "ming")\n'
            'spill starts_with("memingo", "mem")\n'
            'spill ends_with("memingo", "go")\n'
            'spill slice([1, 2, 3, 4], 1, 3)'
        )
        self.assertEqual(
            execute(source),
            ["Memingo Rocks", "MEME", "meme", "based life", "a-b-c", "based", "based", "based", "[2, 3]"],
        )

    def test_collection_builtins(self):
        source = (
            'vibe values = [3, 1, 2]\n'
            'spill sort(values)\n'
            'spill reverse(values)\n'
            'spill sum(values)\n'
            'spill min(values)\n'
            'spill max(values)\n'
            'spill values'
        )
        self.assertEqual(
            execute(source),
            ["[1, 2, 3]", "[2, 1, 3]", "6", "1", "3", "[3, 1, 2]"],
        )

    def test_higher_order_builtins(self):
        source = (
            'ritual double(n) { drop n * 2 }\n'
            'ritual even(n) { drop n % 2 == 0 }\n'
            'ritual combine(a, b) { drop a + b }\n'
            'spill map([1, 2, 3], double)\n'
            'spill filter([1, 2, 3, 4], even)\n'
            'spill reduce([1, 2, 3, 4], combine, 0)'
        )
        self.assertEqual(execute(source), ["[2, 4, 6]", "[2, 4]", "10"])

    def test_math_and_range_builtins(self):
        source = (
            'spill abs(-7)\n'
            'spill floor(2.9)\n'
            'spill ceil(2.1)\n'
            'spill round(2.6)\n'
            'spill clamp(12, 0, 10)\n'
            'spill parse_int("42")\n'
            'spill parse_float("2.5")\n'
            'spill range(2, 8, 2)\n'
            'spill values({a: 1, b: 2})'
        )
        self.assertEqual(execute(source), ["7", "2", "3", "3", "10", "42", "2.5", "[2, 4, 6]", "[1, 2]"])

    def test_playful_builtins(self):
        output = execute(
            'spill meme_case("hello memingo")\n'
            'vibe cards = ["a", "b", "c"]\n'
            'spill shuffle(cards)\n'
            'vibe id = uuid()\n'
            'spill headcount(id)'
        )
        self.assertEqual(output[0], "HeLlO MeMiNgO")
        self.assertEqual(sorted(output[1][1:-1].replace('"', '').split(', ')), ['a', 'b', 'c'])
        self.assertEqual(output[2], "36")

    def test_new_builtin_argument_validation(self):
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute('spill upper(3)')
        self.assertIn("upper", str(context.exception))
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill map("nope", upper)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill reduce([], upper)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill parse_int("not-a-number")')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill meme_case(42)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill shuffle("not-a-list")')

    def test_text_helpers_repeat_lines_and_unique(self):
        source = (
            'spill repeat("ab", 3)\n'
            'spill lines("uno\ndos\ntres")\n'
            'spill unique([1, 2, 2, 3, 1])'
        )
        self.assertEqual(
            execute(source),
            ["ababab", '["uno", "dos", "tres"]', "[1, 2, 3]"],
        )

    def test_text_helpers_validate_arguments(self):
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill repeat("ab", -1)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill repeat(1, 2)')
        with self.assertRaises(RuntimeErrorMemingo):
            execute('spill unique("nope")')


    def test_runtime_errors_include_source_location(self):
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute('vibe answer = 42\nspill missing_value')
        self.assertEqual(context.exception.line, 2)
        self.assertIn("line 2", str(context.exception))

    def test_runtime_error_in_function_keeps_inner_location(self):
        source = 'ritual fail() {\n  spill missing_value\n}\nfail()'
        with self.assertRaises(RuntimeErrorMemingo) as context:
            execute(source)
        self.assertEqual(context.exception.line, 2)
        self.assertIn("line 2", str(context.exception))


    def test_import_math_module(self):
        self.assertEqual(execute('import "math"\nspill math.sqrt(81)\nspill math.pi > 3'), ["9.0", "based"])

    def test_import_project_module_and_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "mathkit.mgo").write_text(
                'ritual double(n) { drop n * 2 }\nvibe label = "MathKit"',
                encoding="utf-8",
            )
            output = execute(
                'import "mathkit" as kit\nspill kit.double(21)\nspill kit.label',
                project_directory=root,
            )
            self.assertEqual(output, ["42", "MathKit"])

    def test_import_module_directory_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "tools"
            package.mkdir()
            (package / "main.mgo").write_text('vibe answer = 42', encoding="utf-8")
            self.assertEqual(
                execute('import "tools"\nspill tools.answer', project_directory=root),
                ["42"],
            )

    def test_import_rejects_path_escape_and_missing_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(RuntimeErrorMemingo):
                execute('import "../outside"', project_directory=root)
            with self.assertRaises(RuntimeErrorMemingo):
                execute('import "missing"', project_directory=root)

    def test_import_detects_circular_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "a.mgo").write_text('import "b"', encoding="utf-8")
            (root / "b.mgo").write_text('import "a"', encoding="utf-8")
            with self.assertRaises(RuntimeErrorMemingo) as context:
                execute('import "a"', project_directory=root)
            self.assertIn("Circular module import", str(context.exception))


    def test_http_server_dispatches_get_and_json_post(self):
        interpreter = Interpreter()
        source = (
            'vibe api = http_server()\n'
            'ritual home(request) { drop {status: 200, body: {message: "Memingo"}} }\n'
            'ritual echo(request) { drop {status: 201, body: request.body} }\n'
            'api.get("/", home)\n'
            'api.post("/echo", echo)'
        )
        interpreter.run(parse(source))
        api = interpreter.global_environment.get("api")
        status, headers, body = api_server_dispatch(api, "GET", "/")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"message": "Memingo"})
        status, headers, body = api_server_dispatch(api, "POST", "/echo", b'{"ok":true}')
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(body), {"ok": True})

    def test_http_server_rejects_invalid_routes(self):
        api = MemingoAPIServer(Interpreter()).api()
        with self.assertRaises(ValueError):
            api["get"]("hello", lambda request: request)
        with self.assertRaises(ValueError):
            api["get"]("/", "not a ritual")


    def test_http_server_dynamic_routes_and_query(self):
        interpreter = Interpreter()
        source = (
            'vibe api = http_server()\n'
            'ritual user(request) { drop {body: {id: request.params.id, page: request.query.page}} }\n'
            'api.get("/users/{id}", user)'
        )
        interpreter.run(parse(source))
        api = interpreter.global_environment.get("api")
        status, headers, body = api_server_dispatch(api, "GET", "/users/42?page=3")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"id": "42", "page": "3"})

    def test_http_server_middleware_and_bearer_auth(self):
        interpreter = Interpreter()
        source = (
            'vibe api = http_server()\n'
            'ritual private(request) { drop {body: {secret: "ok"}} }\n'
            'api.use(api.bearer("test-token"))\n'
            'api.get("/private", private)'
        )
        interpreter.run(parse(source))
        api = interpreter.global_environment.get("api")
        status, headers, body = api_server_dispatch(api, "GET", "/private")
        self.assertEqual(status, 401)
        status, headers, body = api_server_dispatch(
            api, "GET", "/private", headers={"Authorization": "Bearer test-token"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"secret": "ok"})

    def test_sqlite_helpers_support_parameterized_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = execute(
                'vibe db = sqlite(":memory:")\n'
                'db.execute("CREATE TABLE people (name TEXT)")\n'
                'db.execute("INSERT INTO people (name) VALUES (?)", ["Cris"])\n'
                'spill db.query("SELECT name FROM people")[0].name\n'
                'db.close()',
                project_directory=temporary,
            )
            self.assertEqual(output, ["Cris"])

    def test_sqlite_rejects_paths_outside_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(RuntimeErrorMemingo):
                execute('vibe db = sqlite("../outside.db")', project_directory=temporary)

    def test_file_builtins_stay_inside_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            written = execute('spill write_file("notes/hello.txt", "hola")', project_directory=root)
            self.assertEqual(written, ["4"])
            self.assertTrue((root / "notes" / "hello.txt").is_file())

            output = execute(
                'spill read_file("notes/hello.txt")\n'
                'spill file_exists("notes/hello.txt")\n'
                'spill file_exists("notes/missing.txt")\n'
                'spill list_files("notes")',
                project_directory=root,
            )
            self.assertEqual(output, ["hola", "based", "cringe", '["hello.txt"]'])

    def test_file_builtins_reject_escaping_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(RuntimeErrorMemingo):
                execute('spill write_file("../escape.txt", "nope")', project_directory=root)
            with self.assertRaises(RuntimeErrorMemingo):
                execute('spill read_file("/etc/passwd")', project_directory=root)
            self.assertFalse((root.parent / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
