from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class MemingoHandler(SimpleHTTPRequestHandler):
    server_version = "MemingoServer/0.2"


def serve(directory=".", host="127.0.0.1", port=8000):
    root = Path(directory).resolve()
    if not root.exists():
        raise ValueError(f"Directory does not exist: {root}")

    class Handler(MemingoHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Memingo serving {root} at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()
