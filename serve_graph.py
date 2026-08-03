"""Serve graph.html and regenerate its Mermaid definition from graph.py."""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_DIR = Path(__file__).parent
GRAPH_FILE = PROJECT_DIR / "graph.py"
SERVER_FILE = Path(__file__).resolve()
WORKFLOW_DIR = PROJECT_DIR / "workflow"
GRAPH_CHECK_INTERVAL_SECONDS = 0.5
GRAPH_NODE_ORDER = {
    "__start__": 0,
    "intake": 1,
    "learning": 2,
    "planning": 3,
    "building": 4,
    "critic_auditor": 5,
    "validation": 6,
    "debugger": 7,
    "item_router": 8,
    "github_node": 9,
    "attempt_limit": 10,
    "__end__": 11,
}

VIEW_NODE_LABELS = {
    "__start__": "Start",
    "intake": "Intake",
    "learning": "Learn codebase",
    "planning": "planning",
    "building": "Build",
    "critic_auditor": "critic_auditor",
    "validation": "Validate",
    "debugger": "Debug failure",
    "item_router": "more items",
    "github_node": "github node",
    "attempt_limit": "Attempt limit",
    "__end__": "Complete",
}
VIEW_MAIN_FLOW = (
    "__start__",
    "intake",
    "planning",
    "building",
    "validation",
    "item_router",
    "github_node",
    "__end__",
)
VIEW_MAIN_NODES = (
    "__start__",
    "intake",
    "learning",
    "planning",
    "building",
    "critic_auditor",
    "validation",
    "item_router",
    "github_node",
    "__end__",
)
VIEW_CRITIC_EDGES = (
    ("building", "critic_auditor", "-->"),
    ("critic_auditor", "building", "-.->"),
)
VIEW_INTAKE_EDGES = (
    ("intake", "learning", "-.->"),
    ("learning", "intake", "-.->"),
)
VIEW_MAIN_RECOVERY_EDGES = (("item_router", "planning"),)
VIEW_RECOVERY_NODES = ("debugger", "attempt_limit")
VIEW_RECOVERY_EDGES = (
    ("validation", "debugger"),
    ("github_node", "debugger"),
    ("debugger", "planning"),
    ("building", "attempt_limit"),
    ("attempt_limit", "__end__"),
)
VIEW_NODE_DECLARATION = re.compile(
    r"^\s*([A-Za-z0-9_]+)(?=\(|\[|\{)",
    re.MULTILINE,
)
VIEW_EDGE = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s+(-\.->|-->)\s+([A-Za-z0-9_]+)",
    re.MULTILINE,
)


def graph_source_files() -> tuple[Path, ...]:
    """Return graph.py and the Python modules that define its nodes."""

    workflow_files = (
        tuple(sorted(WORKFLOW_DIR.glob("*.py")))
        if WORKFLOW_DIR.is_dir()
        else ()
    )
    return (GRAPH_FILE, *workflow_files)


def graph_revision() -> tuple[tuple[str, int, int], ...]:
    """Return a revision signature for all graph source files."""

    revisions = []
    for path in graph_source_files():
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        revisions.append(
            (path.relative_to(PROJECT_DIR).as_posix(), stat.st_mtime_ns, stat.st_size)
        )
    return tuple(revisions)


def server_revision() -> tuple[int, int] | None:
    """Return a revision signature for the running server source."""

    try:
        stat = SERVER_FILE.stat()
    except FileNotFoundError:
        return None
    return stat.st_mtime_ns, stat.st_size


def restart_on_server_change(initial_revision: tuple[int, int]) -> None:
    """Re-exec the viewer when its server source changes."""

    while True:
        time.sleep(GRAPH_CHECK_INTERVAL_SECONDS)
        revision = server_revision()
        if revision is None or revision == initial_revision:
            continue
        os.execv(sys.executable, [sys.executable, *sys.argv])


def load_graph_module() -> types.ModuleType:
    """Load graph.py and workflow modules fresh from source."""

    # The viewer process stays alive, so normal imports would keep old node
    # functions cached after workflow/*.py changes.
    for module_name in list(sys.modules):
        if module_name == "workflow" or module_name.startswith("workflow."):
            del sys.modules[module_name]

    source = GRAPH_FILE.read_text(encoding="utf-8")
    module = types.ModuleType("graph_live")
    module.__file__ = str(GRAPH_FILE)
    exec(compile(source, str(GRAPH_FILE), "exec"), module.__dict__)
    return module


def style_mermaid(content: str, decision_node_ids: set[str]) -> str:
    """Apply the viewer's white-node theme and diamond decision shapes."""

    content = content.replace("graph TD;", "graph LR;")
    content = style_edge_directions(content)

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


