"""Serve graph.html and regenerate its Mermaid definition from graph.py."""

from __future__ import annotations

import argparse
import json
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
EXECUTION_HISTORY_LIMIT = 20
GRAPH_NODE_ORDER = {
    "__start__": 0,
    "preflight": 1,
    "intake": 2,
    "learning": 3,
    "planning": 4,
    "building": 5,
    "critic_auditor": 6,
    "validation": 7,
    "pre_commit_policy_gate": 8,
    "commit_item": 9,
    "debugger": 10,
    "item_router": 11,
    "push_node": 12,
    "pull_request_node": 13,
    # Recovery nodes rank after the main flow so their loop-back edges (e.g.
    # retry_backoff -> building) style as dashed and their inbound edges solid.
    "retry_backoff": 14,
    "attempt_limit": 15,
    "failed_build": 16,
    "failed_run": 17,
    "stop_run": 18,
    "__end__": 19,
}

VIEW_NODE_LABELS = {
    "__start__": "Start",
    "preflight": "Preflight",
    "intake": "Intake",
    "learning": "Learn codebase",
    "planning": "planning",
    "building": "Build",
    "critic_auditor": "critic_auditor",
    "validation": "Validate",
    "pre_commit_policy_gate": "Policy gate",
    "commit_item": "commit item",
    "debugger": "Debug failure",
    "item_router": "more items",
    "push_node": "push branch",
    "pull_request_node": "open pull request",
    "retry_backoff": "Retry backoff",
    "attempt_limit": "Attempt limit",
    "failed_build": "Failed build",
    "failed_run": "Failed run",
    "stop_run": "Stop run",
    "__end__": "Complete",
}

