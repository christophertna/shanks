"""Serve graph.html and regenerate its Mermaid definition from graph.py."""

from __future__ import annotations

import argparse
import importlib
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import graph


PROJECT_DIR = Path(__file__).parent


def style_mermaid(content: str, decision_node_ids: set[str]) -> str:
    """Apply the viewer's white-node theme and diamond decision shapes."""

    content = content.replace(
        "classDef default fill:#f2f0ff,line-height:1.2",
        "classDef default fill:#ffffff,stroke:#334155,stroke-width:1.5px,color:#111827,line-height:1.2",
    )
    content = content.replace(
        "classDef first fill-opacity:0",
        "classDef first fill:#ffffff,stroke:#334155,stroke-width:1.5px,color:#111827",
    )
    content = content.replace(
        "classDef last fill:#bfb6fc",
        "classDef last fill:#ffffff,stroke:#334155,stroke-width:1.5px,color:#111827",
    )

    for node_id in decision_node_ids:
        node_pattern = re.compile(
            rf"^(\s*{re.escape(node_id)})\((.*)\)$",
            re.MULTILINE,
        )
        content = node_pattern.sub(
            lambda match: f"{match.group(1)}{{{match.group(2)}}}",
            content,
        )

    return content


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
            drawable_graph = current_graph.get_graph()
            decision_node_ids = {
                node.id
                for node in drawable_graph.nodes.values()
                if (node.metadata or {}).get("kind") == "decision"
            }
            content = style_mermaid(
                drawable_graph.draw_mermaid(),
                decision_node_ids,
            )
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
