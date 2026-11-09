"""A dependency-free Language Server Protocol implementation for Memingo."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .lexer import Lexer, LexerError
from .parser import ParseError, parse

KEYWORDS = ("vibe", "ritual", "drop", "when", "nah", "grind", "spill", "borrow", "based", "cringe", "ghost")
BUILTINS = (
    "headcount", "whatkind", "json_parse", "json_stringify", "env", "range",
    "keys", "push", "append", "set_value", "delete_key", "random", "random_int",
    "http_get", "http_post", "trim", "split", "join", "sort", "map", "filter",
    "reduce", "sum", "min", "max", "clamp", "parse_int", "parse_float",
    "repeat", "lines", "unique", "meme_case", "shuffle", "uuid", "now", "sleep",
    "read_file", "write_file", "file_exists", "list_files",
)
WORDS = {word: "Palabra clave de Memingo." for word in KEYWORDS}
WORDS.update({word: "Función integrada de la biblioteca estándar de Memingo." for word in BUILTINS})


def _position(source: str, line: int, column: int) -> dict:
    lines = source.splitlines()
    line = max(0, min(line, max(0, len(lines) - 1)))
    character = max(0, min(column, len(lines[line]) if lines else 0))
    return {"line": line, "character": character}


def _diagnostics(source: str) -> list[dict]:
    try:
        parse(source)
        return []
    except (LexerError, ParseError) as exc:
        message = str(exc)
        match = re.search(r"(?:line|línea)\s+(\d+)(?:,?\s*(?:column|columna)\s+(\d+))?", message, re.I)
        line = max(0, int(match.group(1)) - 1) if match else 0
        column = max(0, int(match.group(2)) - 1) if match and match.group(2) else 0
        start = _position(source, line, column)
        end = _position(source, line, column + 1)
        return [{
            "range": {"start": start, "end": end},
            "severity": 1,
            "source": "memingo",
            "message": message[:2000],
        }]


def _symbols(source: str) -> list[dict]:
    result = []
    for match in re.finditer(r"(?m)^\s*(?:vibe|ritual)\s+([A-Za-z_][A-Za-z0-9_]*)", source):
        line = source.count("\n", 0, match.start())
        line_start = source.rfind("\n", 0, match.start()) + 1
        col = match.start(1) - line_start
        result.append({
            "name": match.group(1),
            "line": line,
            "character": col,
            "kind": 12 if source[match.start():].lstrip().startswith("ritual") else 13,
        })
    return result


class MemingoLanguageServer:
    """Small stdio JSON-RPC/LSP server for the Memingo language."""

    def __init__(self, reader=None, writer=None):
        self.reader = reader or sys.stdin.buffer
        self.writer = writer or sys.stdout.buffer
        self.documents: dict[str, str] = {}
        self.shutdown_requested = False

    def send(self, message: dict) -> None:
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.writer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
        self.writer.flush()

    def notify(self, method: str, params: dict) -> None:
        self.send({"jsonrpc": "2.0", "method": method, "params": params})

    def respond(self, request_id, result=None, error=None) -> None:
        payload = {"jsonrpc": "2.0", "id": request_id}
        payload["error" if error else "result"] = error if error else result
        self.send(payload)

    def _document(self, params: dict) -> tuple[str, str]:
        item = params.get("textDocument") or {}
        uri = str(item.get("uri", ""))
        return uri, self.documents.get(uri, "")

    def _publish(self, uri: str) -> None:
        self.notify("textDocument/publishDiagnostics", {
            "uri": uri, "diagnostics": _diagnostics(self.documents.get(uri, "")),
        })

    def _completion(self, params: dict) -> dict:
        _, source = self._document(params)
        labels = list(KEYWORDS) + list(BUILTINS)
        labels += [item["name"] for item in _symbols(source)]
        items = [{"label": label, "kind": 3 if label in BUILTINS else 14,
                  "detail": "Memingo builtin" if label in BUILTINS else "Memingo"}
                 for label in dict.fromkeys(labels)]
        return {"isIncomplete": False, "items": items[:200]}

    def _word_at(line_text: str, character: int):
    for match in re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", line_text):
        if match.start() <= character <= match.end():
            return match.group(0)
    return None


def _hover(self, params: dict):
        uri, source = self._document(params)
        position = (params.get("position") or {})
        line = int(position.get("line", 0))
        character = int(position.get("character", 0))
        lines = source.splitlines()
        if line < 0 or line >= len(lines):
            return None
        tokens = list(re.finditer(r"[A-Za-z_][A-Za-z0-9_]*", lines[line]))
        match = next((item for item in tokens if item.start() <= character <= item.end()), None)
        if match is None and tokens:
            match = min(tokens, key=lambda item: min(abs(character-item.start()), abs(character-item.end())))
        if not match:
            return None
        word = match.group(0)
        if word in WORDS:
            text = f"**{word}**\n\n{WORDS[word]}"
        else:
            symbol = next((s for s in _symbols(source) if s["name"] == word), None)
            if not symbol:
                return None
            text = f"**{word}**\n\nSímbolo declarado en la línea {symbol['line'] + 1}."
        return {"contents": {"kind": "markdown", "value": text}}

    def _definition(self, params: dict):
        uri, source = self._document(params)
        position = params.get("position") or {}
        line = int(position.get("line", 0))
        character = int(position.get("character", 0))
        lines = source.splitlines()
        if line < 0 or line >= len(lines):
            return None
        segment = lines[line]
        name = _word_at(segment, character)
        if not name:
            return None
        symbol = next((s for s in _symbols(source) if s["name"] == name), None)
        if not symbol:
            return None
        start = {"line": symbol["line"], "character": symbol["character"]}
        end = {"line": symbol["line"], "character": symbol["character"] + len(name)}
        return {"uri": uri, "range": {"start": start, "end": end}}

    def handle(self, message: dict) -> bool:
        method = message.get("method")
        params = message.get("params") or {}
        request_id = message.get("id")
        if method == "exit":
            return False
        if method == "initialize":
            self.respond(request_id, {
                "capabilities": {
                    "textDocumentSync": {"openClose": True, "change": 1, "save": {"includeText": True}},
                    "completionProvider": {"triggerCharacters": [".", " "]},
                    "hoverProvider": True,
                    "definitionProvider": True,
                    "documentSymbolProvider": True,
                },
                "serverInfo": {"name": "Memingo Language Server", "version": "0.1.0"},
            })
        elif method == "initialized":
            pass
        elif method == "shutdown":
            self.shutdown_requested = True
            self.respond(request_id, None)
        elif method == "textDocument/didOpen":
            item = params.get("textDocument") or {}
            uri = str(item.get("uri", ""))
            self.documents[uri] = str(item.get("text", ""))
            self._publish(uri)
        elif method == "textDocument/didChange":
            item = params.get("textDocument") or {}
            uri = str(item.get("uri", ""))
            changes = params.get("contentChanges") or []
            if uri and changes and isinstance(changes[-1].get("text"), str):
                self.documents[uri] = changes[-1]["text"]
                self._publish(uri)
        elif method == "textDocument/didSave":
            uri, source = self._document(params)
            if isinstance(params.get("text"), str):
                self.documents[uri] = params["text"]
            self._publish(uri)
        elif method == "textDocument/didClose":
            uri, _ = self._document(params)
            self.documents.pop(uri, None)
            self.notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []})
        elif method == "textDocument/completion":
            self.respond(request_id, self._completion(params))
        elif method == "textDocument/hover":
            self.respond(request_id, self._hover(params))
        elif method == "textDocument/definition":
            self.respond(request_id, self._definition(params))
        elif method == "textDocument/documentSymbol":
            uri, source = self._document(params)
            symbols = []
            for item in _symbols(source):
                start = {"line": item["line"], "character": item["character"]}
                end = {"line": item["line"], "character": item["character"] + len(item["name"])}
                symbols.append({"name": item["name"], "kind": item["kind"],
                                "range": {"start": start, "end": end},
                                "selectionRange": {"start": start, "end": end}})
            self.respond(request_id, symbols)
        elif request_id is not None:
            self.respond(request_id, None, {"code": -32601, "message": f"Method not found: {method}"})
        return True

    def run(self) -> int:
        while True:
            header = self.reader.readline()
            if not header:
                return 0
            if header in (b"\\r\\n", b"\\n"):
                continue
            try:
                headers = {}
                current = header
                while current not in (b"\\r\\n", b"\\n", b""):
                    if b":" in current:
                        name, value = current.split(b":", 1)
                        headers[name.strip().lower()] = value.strip()
                    current = self.reader.readline()
                raw_length = headers.get(b"content-length")
                if raw_length is None:
                    continue
                length = int(raw_length)
                if length < 0 or length > 8 * 1024 * 1024:
                    return 2
                body = self.reader.read(length)
                if len(body) != length:
                    return 2
                message = json.loads(body.decode("utf-8"))
                if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                    continue
                if not self.handle(message):
                    return 0
            except (ValueError, UnicodeError, json.JSONDecodeError):
                continue


def run_language_server() -> int:
    return MemingoLanguageServer().run()