def structured_mermaid(
    content: str,
    decision_node_ids: set[str],
    *,
    detailed: bool = False,
) -> str:
    """Build a readable overview, optionally showing recovery paths."""

    node_ids = set(VIEW_NODE_DECLARATION.findall(content))
    edges = {
        (source, target)
        for source, _arrow, target in VIEW_EDGE.findall(content)
    }
    if not set(VIEW_MAIN_FLOW).issubset(node_ids):
        return style_mermaid(content, decision_node_ids)

    lines = [
        "%%{init: {\"flowchart\": {\"curve\": \"basis\", \"nodeSpacing\": 54, \"rankSpacing\": 88}}}%%",
        "flowchart LR",
        '  subgraph main["Main workflow"]',
        "    direction LR",
    ]

    for node_id in VIEW_MAIN_NODES:
        if node_id in node_ids:
            lines.append(_view_node(node_id, decision_node_ids))
    for source, target in zip(VIEW_MAIN_FLOW, VIEW_MAIN_FLOW[1:]):
        if (source, target) in edges:
            lines.append(f"    {source} --> {target}")
    for source, target, arrow in VIEW_CRITIC_EDGES:
        if (source, target) in edges:
            lines.append(f"    {source} {arrow} {target}")
    for source, target, arrow in VIEW_INTAKE_EDGES:
        if (source, target) in edges:
            lines.append(f"    {source} {arrow} {target}")
    for source, target in VIEW_MAIN_RECOVERY_EDGES:
        if (source, target) in edges:
            lines.append(f"    {source} -.-> {target}")
    lines.append("  end")

    if detailed:
        lines.extend(
            [
                '  subgraph recovery["Recovery and safety"]',
                "    direction TB",
            ]
        )
        for node_id in VIEW_RECOVERY_NODES:
            if node_id in node_ids:
                lines.append(_view_node(node_id, decision_node_ids))
        lines.append("  end")

        if any((source, target) in edges for source, target in VIEW_RECOVERY_EDGES):
            lines.extend(
                [
                    "  main -.-> recovery",
                    "  recovery -.-> main",
                ]
            )

    lines.extend(
        [
            "  classDef mainNode fill:#ffffff,stroke:#2563eb,stroke-width:2px,color:#0f172a",
            "  classDef decisionNode fill:#eff6ff,stroke:#2563eb,stroke-width:2px,color:#0f172a",
            "  classDef yellowNode fill:#fef3c7,stroke:#ca8a04,stroke-width:2px,color:#713f12",
            "  classDef startNode fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a",
            "  classDef endNode fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d",
            "  classDef recoveryNode fill:#faf5ff,stroke:#9333ea,stroke-width:2px,color:#581c87",
            "  classDef safetyNode fill:#fff7ed,stroke:#ea580c,stroke-width:2px,color:#7c2d12",
        ]
    )
    return "\n".join(lines) + "\n"


def _view_node(node_id: str, decision_node_ids: set[str]) -> str:
    """Return one consistently labeled node for the structured viewer."""

    label = VIEW_NODE_LABELS.get(node_id, node_id)
    if node_id == "__start__":
        return f'    {node_id}(["{label}"]):::startNode'
    if node_id == "__end__":
        return f'    {node_id}(["{label}"]):::endNode'
    if node_id in {"item_router", *decision_node_ids}:
        node_class = "yellowNode" if node_id == "validation" else "decisionNode"
        return f'    {node_id}{{"{label}"}}:::{node_class}'
    node_class = "safetyNode" if node_id == "attempt_limit" else "recoveryNode"
    if node_id in VIEW_MAIN_NODES:
        node_class = "mainNode"
    if node_id == "github_node":
        node_class = "yellowNode"
    return f'    {node_id}["{label}"]:::{node_class}'


def style_edge_directions(content: str) -> str:
    """Make forward edges solid and edges moving back through the flow dashed."""

    edge_pattern = re.compile(
        r"^(\s*)([A-Za-z0-9_]+)\s+(-\.->|-->)\s+([A-Za-z0-9_]+)(.*)$",
        re.MULTILINE,
    )

    def replace_edge(match: re.Match[str]) -> str:
        source = match.group(2)
        target = match.group(4)
        source_order = GRAPH_NODE_ORDER.get(source)
        target_order = GRAPH_NODE_ORDER.get(target)
        if source_order is None or target_order is None:
            return match.group(0)

        arrow = "-.->" if source_order > target_order else "-->"
        return f"{match.group(1)}{source} {arrow} {target}{match.group(5)}"

    return edge_pattern.sub(replace_edge, content)


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
                    b"data: graph source changed\n\n"
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
            query = parse_qs(urlparse(self.path).query)
            detailed = query.get("mode", ["overview"])[0] == "detail"
            content = structured_mermaid(
                drawable_graph.draw_mermaid(),
                decision_node_ids,
                detailed=detailed,
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

    initial_revision = server_revision()
    if initial_revision is not None:
        threading.Thread(
            target=restart_on_server_change,
            args=(initial_revision,),
            daemon=True,
        ).start()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), GraphRequestHandler)
    server.daemon_threads = True
    print(f"Open http://127.0.0.1:{args.port}/graph.html")
    print(
        "The viewer updates when graph.py or workflow/*.py changes; "
        "serve_graph.py reloads itself when edited."
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping graph viewer.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
