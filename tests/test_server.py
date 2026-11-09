import unittest

from memingo.server import MemingoApp, Response


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
            return "pong"

        response = app.dispatch(FakeRequest("/ping"))
        self.assertEqual(response.body, "pong")
        self.assertEqual(seen, ["before", "after"])
        self.assertEqual(response.headers["X-Memingo"], "middleware")

    def test_route_validation(self):
        with self.assertRaises(ValueError):
            self.app.get("missing-slash")


if __name__ == "__main__":
    unittest.main()
