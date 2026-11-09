"""Memingo HTTP application server with routes, request/response helpers and middleware."""
import json
import re
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


class Request:
    """An incoming HTTP request."""

    def __init__(self, handler, params=None):
        self.method = handler.command.upper()
        parsed = urlsplit(handler.path)
        self.path = parsed.path
        self.query = {key: values[-1] if len(values) == 1 else values
                      for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
        self.params = dict(params or {})
        self.headers = dict(handler.headers.items())
        self.body = handler.rfile.read(int(handler.headers.get("Content-Length", "0") or 0))

    def text(self, encoding="utf-8"):
        return self.body.decode(encoding)

    def json(self):
        if not self.body:
            return {}
        try:
            return json.loads(self.text())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Request body is not valid JSON") from exc


class Response:
    """An HTTP response returned by a Memingo route."""

    def __init__(self, body="", status=200, headers=None, content_type="text/plain; charset=utf-8"):
        self.body = body
        self.status = int(status)
        self.headers = dict(headers or {})
        self.content_type = content_type

    @classmethod
    def json(cls, value, status=200, headers=None):
        return cls(json.dumps(value, ensure_ascii=False), status, headers,
                   "application/json; charset=utf-8")

    @classmethod
    def text(cls, value, status=200, headers=None):
        return cls(str(value), status, headers, "text/plain; charset=utf-8")


class MemingoApp:
    """Small route-based HTTP application."""

    def __init__(self):
        self.routes = []
        self.middleware = []

    def route(self, path, methods=("GET",), handler=None):
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("Route paths must start with '/'")
        if isinstance(methods, str):
            methods = (methods,)
        methods = tuple(dict.fromkeys(str(method).upper() for method in methods))
        if not methods or any(not method.isalpha() for method in methods):
            raise ValueError("Route methods must be valid HTTP method names")

        def register(function):
            if not callable(function):
                raise TypeError("Route handler must be callable")
            pattern_text = re.escape(path)
            pattern_text = re.sub(
                r"<([a-zA-Z_][a-zA-Z0-9_]*)>",
                r"(?P<\1>[^/]+)", pattern_text
            )
            self.routes.append((path, methods, re.compile("^" + pattern_text + "$"), function))
            return function

        return register(handler) if handler is not None else register

    def get(self, path, handler=None):
        return self.route(path, ("GET",), handler)

    def post(self, path, handler=None):
        return self.route(path, ("POST",), handler)

    def put(self, path, handler=None):
        return self.route(path, ("PUT",), handler)

    def delete(self, path, handler=None):
        return self.route(path, ("DELETE",), handler)

    def use(self, middleware):
        if not callable(middleware):
            raise TypeError("Middleware must be callable")
        self.middleware.append(middleware)
        return middleware

    def dispatch(self, request):
        allowed = set()
        selected = None
        for path, methods, pattern, function in self.routes:
            match = pattern.match(request.path)
            if match:
                allowed.update(methods)
                if request.method in methods:
                    selected = (function, match.groupdict())
                    break
        if selected is None:
            if allowed:
                return Response.text("Method not allowed", 405, {"Allow": ", ".join(sorted(allowed))})
            return Response.text("Not found", 404)

        function, params = selected
        request.params = params

        def invoke(index):
            if index >= len(self.middleware):
                return function(request)
            return self.middleware[index](request, lambda: invoke(index + 1))

        try:
            result = invoke(0)
        except ValueError as exc:
            return Response.json({"error": str(exc)}, 400)
        if isinstance(result, Response):
            return result
        if isinstance(result, (dict, list)):
            return Response.json(result)
        if result is None:
            return Response("", 204)
        return Response.text(result)


def serve_app(app, host="127.0.0.1", port=8000):
    """Serve a MemingoApp until interrupted."""
    if not isinstance(app, MemingoApp):
        raise TypeError("serve_app() requires a MemingoApp instance")

    class Handler(BaseHTTPRequestHandler):
        server_version = "MemingoServer/0.3"

        def do_GET(self): self._dispatch()
        def do_POST(self): self._dispatch()
        def do_PUT(self): self._dispatch()
        def do_PATCH(self): self._dispatch()
        def do_DELETE(self): self._dispatch()
        def do_OPTIONS(self): self._dispatch()
        def do_HEAD(self): self._dispatch()

        def _dispatch(self):
            request = Request(self)
            response = app.dispatch(request)
            payload = response.body if isinstance(response.body, bytes) else str(response.body).encode("utf-8")
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("Content-Length", str(len(payload)))
            for key, value in response.headers.items():
                self.send_header(str(key), str(value))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer((host, int(port)), Handler)
    server.daemon_threads = True
    print(f"Memingo API serving at http://{host}:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMemingo API stopped.")
    finally:
        server.server_close()


class MemingoHandler(SimpleHTTPRequestHandler):
    server_version = "MemingoServer/0.2"


def serve(directory=".", host="127.0.0.1", port=8000):
    root = Path(directory).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory does not exist: {root}")

    class Handler(MemingoHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

    server = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"Memingo serving {root} at http://{host}:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
