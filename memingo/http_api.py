"""Small, project-scriptable HTTP API server for Memingo."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class MemingoAPIServer:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.routes = {}
        self.httpd = None
        self.thread = None
        self.lock = threading.RLock()

    def _register(self, method, path, handler):
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError("Route path must start with '/'")
        if not callable(handler) and not hasattr(handler, "call"):
            raise ValueError("Route handler must be a Memingo ritual")
        self.routes[(method, path)] = handler
        return self

    def get(self, path, handler):
        return self._register("GET", path, handler)

    def post(self, path, handler):
        return self._register("POST", path, handler)

    def put(self, path, handler):
        return self._register("PUT", path, handler)

    def delete(self, path, handler):
        return self._register("DELETE", path, handler)

    def _dispatch(self, method, target, headers=None, body=b""):
        parsed = urlsplit(target)
        route = self.routes.get((method, parsed.path))
        if route is None:
            return 404, {"Content-Type": "application/json; charset=utf-8"}, {"error": "Not found"}
        try:
            raw_body = body.decode("utf-8") if body else ""
            try:
                payload = json.loads(raw_body) if raw_body else None
            except json.JSONDecodeError:
                payload = raw_body
            request = {
                "method": method,
                "path": parsed.path,
                "query": {key: values[-1] if len(values) == 1 else values
                          for key, values in parse_qs(parsed.query, keep_blank_values=True).items()},
                "headers": dict(headers or {}),
                "body": payload,
            }
            with self.lock:
                response = self.interpreter._invoke(route, [request], "HTTP route")
            if not isinstance(response, dict):
                response = {"body": response}
            status = response.get("status", 200)
            if not isinstance(status, int) or not 100 <= status <= 599:
                raise ValueError("Response status must be an HTTP status code")
            response_headers = response.get("headers", {})
            if not isinstance(response_headers, dict):
                raise ValueError("Response headers must be an object")
            response_body = response.get("body", None)
            content_type = response_headers.get("Content-Type", "application/json; charset=utf-8")
            if isinstance(response_body, (dict, list)) or response_body is None:
                encoded = json.dumps(response_body, ensure_ascii=False).encode("utf-8")
            else:
                encoded = str(response_body).encode("utf-8")
                if "Content-Type" not in response_headers:
                    content_type = "text/plain; charset=utf-8"
            safe_headers = {"Content-Type": content_type}
            for key, value in response_headers.items():
                if key.lower() not in ("content-length", "connection", "transfer-encoding"):
                    safe_headers[str(key)] = str(value)
            return status, safe_headers, encoded
        except Exception as error:
            message = str(error)
            return 500, {"Content-Type": "application/json; charset=utf-8"}, {
                "error": "Internal server error", "message": message
            }

    def start(self, host="127.0.0.1", port=8000):
        if self.httpd is not None:
            raise ValueError("Server is already running")
        if not isinstance(host, str) or not host:
            raise ValueError("Host must be a non-empty string")
        if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
            raise ValueError("Port must be between 0 and 65535")

        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "MemingoAPI/1.0"

            def _handle(self):
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length > 1_048_576:
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
            "delete": self.delete, "start": self.start,
            "stop": self.stop, "listen": self.listen,
        }
