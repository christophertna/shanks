"""Serve graph.html and regenerate its Mermaid definition from graph.py."""

from __future__ import annotations

import argparse
import importlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import graph


PROJECT_DIR = Path(__file__).parent


class GraphRequestHandler(BaseHTTPRequestHandler):
    """Serve the viewer and the current compiled LangGraph definition."""

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        path = urlparse(self.path).path

        if path in {"/", "/graph.html"}:
            self._send_file(PROJECT_DIR / "graph.html", "text/html; charset=utf-8")
            return

        if path == "/graph.mmd":
            self._send_mermaid()
            return

        self.send_error(404)

    def _send_file(self, file_path: Path, content_type: str) -> None:
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_mermaid(self) -> None:
        try:
            current_graph = importlib.reload(graph).build_graph()
            content = current_graph.get_graph().draw_mermaid()
            payload = content.encode("utf-8")
            self.send_response(200)
        except Exception as error:  # pragma: no cover - viewer error response
            payload = f"graph TD\n  error[\"{error}\"]".encode("utf-8")
            self.send_response(500)

        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        print(f"graph-viewer: {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the LangGraph viewer.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), GraphRequestHandler)
    print(f"Open http://127.0.0.1:{args.port}/graph.html")
    print("The viewer refreshes the graph definition every 1.5 seconds.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping graph viewer.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
