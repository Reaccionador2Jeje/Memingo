"""Memingo HTTP application server with routes, request/response helpers and middleware."""
import json
import re
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


MAX_REQUEST_BODY_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_FILE_SIZE = 5 * 1024 * 1024


class RequestTooLargeError(Exception):
    """Raised when a request or uploaded file exceeds its configured limit."""



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
        self._form_cache = None
        self._files_cache = None

    def text(self, encoding="utf-8", errors="strict"):
        return self.body.decode(encoding, errors=errors)

    def form(self):
        """Parse URL-encoded or multipart form fields."""
        if self._form_cache is not None:
            return self._form_cache
        content_type = self.headers.get("Content-Type", "")
        if content_type.lower().startswith("application/x-www-form-urlencoded"):
            parsed = parse_qs(self.text(errors="replace"), keep_blank_values=True)
            self._form_cache = {
                key: values[-1] if len(values) == 1 else values
                for key, values in parsed.items()
            }
            self._files_cache = []
            return self._form_cache
        if not content_type.lower().startswith("multipart/form-data"):
            self._form_cache = {}
            self._files_cache = []
            return self._form_cache

        header = (
            "Content-Type: " + content_type + "\r\n"
            "MIME-Version: 1.0\r\n\r\n"
        ).encode("utf-8")
        message = BytesParser(policy=email_policy).parsebytes(header + self.body)
        if not message.is_multipart():
            raise ValueError("Malformed multipart form data")

        fields = {}
        files = []
        for part in message.iter_parts():
            if part.get_content_disposition() != "form-data":
                continue
            field_name = part.get_param("name", header="content-disposition")
            if not isinstance(field_name, str) or not field_name:
                continue
            raw_filename = part.get_filename()
            payload = part.get_payload(decode=True) or b""
            if raw_filename is not None:
                filename = raw_filename.replace("\\", "/").split("/")[-1]
                if len(payload) > MAX_UPLOAD_FILE_SIZE:
                    raise RequestTooLargeError("Uploaded file exceeds the 5 MB limit")
                files.append({
                    "field": field_name,
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "size": len(payload),
                    "data": payload,
                })
                continue
            charset = part.get_content_charset() or "utf-8"
            value = payload.decode(charset, errors="replace")
            if field_name in fields:
                if not isinstance(fields[field_name], list):
                    fields[field_name] = [fields[field_name]]
                fields[field_name].append(value)
            else:
                fields[field_name] = value

        self._form_cache = fields
        self._files_cache = files
        return fields

    def files(self):
        if self._files_cache is None:
            self.form()
        return list(self._files_cache or [])

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
        if not isinstance(status, int) or isinstance(status, bool) or not 100 <= status <= 599:
            raise ValueError("Response status must be an integer from 100 to 599")
        if headers is not None and not isinstance(headers, dict):
            raise TypeError("Response headers must be a dictionary")
        safe_headers = {}
        for name, value in (headers or {}).items():
            name = str(name)
            value = str(value)
            if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
                raise ValueError("Invalid HTTP response header name")
            if "\r" in value or "\n" in value:
                raise ValueError("HTTP response header values cannot contain line breaks")
            safe_headers[name] = value
        if not isinstance(content_type, str) or "\r" in content_type or "\n" in content_type:
            raise ValueError("Invalid HTTP response content type")
        self.body = body
        self.status = status
        self.headers = safe_headers
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

        def normalize(result):
            if isinstance(result, Response):
                return result
            if isinstance(result, (dict, list)):
                return Response.json(result)
            if result is None:
                return Response("", 204)
            return Response.text(result)

        def invoke(index):
            if index >= len(self.middleware):
                return normalize(function(request))
            return normalize(self.middleware[index](request, lambda: invoke(index + 1)))

        try:
            return invoke(0)
        except RequestTooLargeError as exc:
            return Response.json({"error": str(exc)}, 413)
        except ValueError as exc:
            return Response.json({"error": str(exc)}, 400)
        except Exception:
            # Do not leak application internals or tracebacks to HTTP clients.
            return Response.json({"error": "Internal server error"}, 500)


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
            try:
                content_length = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                self._send_response(Response.json({"error": "Invalid Content-Length"}, 400))
                return
            if content_length < 0:
                self._send_response(Response.json({"error": "Invalid Content-Length"}, 400))
                return
            if content_length > MAX_REQUEST_BODY_SIZE:
                self._send_response(Response.json({"error": "Request body too large"}, 413))
                return
            request = Request(self)
            response = app.dispatch(request)
            self._send_response(response)

        def _send_response(self, response):
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
