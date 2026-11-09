import io
import unittest

from memingo.server import MemingoApp, Request, RequestTooLargeError, Response


class FakeRequest:
    def __init__(self, path, method="GET"):
        self.path = path
        self.method = method
        self.params = {}


class MemingoServerTests(unittest.TestCase):
    def setUp(self):
        self.app = MemingoApp()

        @self.app.get("/hello/<name>")
        def hello(request):
            return {"message": "Hello " + request.params["name"]}

    def test_route_parameter_and_json_response(self):
        response = self.app.dispatch(FakeRequest("/hello/Cris"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "application/json; charset=utf-8")
        self.assertEqual(response.body, '{"message": "Hello Cris"}')

    def test_method_not_allowed(self):
        response = self.app.dispatch(FakeRequest("/hello/Cris", "POST"))
        self.assertEqual(response.status, 405)
        self.assertIn("GET", response.headers["Allow"])

    def test_not_found(self):
        response = self.app.dispatch(FakeRequest("/missing"))
        self.assertEqual(response.status, 404)

    def test_middleware_wraps_handler(self):
        app = MemingoApp()
        seen = []

        @app.use
        def middleware(request, next_handler):
            seen.append("before")
            response = next_handler()
            seen.append("after")
            response.headers["X-Memingo"] = "middleware"
            return response

        @app.get("/ping")
        def ping(request):
            return Response.text("pong")

        response = app.dispatch(FakeRequest("/ping"))
        self.assertEqual(response.body, "pong")
        self.assertEqual(seen, ["before", "after"])
        self.assertEqual(response.headers["X-Memingo"], "middleware")

    def test_handler_errors_return_safe_500_response(self):
        app = MemingoApp()

        @app.get("/broken")
        def broken(request):
            raise RuntimeError("private implementation detail")

        response = app.dispatch(FakeRequest("/broken"))
        self.assertEqual(response.status, 500)
        self.assertEqual(response.body, '{"error": "Internal server error"}')
        self.assertNotIn("private implementation detail", response.body)

    def test_value_error_returns_bad_request(self):
        app = MemingoApp()

        @app.get("/invalid")
        def invalid(request):
            raise ValueError("invalid input")

        response = app.dispatch(FakeRequest("/invalid"))
        self.assertEqual(response.status, 400)
        self.assertIn("invalid input", response.body)

    def test_response_rejects_invalid_status(self):
        with self.assertRaises(ValueError):
            Response("bad", status=700)

    def test_response_rejects_header_injection(self):
        with self.assertRaisesRegex(ValueError, "line breaks"):
            Response("ok", headers={"X-Test": "safe\r\nInjected: yes"})

    def test_response_rejects_invalid_header_name(self):
        with self.assertRaisesRegex(ValueError, "header name"):
            Response("ok", headers={"X-Test\r\nInjected": "value"})

    def test_urlencoded_request_form(self):
        body = b"name=Cris&tag=one&tag=two"
        handler = type("Handler", (), {
            "command": "POST",
            "path": "/submit",
            "headers": {"Content-Length": str(len(body)), "Content-Type": "application/x-www-form-urlencoded"},
            "rfile": io.BytesIO(body),
        })()
        request = Request(handler)
        self.assertEqual(request.form(), {"name": "Cris", "tag": ["one", "two"]})
        self.assertEqual(request.files(), [])

    def test_multipart_request_parses_fields_and_sanitizes_filename(self):
        boundary = "MGO-BOUNDARY"
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="title"\r\n\r\n'
            "hello\r\n"
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="asset"; filename="../folder\\\\unsafe.txt"\r\n'
            "Content-Type: text/plain\r\n\r\n"
            "sample bytes\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8")
        handler = type("Handler", (), {
            "command": "POST",
            "path": "/upload",
            "headers": {"Content-Length": str(len(body)), "Content-Type": f"multipart/form-data; boundary={boundary}"},
            "rfile": io.BytesIO(body),
        })()
        request = Request(handler)
        self.assertEqual(request.form(), {"title": "hello"})
        files = request.files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0]["filename"], "unsafe.txt")
        self.assertEqual(files[0]["data"], b"sample bytes")
        self.assertEqual(files[0]["field"], "asset")

    def test_multipart_upload_size_limit(self):
        boundary = "MGO-LIMIT"
        payload = b"x" * (5 * 1024 * 1024 + 1)
        body = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="asset"; filename="large.bin"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
        handler = type("Handler", (), {
            "command": "POST",
            "path": "/upload",
            "headers": {"Content-Length": str(len(body)), "Content-Type": f"multipart/form-data; boundary={boundary}"},
            "rfile": io.BytesIO(body),
        })()
        with self.assertRaises(RequestTooLargeError):
            Request(handler).form()

    def test_route_validation(self):
        with self.assertRaises(ValueError):
            self.app.get("missing-slash")


if __name__ == "__main__":
    unittest.main()
