import io
import json
import unittest

from memingo.lsp import MemingoLanguageServer


class LanguageServerTests(unittest.TestCase):
    def make_message(self, value):
        body = json.dumps(value).encode("utf-8")
        return b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body

    def test_initialize_and_document_diagnostics(self):
        source = self.make_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        source += self.make_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        source += self.make_message({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": "file:///main.mgo", "text": "vibe x = 2\nspill x"}
        }})
        output = io.BytesIO()
        server = MemingoLanguageServer(io.BytesIO(source), output)
        self.assertEqual(server.run(), 0)
        packets = output.getvalue().split(b"\r\n\r\n")
        messages = [json.loads(packets[i+1]) for i in range(0, len(packets)-1, 2) if packets[i+1]]
        self.assertEqual(messages[0]["id"], 1)
        self.assertIn("completionProvider", messages[0]["result"]["capabilities"])
        diagnostics = next(item for item in messages if item.get("method") == "textDocument/publishDiagnostics")
        self.assertEqual(diagnostics["params"]["diagnostics"], [])

    def test_completion_includes_memingo_keywords_and_builtins(self):
        server = MemingoLanguageServer(io.BytesIO(), io.BytesIO())
        server.documents["file:///main.mgo"] = "vibe score = 4"
        result = server._completion({"textDocument": {"uri": "file:///main.mgo"}})
        labels = {item["label"] for item in result["items"]}
        self.assertIn("ritual", labels)
        self.assertIn("json_parse", labels)
        self.assertIn("score", labels)

    def test_hover_describes_builtin(self):
        server = MemingoLanguageServer(io.BytesIO(), io.BytesIO())
        server.documents["file:///main.mgo"] = "spill json_parse(\"{}\")"
        result = server._hover({"textDocument": {"uri": "file:///main.mgo"}, "position": {"line": 0, "character": 10}})
        self.assertIn("Función integrada", result["contents"]["value"])

    def test_hover_uses_word_under_cursor(self):
        server = MemingoLanguageServer(io.BytesIO(), io.BytesIO())
        server.documents["file:///main.mgo"] = "spill json_parse(\\"{}\\")"
        result = server._hover({"textDocument": {"uri": "file:///main.mgo"}, "position": {"line": 0, "character": 10}})
        self.assertIn("Función integrada", result["contents"]["value"])

    def test_definition_finds_declared_vibe(self):
        server = MemingoLanguageServer(io.BytesIO(), io.BytesIO())
        server.documents["file:///main.mgo"] = "vibe score = 4\nspill score"
        result = server._definition({"textDocument": {"uri": "file:///main.mgo"}, "position": {"line": 1, "character": 11}})
        self.assertEqual(result["range"]["start"]["line"], 0)


if __name__ == "__main__":
    unittest.main()
