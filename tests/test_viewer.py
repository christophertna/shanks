import unittest
import os
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from langgraph.checkpoint.memory import InMemorySaver

from graph import build_graph as compile_graph
from serve_graph import (
    execution_state,
    load_graph_module,
    structured_mermaid,
    style_mermaid,
)
from workflow.adapters import StubAgentAdapter
from workflow.nodes import NodeDependencies


def build_graph(*args, **kwargs):
    """Keep viewer topology tests isolated from the shared production store."""

    kwargs.setdefault("checkpointer", InMemorySaver())
    return compile_graph(*args, **kwargs)


def stub_dependencies() -> NodeDependencies:
    return NodeDependencies(
        planner=StubAgentAdapter("planner", "planner"),
        builder=StubAgentAdapter("builder", "builder"),
        critic=StubAgentAdapter("critic", "critic"),
        validator=StubAgentAdapter("validator", "validator"),
        debugger=StubAgentAdapter("debugger", "debugger"),
    )


class GraphViewerTests(unittest.TestCase):
    def test_viewer_refreshes_after_server_reconnect(self) -> None:
        content = (Path(__file__).parents[1] / "graph.html").read_text(encoding="utf-8")

        self.assertIn('graphEvents.addEventListener("open"', content)
        self.assertIn('lastDefinition = "";', content)
        self.assertIn('id="thread-id"', content)
        self.assertIn('id="execution-budget"', content)
        self.assertIn("fetch(`/graph-state?", content)
        self.assertIn("Checkpoint history", content)
        self.assertIn("Run manifest", content)
        self.assertIn('<details class="execution-shell" open>', content)
        self.assertIn('<summary class="execution-header">', content)

    def test_execution_state_reads_current_snapshot_and_history(self) -> None:
        current = SimpleNamespace(
            values={
                "current_item_id": "item-2",
                "current_item_title": "Second item",
                "current_item_index": 1,
                "prd_items": [{"id": "item-2", "title": "Second item"}],
                "attempts_count": 2,
                "total_attempts": 3,
                "max_total_attempts": 20,
                "total_tokens": 120,
                "max_tokens": 1000,
                "total_cost_usd": 0.25,
                "max_cost_usd": 2.0,
                "max_runtime_seconds": 3600,
                "cancel_requested": False,
                "last_error": "Validation failed",
                "assigned_model": "ralph-model",
                "status": "building",
                "run_manifest": [
                    {"type": "agent", "node": "planning", "model": "ralph-model"}
                ],
            },
            next=("building",),
            config={"configurable": {"checkpoint_id": "checkpoint-2"}},
            metadata={"step": 4},
            created_at="2026-08-05T00:00:00+00:00",
        )
        history = [
            SimpleNamespace(
                values={"attempts_count": 1, "status": "planning"},
                next=("building",),
                config={"configurable": {"checkpoint_id": "checkpoint-1"}},
                metadata={"step": 3},
                created_at="2026-08-05T00:00:00+00:00",
            )
        ]

        class FakeGraph:
            def get_state(self, config):
                self.config = config
                return current

            def get_state_history(self, config, *, limit):
                self.history_config = config
                self.history_limit = limit
                return iter(history)

        graph = FakeGraph()
        result = execution_state(graph, "thread-1", limit=5)

        self.assertEqual(graph.config, {"configurable": {"thread_id": "thread-1"}})
        self.assertEqual(graph.history_limit, 5)
        self.assertEqual(result["current_node"], "building")
        self.assertEqual(result["item"]["id"], "item-2")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(result["total_attempts"], 3)
        self.assertEqual(result["total_tokens"], 120)
        self.assertEqual(result["total_cost_usd"], 0.25)
        self.assertEqual(result["last_error"], "Validation failed")
        self.assertEqual(result["model"], "ralph-model")
        self.assertEqual(
            result["checkpoint_history"][0]["checkpoint_id"], "checkpoint-1"
        )
        self.assertEqual(result["run_manifest"][0]["node"], "planning")

    def test_default_graphs_share_sqlite_checkpoints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint_db = Path(directory) / "checkpoints.sqlite"
            with patch.dict(
                os.environ,
                {"SHANKS_CHECKPOINT_DB": str(checkpoint_db)},
            ):
                config = {"configurable": {"thread_id": "shared-thread"}}
                first_graph = compile_graph(stub_dependencies())
                first_graph.invoke({"task": "Shared state"}, config)
                second_graph = compile_graph(stub_dependencies())

                snapshot = second_graph.get_state(config)
                history = list(second_graph.get_state_history(config))
                first_graph.checkpointer.conn.close()
                second_graph.checkpointer.conn.close()

        self.assertEqual(snapshot.next, ("intake",))
        self.assertGreaterEqual(len(history), 1)

    def test_load_graph_module_draws_mermaid_without_raising(self) -> None:
        # load_graph_module() execs graph.py's source into a synthetic
        # module rather than a normal import; dataclasses' resolution of
        # graph.py's `from __future__ import annotations` string
        # annotations requires that module to be registered in
        # sys.modules, or CheckpointCleanup's @dataclass(slots=True)
        # processing raises AttributeError deep inside draw_mermaid().
        module = load_graph_module()
        drawable_graph = module.build_graph(checkpointer=InMemorySaver()).get_graph()

        content = drawable_graph.draw_mermaid()

        self.assertIn("preflight", content)

    def test_load_graph_module_serializes_on_shared_lock(self) -> None:
        # _send_mermaid() and /graph-state both go through
        # load_execution_graph(), which calls load_graph_module(), from
        # separate request threads (e.g. on every page load, graph.html
        # fires refreshGraph() and refreshExecution() back-to-back). Without
        # a lock shared by every caller, one thread's
        # sys.modules["graph_live"] cleanup can race another thread's
        # in-flight exec() and raise KeyError. Prove mutual exclusion
        # directly instead of relying on timing to reproduce the race.
        import serve_graph

        holder_started = threading.Event()
        release_holder = threading.Event()

        def hold_lock() -> None:
            with serve_graph._graph_module_lock:
                holder_started.set()
                release_holder.wait(timeout=2)

        holder = threading.Thread(target=hold_lock)
        holder.start()
        self.assertTrue(holder_started.wait(timeout=2))

        result: dict[str, object] = {}

        def call_load() -> None:
            result["module"] = load_graph_module()

        caller = threading.Thread(target=call_load)
        caller.start()
        caller.join(timeout=0.2)
        self.assertTrue(
            caller.is_alive(), "load_graph_module() did not block on the shared lock"
        )

        release_holder.set()
        caller.join(timeout=2)
        holder.join(timeout=2)

        self.assertIn("module", result)
        self.assertTrue(hasattr(result["module"], "build_graph"))

    def test_viewer_keeps_forward_edges_solid_and_backward_edges_dashed(self) -> None:
        drawable_graph = build_graph().get_graph()
        decision_nodes = {
            node.id
            for node in drawable_graph.nodes.values()
            if (node.metadata or {}).get("kind") == "decision"
        }

        content = style_mermaid(drawable_graph.draw_mermaid(), decision_nodes)

        self.assertIn("graph TD;", content)
        self.assertIn("preflight --> intake;", content)
        self.assertIn("validation{validation}", content)
        self.assertIn("planning --> building;", content)
        self.assertIn("building --> validation;", content)
        self.assertIn("building --> failed_build;", content)
        self.assertIn("building -.-> retry_backoff;", content)
        self.assertIn("retry_backoff -.-> building;", content)
        self.assertIn("failed_build --> __end__;", content)
        self.assertIn("failed_run --> __end__;", content)
        self.assertIn("validation --> pre_commit_policy_gate;", content)
        self.assertIn("pre_commit_policy_gate --> commit_item;", content)
        self.assertIn("commit_item --> item_router;", content)
        self.assertIn("validation --> debugger;", content)
        self.assertNotIn("push_node -.-> debugger;", content)
        self.assertIn("building --> critic_auditor;", content)
        self.assertIn("critic_auditor -.-> building;", content)
        self.assertIn("debugger -.-> planning;", content)
        self.assertIn("item_router -.-> planning;", content)

        self.assertNotIn("building --> __end__;", content)
        self.assertNotIn("validation -.-> planning;", content)

    def test_structured_view_labels_and_critic_loop(self) -> None:
        drawable_graph = build_graph().get_graph()
        decision_nodes = {
            node.id
            for node in drawable_graph.nodes.values()
            if (node.metadata or {}).get("kind") == "decision"
        }

        content = structured_mermaid(
            drawable_graph.draw_mermaid(),
            decision_nodes,
        )

        self.assertIn('planning["planning"]', content)
        self.assertIn('intake["Intake"]:::mainNode', content)
        self.assertIn('preflight["Preflight"]:::mainNode', content)
        self.assertIn('learning["Learn codebase"]:::mainNode', content)
        self.assertIn('building["Build"]:::mainNode', content)
        self.assertIn('item_router{"more items"}', content)
        self.assertIn('validation{"Validate"}:::yellowNode', content)
        self.assertIn('pre_commit_policy_gate["Policy gate"]:::mainNode', content)
        self.assertIn('commit_item["commit item"]:::mainNode', content)
        self.assertIn('push_node["push branch"]:::yellowNode', content)
        self.assertIn(
            'pull_request_node["open pull request"]:::yellowNode',
            content,
        )
        self.assertIn('critic_auditor["critic_auditor"]', content)
        main_section = content.split("  end", 1)[0]
        self.assertIn("building --> critic_auditor", main_section)
        self.assertIn("critic_auditor -.-> building", main_section)
        self.assertIn("validation --> pre_commit_policy_gate", main_section)
        self.assertIn("pre_commit_policy_gate --> commit_item", main_section)
        self.assertIn("commit_item --> item_router", main_section)
        self.assertIn("intake -.-> learning", main_section)
        self.assertIn("learning -.-> intake", main_section)
        self.assertNotIn("building --> building", main_section)
        self.assertIn("item_router -.-> planning", main_section)
        self.assertIn("item_router --> push_node", main_section)
        self.assertIn("push_node --> pull_request_node", main_section)
        self.assertIn("pull_request_node --> __end__", main_section)
        self.assertNotIn("critic_auditor -.-> validation", content)
        self.assertNotIn("critic_auditor -.-> item_router", content)

        detailed_content = structured_mermaid(
            drawable_graph.draw_mermaid(),
            decision_nodes,
            detailed=True,
        )
        self.assertIn("main -.-> recovery", detailed_content)
        self.assertIn("recovery -.-> main", detailed_content)
        self.assertNotIn("validation -.-> debugger", detailed_content)
        self.assertNotIn("push_node -.-> debugger", detailed_content)
        self.assertNotIn("building -.-> attempt_limit", detailed_content)


if __name__ == "__main__":
    unittest.main()
