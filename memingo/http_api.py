"""Lightweight HTTP API server for Memingo development projects."""
import hmac
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit


class MemingoAPIServer:
    MAX_BODY = 1_048_576

    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.routes = {}
        self.middleware = []
        self.httpd = None
        self.thread = None
        self.lock = threading.RLock()

    def _register(self, method, path, handler):
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("Route path must start with '/'")
        if not callable(handler) and not hasattr(handler, "call"):
            raise ValueError("Route handler must be a Memingo ritual")
        names = re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", path)
        if len(names) != len(set(names)):
            raise ValueError("Route parameter names must be unique")
        parts = re.split(r"(\{[A-Za-z_][A-Za-z0-9_]*\})", path)
        pattern_parts = []
        for part in parts:
            if part.startswith("{") and part.endswith("}"):
                pattern_parts.append("([^/]+)")
            else:
                pattern_parts.append(re.escape(part))
        pattern = "".join(pattern_parts)
        self.routes[(method, path)] = (re.compile("^" + pattern + "$"), names, handler)
        return self

    def get(self, path, handler): return self._register("GET", path, handler)
    def post(self, path, handler): return self._register("POST", path, handler)
    def put(self, path, handler): return self._register("PUT", path, handler)
    def patch(self, path, handler): return self._register("PATCH", path, handler)
    def delete(self, path, handler): return self._register("DELETE", path, handler)

    def use(self, handler):
        if not callable(handler) and not hasattr(handler, "call"):
            raise ValueError("Middleware must be a Memingo ritual")
        self.middleware.append(handler)
        return self

    def bearer(self, expected_token):
        if not isinstance(expected_token, str) or not expected_token:
            raise ValueError("Bearer token must be a non-empty string")

        def authenticate(request):
            authorization = next(
                (value for key, value in request["headers"].items()
                 if key.lower() == "authorization"),
                "",
            )
            scheme, _, supplied = authorization.partition(" ")
            if scheme.lower() != "bearer" or not hmac.compare_digest(supplied, expected_token):
                return {
                    "status": 401,
                    "headers": {"WWW-Authenticate": "Bearer"},
                    "body": {"error": "Unauthorized"},
                }
            return None

        return authenticate

    def _find_route(self, method, path):
        matching = [
            (route_path, pattern, names, handler)
            for (route_method, route_path), (pattern, names, handler) in self.routes.items()
            if route_method == method
        ]
        matching.sort(key=lambda item: item[0].count("{"))
        for route_path, pattern, names, handler in matching:
            match = pattern.match(path)
            if match:
                return handler, {
                    name: unquote(value)
                    for name, value in zip(names, match.groups())
                }
        return None, {}

    def _dispatch(self, method, target, headers=None, body=b""):
        parsed = urlsplit(target)
        handler, params = self._find_route(method, parsed.path)
        if handler is None:
            return 404, {"Content-Type": "application/json; charset=utf-8"}, {
                "error": "Not found"
            }
        try:
            raw_body = body.decode("utf-8") if body else ""
            try:
                payload = json.loads(raw_body) if raw_body else None
            except json.JSONDecodeError:
                payload = raw_body
            request = {
                "method": method,
                "path": parsed.path,
                "params": params,
                "query": {
                    key: values[-1] if len(values) == 1 else values
                    for key, values in parse_qs(
                        parsed.query, keep_blank_values=True
                    ).items()
                },
                "headers": dict(headers or {}),
                "body": payload,
            }
            with self.lock:
                for middleware in self.middleware:
                    result = self.interpreter._invoke(
                        middleware, [request], "HTTP middleware"
                    )
                    if result is None:
                        continue
                    if not isinstance(result, dict):
                        raise ValueError("Middleware must return an object or ghost")
                    if "status" in result or "body" in result:
                        return self._encode_response(result)
                    request.update(result)
                response = self.interpreter._invoke(handler, [request], "HTTP route")
            if not isinstance(response, dict):
                response = {"body": response}
            return self._encode_response(response)
        except Exception:
            return 500, {"Content-Type": "application/json; charset=utf-8"}, {
                "error": "Internal server error"
            }

    @staticmethod
    def _encode_response(response):
        status = response.get("status", 200)
        if not isinstance(status, int) or isinstance(status, bool) or not 100 <= status <= 599:
            raise ValueError("Response status must be an HTTP status code")
        response_headers = response.get("headers", {})
        if not isinstance(response_headers, dict):
            raise ValueError("Response headers must be an object")
        content = response.get("body")
        content_type = next(
            (value for key, value in response_headers.items()
             if str(key).lower() == "content-type"),
            "application/json; charset=utf-8",
        )
        if isinstance(content, (dict, list)) or content is None:
            encoded = json.dumps(content, ensure_ascii=False).encode("utf-8")
        else:
            encoded = str(content).encode("utf-8")
            if not any(str(key).lower() == "content-type" for key in response_headers):
                content_type = "text/plain; charset=utf-8"
        safe_headers = {"Content-Type": str(content_type)}
        for key, value in response_headers.items():
            key, value = str(key), str(value)
            if key.lower() in ("content-length", "connection", "transfer-encoding"):
                continue
            if any(char in key + value for char in "\r\n"):
                raise ValueError("Response headers cannot contain newlines")
            safe_headers[key] = value
        return status, safe_headers, encoded

    def start(self, host="127.0.0.1", port=8000):
        if self.httpd is not None:
            raise ValueError("Server is already running")
        if not isinstance(host, str) or not host:
            raise ValueError("Host must be a non-empty string")
        if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
            raise ValueError("Port must be between 0 and 65535")
        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "MemingoAPI/1.1"

            def _handle(self):
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                except ValueError:
                    self.send_error(400, "Invalid Content-Length")
                    return
                if length < 0 or length > api.MAX_BODY:
                    self.send_error(413, "Request body too large")
                    return
                body = self.rfile.read(length) if length else b""
                status, headers, response = api._dispatch(
                    self.command, self.path, self.headers, body
                )
                if isinstance(response, dict):
                    response = json.dumps(response, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            do_GET = _handle
            do_POST = _handle
            do_PUT = _handle
            do_PATCH = _handle
            do_DELETE = _handle

            def log_message(self, *_args):
                pass

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return {"host": host, "port": self.httpd.server_address[1]}

    def stop(self):
        if self.httpd is None:
            return False
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        self.httpd = None
        self.thread = None
        return True

    def listen(self, host="127.0.0.1", port=8000):
        address = self.start(host, port)
        print(f"Memingo API listening at http://{address['host']}:{address['port']}")
        try:
            self.thread.join()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def api(self):
        return {
            "get": self.get, "post": self.post, "put": self.put,
            "patch": self.patch, "delete": self.delete,
            "use": self.use, "bearer": self.bearer,
            "start": self.start, "stop": self.stop, "listen": self.listen,
        }
