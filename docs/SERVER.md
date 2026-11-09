# Memingo HTTP Server API

Memingo 0.3 adds a small Python application API alongside the existing static-file server.

## Quick start

A runnable example is included in `examples/api.py`. From the repository root, start it with:

```bash
python -m memingo api examples/api.py
```

Then open `http://127.0.0.1:8000/` or try `/hello/Cris`.

## Create an API

Create `app.py`:

```python
from memingo import MemingoApp, Response, serve_app

app = MemingoApp()

@app.get("/")
def home(request):
    return {"name": "Memingo API", "status": "based"}

@app.get("/users/<user_id>")
def get_user(request):
    return {
        "id": request.params["user_id"],
        "search": request.query,
    }

@app.post("/echo")
def echo(request):
    return Response.json({"received": request.json()})

@app.put("/notes/<note_id>")
def update_note(request):
    data = request.json()
    return Response.json({"id": request.params["note_id"], "note": data})

@app.delete("/notes/<note_id>")
def delete_note(request):
    return Response("", status=204)

@app.use
def add_server_header(request, next_handler):
    response = next_handler()
    response.headers["X-Powered-By"] = "Memingo"
    return response

if __name__ == "__main__":
    serve_app(app, host="127.0.0.1", port=8000)
```

Run it with Python:

```bash
python app.py
```

Or use the Memingo launcher from the project directory:

```bash
memingo api app.py --host 127.0.0.1 --port 8000
```

The launcher imports `app.py`, checks that it exports an `app` instance of `MemingoApp`, and starts the API. The default bind address is local-only (`127.0.0.1`). The API listens on `http://127.0.0.1:8000`. Use `host="0.0.0.0"` only when you intentionally want other devices on your network to reach the server; use an appropriate firewall and do not expose development services to the public internet.

## Routes

- `@app.get(path)`
- `@app.post(path)`
- `@app.put(path)`
- `@app.delete(path)`
- `@app.route(path, methods=("GET", "POST"))`

Path parameters use angle brackets, for example `/users/<user_id>`.

## Request

A route receives a `Request` object:

- `request.method`, `request.path`
- `request.params` for path parameters
- `request.query` for query-string values
- `request.headers`
- `request.body`
- `request.text()`
- `request.json()`

Invalid JSON returns an HTTP 400 response.

## Response

A route can return a string, dictionary, list, `None`, or a `Response`:

- strings become text responses
- dictionaries and lists become JSON responses
- `None` becomes HTTP 204
- `Response.json(data, status=200, headers=None)`
- `Response.text(text, status=200, headers=None)`
- `Response(body, status=200, headers=None, content_type=...)`

Unmatched routes return 404. A matching route with an unsupported method returns 405 and an `Allow` header.

## Middleware

Middleware receives `(request, next_handler)`. Call `next_handler()` to continue to the next middleware and route. Middleware may inspect or modify the response.

## Static files

The existing static server remains available:

```bash
memingo serve public --host 127.0.0.1 --port 8000
```

The route-based API and static-file serving are separate entry points in this first release. Templates, uploads, hot reload, and direct `.mgo` route declarations are still planned.
