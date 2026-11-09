import unittest
from unittest.mock import patch

from memingo.interpreter import Interpreter, RuntimeErrorMemingo
from memingo.parser import parse
from memingo.server import MemingoApp


class FakeRequest:
    def __init__(self, path, method="GET", query=None, body=""):
        self.path = path
        self.method = method
        self.query = query or {}
        self.params = {}
        self.headers = {}
        self.body = body.encode("utf-8")

    def text(self):
        return self.body.decode("utf-8")


class NativeApiTests(unittest.TestCase):
    def setUp(self):
        self.interpreter = Interpreter()

    def test_mgo_ritual_handles_get_route_and_path_parameter(self):
        source = '''
vibe app = api()
ritual greet(request) {
    drop {message: "Hello " + request.params.name}
}
api_get(app, "/hello/<name>", greet)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        self.assertIsInstance(app, MemingoApp)
        response = app.dispatch(FakeRequest("/hello/Cris"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, '{"message": "Hello Cris"}')

    def test_post_route_can_parse_json_body(self):
        source = '''
vibe app = api()
ritual echo(request) {
    vibe data = request_json(request)
    drop {received: data.message}
}
api_post(app, "/echo", echo)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/echo", "POST", body='{"message":"based"}'))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, '{"received": "based"}')

    def test_invalid_json_body_returns_bad_request(self):
        source = '''
vibe app = api()
ritual echo(request) {
    drop request_json(request)
}
api_post(app, "/echo", echo)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/echo", "POST", body="{broken"))
        self.assertEqual(response.status, 400)
        self.assertIn("Request body is not valid JSON", response.body)

    def test_native_middleware_can_add_response_header(self):
        source = '''
vibe app = api()
ritual home(request) {
    drop {status: "ok"}
}
ritual add_header(request, next) {
    vibe response = next()
    response_header(response, "X-Powered-By", "Memingo")
    drop response
}
api_use(app, add_header)
api_get(app, "/", home)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.headers["X-Powered-By"], "Memingo")
        self.assertEqual(response.body, '{"status": "ok"}')

    def test_native_middleware_can_change_status_and_body(self):
        source = '''
vibe app = api()
ritual home(request) {
    drop {status: "original"}
}
ritual customize(request, next) {
    vibe response = next()
    response_status(response, 202)
    response_body(response, "accepted")
    drop response
}
api_use(app, customize)
api_get(app, "/", home)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/"))
        self.assertEqual(response.status, 202)
        self.assertEqual(response.body, "accepted")

    def test_native_middleware_can_short_circuit_route(self):
        source = '''
vibe app = api()
ritual blocked(request, next) {
    drop {error: "blocked"}
}
ritual home(request) {
    drop {status: "should not run"}
}
api_use(app, blocked)
api_get(app, "/", home)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, '{"error": "blocked"}')

    def test_middleware_next_can_only_be_called_once(self):
        source = '''
vibe app = api()
ritual duplicate_next(request, next) {
    next()
    drop next()
}
ritual home(request) {
    drop {status: "ok"}
}
api_use(app, duplicate_next)
api_get(app, "/", home)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/"))
        self.assertEqual(response.status, 500)
        self.assertIn("Internal server error", response.body)

    def test_response_header_rejects_line_breaks(self):
        response = {
            "__memingo_response__": True,
            "status": 200,
            "body": "ok",
            "headers": {},
        }
        with self.assertRaisesRegex(RuntimeErrorMemingo, "cannot contain line breaks"):
            self.interpreter._response_header(response, "X-Test", "safe\r\nInjected: yes")

    def test_response_header_rejects_invalid_names(self):
        response = {
            "__memingo_response__": True,
            "status": 200,
            "body": "ok",
            "headers": {},
        }
        with self.assertRaisesRegex(RuntimeErrorMemingo, "name is invalid"):
            self.interpreter._response_header(response, "X-Test\r\nInjected", "value")

    def test_patch_route_is_available_natively(self):
        source = '''
vibe app = api()
ritual update(request) {
    drop {method: request.method, id: request.params.id}
}
api_patch(app, "/items/<id>", update)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/items/42", "PATCH"))
        self.assertEqual(response.status, 200)
        self.assertEqual(response.body, '{"method": "PATCH", "id": "42"}')

    def test_native_response_json_custom_status_and_headers(self):
        source = '''
vibe app = api()
ritual created(request) {
    drop response_json({id: 7, state: "created"}, 201, {"X-Source": "Memingo"})
}
api_post(app, "/items", created)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/items", "POST"))
        self.assertEqual(response.status, 201)
        self.assertEqual(response.content_type, "application/json; charset=utf-8")
        self.assertEqual(response.headers["X-Source"], "Memingo")
        self.assertEqual(response.body, '{"id": 7, "state": "created"}')

    def test_native_response_text_and_html(self):
        source = '''
vibe app = api()
ritual plain(request) {
    drop response_text("created", 202)
}
ritual page(request) {
    drop response_html("<h1>Hi</h1>")
}
api_get(app, "/plain", plain)
api_get(app, "/page", page)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        plain = app.dispatch(FakeRequest("/plain"))
        page = app.dispatch(FakeRequest("/page"))
        self.assertEqual((plain.status, plain.body), (202, "created"))
        self.assertEqual(page.content_type, "text/html; charset=utf-8")
        self.assertEqual(page.body, "<h1>Hi</h1>")

    def test_native_redirect_response(self):
        source = '''
vibe app = api()
ritual old_page(request) {
    drop response_redirect("/new-page", 308)
}
api_get(app, "/old-page", old_page)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/old-page"))
        self.assertEqual(response.status, 308)
        self.assertEqual(response.headers["Location"], "/new-page")
        self.assertEqual(response.body, "")

    def test_native_error_response(self):
        source = '''
vibe app = api()
ritual missing(request) {
    drop response_error(404, "Item not found")
}
api_get(app, "/missing", missing)
'''
        self.interpreter.run(parse(source))
        app = self.interpreter.global_environment.get("app")
        response = app.dispatch(FakeRequest("/missing"))
        self.assertEqual(response.status, 404)
        self.assertEqual(response.content_type, "application/json; charset=utf-8")
        self.assertEqual(response.body, '{"error": "Item not found", "status": 404}')

    def test_response_helpers_validate_status_and_redirect(self):
        with self.assertRaisesRegex(RuntimeErrorMemingo, "100 to 599"):
            self.interpreter._response_json({}, 700)
        with self.assertRaisesRegex(RuntimeErrorMemingo, "Redirect status"):
            self.interpreter._response_redirect("/new", 200)
        with self.assertRaisesRegex(RuntimeErrorMemingo, "line breaks"):
            self.interpreter._response_redirect("/new\\r\\nX-Evil: yes")

    def test_api_listen_uses_cli_host_and_port_defaults(self):
        app = self.interpreter._api_create()
        self.interpreter.api_host = "127.0.0.1"
        self.interpreter.api_port = 8123
        with patch("memingo.interpreter.serve_app") as start_server:
            self.interpreter._api_listen(app)
        start_server.assert_called_once_with(app, "127.0.0.1", 8123)
        self.assertTrue(self.interpreter.api_server_started)

    def test_api_rejects_invalid_app(self):
        with self.assertRaisesRegex(RuntimeErrorMemingo, "app created by api"):
            self.interpreter._api_route(object(), ("GET",), "/", lambda request: {})


if __name__ == "__main__":
    unittest.main()
