"""Example Memingo API application.

Run from the repository root:
    python -m memingo api examples/api.py
"""

from memingo import MemingoApp, Response

app = MemingoApp()


@app.get("/")
def home(request):
    return {
        "name": "Memingo API",
        "status": "ready",
        "version": "0.3",
    }


@app.get("/hello/<name>")
def hello(request):
    return {"message": f"Hello, {request.params['name']}!"}


@app.post("/echo")
def echo(request):
    return Response.json({"received": request.json()})


@app.use
def powered_by_memingo(request, next_handler):
    response = next_handler()
    response.headers["X-Powered-By"] = "Memingo"
    return response