VIEW_NODE_CLASSES = {
    "__start__": "startNode",
    "preflight": "mainNode",
    "intake": "learningNode",
    "learning": "learningNode",
    "planning": "mainNode",
    "building": "mainNode",
    "critic_auditor": "reviewNode",
    "validation": "decisionNode",
    "pre_commit_policy_gate": "deliveryNode",
    "commit_item": "deliveryNode",
    "item_router": "decisionNode",
    "push_node": "deliveryNode",
    "pull_request_node": "deliveryNode",
    "debugger": "recoveryNode",
    "retry_backoff": "recoveryNode",
    "attempt_limit": "safetyNode",
    "failed_build": "failureNode",
    "failed_run": "failureNode",
    "stop_run": "stopNode",
    "__end__": "endNode",
}
VIEW_MAIN_FLOW = (
    "__start__",
    "preflight",
    "intake",
    "planning",
    "building",
    "validation",
    "pre_commit_policy_gate",
    "commit_item",
    "item_router",
    "push_node",
    "pull_request_node",
    "__end__",
)
VIEW_MAIN_NODES = (
    "__start__",
    "preflight",
    "intake",
    "learning",
    "planning",
    "building",
    "critic_auditor",
    "validation",
    "pre_commit_policy_gate",
    "commit_item",
    "item_router",
    "push_node",
    "pull_request_node",
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
# Partitions the graph's nodes with VIEW_MAIN_NODES; their union is asserted to
# cover create_nodes() in tests/test_viewer.py.
VIEW_RECOVERY_NODES = (
    "debugger",
    "retry_backoff",
    "attempt_limit",
    "failed_build",
    "failed_run",
    "stop_run",
)
VIEW_RECOVERY_EDGES = (
    ("validation", "debugger"),
    ("validation", "debugger"),
    ("debugger", "planning"),
    ("building", "attempt_limit"),
    ("attempt_limit", "__end__"),
    ("building", "failed_build"),
    ("failed_build", "__end__"),
    ("preflight", "__end__"),
    ("stop_run", "__end__"),
)
VIEW_NODE_DECLARATION = re.compile(
    r"^\s*([A-Za-z0-9_]+)(?=\(|\[|\{)",
    re.MULTILINE,
)
VIEW_EDGE = re.compile(
    r"^\s*([A-Za-z0-9_]+)\s+(-\.->|-->)\s+([A-Za-z0-9_]+)",
    re.MULTILINE,
)

_execution_graph = None
_execution_graph_revision = None
# RLock: load_execution_graph() holds this while calling load_graph_module(),
# which re-acquires it itself, so every caller of either function - including
# _send_mermaid(), which goes through load_execution_graph() - is protected
# against the sys.modules["graph_live"] race.
_graph_module_lock = threading.RLock()


def graph_source_files() -> tuple[Path, ...]:
    """Return graph.py and the Python modules that define its nodes."""

    workflow_files = (
        tuple(sorted(WORKFLOW_DIR.glob("*.py"))) if WORKFLOW_DIR.is_dir() else ()
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

    with _graph_module_lock:
        # The viewer process stays alive, so normal imports would keep old node
        # functions cached after workflow/*.py changes.
        for module_name in list(sys.modules):
            if module_name == "workflow" or module_name.startswith("workflow."):
                del sys.modules[module_name]

        source = GRAPH_FILE.read_text(encoding="utf-8")
        module = types.ModuleType("graph_live")
        module.__file__ = str(GRAPH_FILE)
        # dataclasses' string-annotation resolution (from graph.py's `from
        # __future__ import annotations`) looks the module up by name via
        # sys.modules, so an unregistered module breaks @dataclass processing.
        sys.modules[module.__name__] = module
        try:
            exec(compile(source, str(GRAPH_FILE), "exec"), module.__dict__)
        except BaseException:
            del sys.modules[module.__name__]
            raise
        return module


def load_execution_graph():
    """Return the cached compiled graph whose checkpointer holds viewer state."""

    global _execution_graph, _execution_graph_revision

    revision = graph_revision()
    with _graph_module_lock:
        if _execution_graph is None or _execution_graph_revision != revision:
            _execution_graph = load_graph_module().build_graph()
            _execution_graph_revision = revision
        return _execution_graph


def _json_safe(value):
    """Convert checkpoint values into JSON-safe viewer data."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _current_item(values: dict) -> dict:
    """Return the current item from state, including a safe empty fallback."""

    index = values.get("current_item_index")
    items = values.get("prd_items") or []
    selected = {}
    if isinstance(index, int) and 0 <= index < len(items):
        selected = items[index] or {}

    return {
        "id": values.get("current_item_id") or selected.get("id", ""),
        "title": values.get("current_item_title") or selected.get("title", ""),
        "index": index,
    }


def _snapshot_summary(snapshot: object, *, include_manifest: bool = True) -> dict:
    """Flatten a LangGraph state snapshot into data the viewer can render."""

    values = getattr(snapshot, "values", None) or {}
    next_nodes = [str(node) for node in (getattr(snapshot, "next", None) or ())]
    metadata = getattr(snapshot, "metadata", None) or {}
    config = getattr(snapshot, "config", None) or {}
    configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
    model = values.get("assigned_model", "")
    if not model:
        model = values.get("critic_model", "") or values.get("debugger_model", "")

    summary = {
        "checkpoint_id": configurable.get("checkpoint_id"),
        "created_at": _json_safe(getattr(snapshot, "created_at", None)),
        "step": metadata.get("step"),
        "current_node": next_nodes[0] if next_nodes else None,
        "next_nodes": next_nodes,
        "item": _current_item(values),
        "attempt_count": values.get("attempts_count", 0),
        "attempts_count": values.get("attempts_count", 0),
        "total_attempts": values.get("total_attempts", 0),
        "max_total_attempts": values.get("max_total_attempts", 0),
        "total_tokens": values.get("total_tokens", 0),
        "max_tokens": values.get("max_tokens", 0),
        "total_cost_usd": values.get("total_cost_usd", 0.0),
        "max_cost_usd": values.get("max_cost_usd", 0.0),
        "max_runtime_seconds": values.get("max_runtime_seconds", 0),
        "cancel_requested": values.get("cancel_requested", False),
        "last_error": _json_safe(values.get("last_error", "")),
        "model": _json_safe(model),
        "status": _json_safe(values.get("status", "")),
        "run_id": _json_safe(values.get("run_id", "")),
        "run_branch": _json_safe(values.get("run_branch", "")),
        "workspace_directory": _json_safe(values.get("workspace_directory", "")),
        "run_lifecycle_status": _json_safe(values.get("run_lifecycle_status", "")),
        "run_lease_expires_at": values.get("run_lease_expires_at", 0.0),
        "run_last_heartbeat_at": values.get("run_last_heartbeat_at", 0.0),
        "run_recovery_count": values.get("run_recovery_count", 0),
        "repo_drift": _json_safe(values.get("repo_drift", "")),
        "interrupts": [
            {
                "id": _json_safe(getattr(item, "id", "")),
                "value": _json_safe(getattr(item, "value", item)),
            }
            for item in (getattr(snapshot, "interrupts", None) or ())
        ],
    }
    if include_manifest:
        summary["run_manifest"] = _json_safe(values.get("run_manifest", []))
    return summary


def execution_state(
    graph: object, thread_id: str, *, limit: int = EXECUTION_HISTORY_LIMIT
) -> dict:
    """Read the current state and recent checkpoint history for one thread."""

    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    history = [
        _snapshot_summary(checkpoint, include_manifest=False)
        for checkpoint in graph.get_state_history(config, limit=limit)
    ]
    current = _snapshot_summary(snapshot)
    lifecycle_manager = getattr(
        getattr(graph, "checkpointer", None),
        "lifecycle_manager",
        None,
    )
    lifecycle = lifecycle_manager.get_run(thread_id) if lifecycle_manager else None
    if lifecycle is not None:
        current["lifecycle"] = {
            "status": lifecycle.status,
            "started_at": lifecycle.started_at,
            "updated_at": lifecycle.updated_at,
            "finished_at": lifecycle.finished_at,
            "recovery_count": lifecycle.recovery_count,
            "last_error": lifecycle.last_error,
        }
    return {
        "thread_id": thread_id,
        "available": bool(current["checkpoint_id"] or history),
        **current,
        "checkpoint_history": history,
    }


def style_mermaid(content: str, decision_node_ids: set[str]) -> str:
    """Apply the viewer's white-node theme and diamond decision shapes."""

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
    edges = {(source, target) for source, _arrow, target in VIEW_EDGE.findall(content)}
    if not set(VIEW_MAIN_FLOW).issubset(node_ids):
        return style_mermaid(content, decision_node_ids)

    lines = [
        '%%{init: {"flowchart": {"curve": "basis", "nodeSpacing": 34, "rankSpacing": 12, "padding": 14}, "themeVariables": {"fontSize": "14px"}}}%%',
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
                "    direction LR",
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
            "  classDef mainNode fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a8a",
            "  classDef learningNode fill:#ccfbf1,stroke:#0f766e,stroke-width:2px,color:#134e4a",
            "  classDef reviewNode fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#312e81",
            "  classDef decisionNode fill:#fef3c7,stroke:#ca8a04,stroke-width:2px,color:#713f12",
            "  classDef deliveryNode fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#7c2d12",
            "  classDef startNode fill:#e2e8f0,stroke:#475569,stroke-width:2px,color:#1e293b",
            "  classDef endNode fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d",
            "  classDef recoveryNode fill:#faf5ff,stroke:#9333ea,stroke-width:2px,color:#581c87",
            "  classDef safetyNode fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#831843",
            "  classDef failureNode fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d",
            "  classDef stopNode fill:#f1f5f9,stroke:#64748b,stroke-width:2px,color:#334155",
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
        node_class = VIEW_NODE_CLASSES.get(node_id, "decisionNode")
        return f'    {node_id}{{"{label}"}}:::{node_class}'
    node_class = VIEW_NODE_CLASSES.get(
        node_id,
        "mainNode" if node_id in VIEW_MAIN_NODES else "recoveryNode",
    )
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

        if path == "/graph-state":
            self._send_graph_state()
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

    def _send_json(self, payload: dict, status: int = 200) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_graph_state(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        thread_id = query.get("thread_id", [""])[0].strip()
        if not thread_id:
            self._send_json(
                {"error": "thread_id query parameter is required"},
                status=400,
            )
            return

        try:
            limit = int(query.get("limit", [str(EXECUTION_HISTORY_LIMIT)])[0])
            limit = max(1, min(limit, 100))
        except (TypeError, ValueError):
            self._send_json({"error": "limit must be an integer"}, status=400)
            return

        try:
            payload = execution_state(load_execution_graph(), thread_id, limit=limit)
        except Exception as error:  # pragma: no cover - viewer error response
            self._send_json({"error": str(error)}, status=500)
            return

        self._send_json(payload)

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
                    b"event: graph-changed\n" b"data: graph source changed\n\n"
                )
                self.wfile.flush()
                revision = current_revision
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError):
            # The browser closes this connection when the page is closed or reloaded.
            return

    def _send_mermaid(self) -> None:
        try:
            drawable_graph = load_execution_graph().get_graph()
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
            payload = f'graph TD\n  error["{error}"]'.encode("utf-8")
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
