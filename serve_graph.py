"""Serve graph.html and regenerate its Mermaid definition from graph.py."""

from __future__ import annotations

import argparse
import re
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_DIR = Path(__file__).parent
GRAPH_FILE = PROJECT_DIR / "graph.py"
GRAPH_CHECK_INTERVAL_SECONDS = 0.5


def graph_revision() -> tuple[int, int]:
    """Return a lightweight revision signature for graph.py."""

    stat = GRAPH_FILE.stat()
    return stat.st_mtime_ns, stat.st_size


def load_graph_module() -> types.ModuleType:
    """Load graph.py directly from source, bypassing Python bytecode caches."""

    source = GRAPH_FILE.read_text(encoding="utf-8")
    module = types.ModuleType("graph_live")
    module.__file__ = str(GRAPH_FILE)
    exec(compile(source, str(GRAPH_FILE), "exec"), module.__dict__)
    return module


def style_mermaid(content: str, decision_node_ids: set[str]) -> str:
    """Apply the viewer's white-node theme and diamond decision shapes."""

    # LangGraph includes node metadata in labels; keep it for styling, not display.
    content = content.replace(
        "<hr/><small><em>kind = decision</em></small>",
        "",
    )
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

        if path == "/graph-events":
            self._send_graph_events()
            return

        self.send_error(404)

    def _send_file(self, file_path: Path, content_type: str) -> None:
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_graph_events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            revision = graph_revision()
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()

            while True:
                time.sleep(GRAPH_CHECK_INTERVAL_SECONDS)
                current_revision = graph_revision()
                if current_revision == revision:
                    continue

                self.wfile.write(
                    b"event: graph-changed\n"
                    b"data: graph.py changed\n\n"
                )
                self.wfile.flush()
                revision = current_revision
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            # The browser closes this connection when the page is closed or reloaded.
            return

    def _send_mermaid(self) -> None:
        try:
            current_graph = load_graph_module().build_graph()
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
        self.send_header("Cache-Control", "no-store")
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
    server.daemon_threads = True
    print(f"Open http://127.0.0.1:{args.port}/graph.html")
    print("The viewer updates only when graph.py changes.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping graph viewer.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
