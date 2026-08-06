import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from graph import VersionedSqliteSaver, build_graph
from workflow.adapters import (
    GitHubAdapter,
    LocalTestAdapter,
    StubAgentAdapter,
    SubprocessAgentAdapter,
)
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import NodeDependencies


def _initial_state() -> dict[str, object]:
    return {
        "task": "Inject a controlled failure",
        "workflow_mode": "implement",
        "prd_items": [
            {
                "id": "item-1",
                "title": "Failure test",
                "description": "Exercise a controlled failure.",
                "passes": False,
                "validation": False,
            }
        ],
    }


def _dependencies(*, builder=None) -> NodeDependencies:
    return NodeDependencies(
        planner=StubAgentAdapter("planner", "planner"),
        builder=builder or StubAgentAdapter("builder", "builder"),
        critic=StubAgentAdapter("critic", "critic"),
        validator=StubAgentAdapter("validator", "validator"),
        debugger=StubAgentAdapter("debugger", "debugger"),
    )


def _checkpoint_payload() -> tuple[dict[str, object], dict[str, object]]:
    config = {
        "configurable": {
            "thread_id": "faulty-checkpoint",
            "checkpoint_ns": "",
        }
    }
    checkpoint = {
        "v": 1,
        "id": "checkpoint-1",
        "ts": "2026-08-06T00:00:00+00:00",
        "channel_values": {"task": "checkpoint fault"},
        "channel_versions": {},
        "versions_seen": {},
        "updated_channels": None,
    }
    return config, checkpoint


class ExplodingBuilder:
    model_name = "exploding-builder"

    def run(self, request: AgentRequest) -> AgentResult:
        raise ValueError("injected agent crash")


class FaultInjectionTests(unittest.TestCase):
    def test_git_process_error_is_returned_as_a_classified_failure(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())

        with patch(
            "workflow.adapters.subprocess.run",
            side_effect=OSError("injected git executable failure"),
        ):
            result = adapter._run(("git", "branch", "--show-current"))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_class, "permanent")
        self.assertIn("injected git executable failure", result.error)
        self.assertEqual(result.commands, [["git", "branch", "--show-current"]])

    def test_github_pr_creation_failure_stops_after_push_and_lookup(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="fault-branch\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(args=(), returncode=0, stdout="[]", stderr=""),
            subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="injected GitHub rejection"
            ),
        ]

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
            result = adapter.publish_pr("Ship the fault tests")

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_class, "permanent")
        self.assertEqual(run.call_count, 4)
        self.assertEqual(
            run.call_args_list[-1].args[0][:4], ("gh", "pr", "create", "--base")
        )
        self.assertEqual(result.pr_url, "")

    def test_validation_timeout_becomes_a_transient_validation_failure(self) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        timeout = subprocess.TimeoutExpired(adapter.command, timeout=1)

        with patch("workflow.adapters.subprocess.run", side_effect=timeout):
            result = adapter.run(AgentRequest(task="Run injected validation"))

        self.assertEqual(result.status, "validation_failed")
        self.assertFalse(result.validation_passed)
        self.assertEqual(result.failure_class, "transient")
        self.assertTrue(result.validation_errors)

    def test_agent_timeout_is_classified_transient_before_workflow_routing(
        self,
    ) -> None:
        adapter = SubprocessAgentAdapter(
            command=(sys.executable, "-c", "print('agent')"),
            model_name="faulty-agent",
        )
        timeout = subprocess.TimeoutExpired(adapter.command, timeout=1)

        with patch("workflow.adapters.subprocess.run", side_effect=timeout):
            result = adapter.run(AgentRequest(task="Run injected agent"))

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.failure_class, "transient")
        self.assertIn("timed out", result.error)

    def test_agent_exception_reaches_terminal_build_failure_with_audit_event(
        self,
    ) -> None:
        graph = build_graph(
            _dependencies(builder=ExplodingBuilder()),
            checkpointer=InMemorySaver(),
        )

        result = graph.invoke(
            _initial_state(),
            {"configurable": {"thread_id": "faulty-builder"}},
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_node"], "building")
        self.assertEqual(result["failure_class"], "permanent")
        self.assertEqual(result["last_error"], "injected agent crash")
        self.assertTrue(
            any(
                event.get("type") == "agent_error" and event.get("node") == "building"
                for event in result["run_manifest"]
            )
        )

    def test_checkpoint_write_failure_is_not_silently_swallowed(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        saver = VersionedSqliteSaver(connection)
        config, checkpoint = _checkpoint_payload()

        with patch.object(
            SqliteSaver,
            "put",
            side_effect=sqlite3.OperationalError("injected checkpoint write failure"),
        ):
            with self.assertRaisesRegex(sqlite3.OperationalError, "checkpoint write"):
                saver.put(config, checkpoint, {}, {})

        connection.close()

    def test_checkpoint_read_failure_is_not_silently_swallowed(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        saver = VersionedSqliteSaver(connection)

        with patch.object(
            SqliteSaver,
            "get_tuple",
            side_effect=sqlite3.OperationalError("injected checkpoint read failure"),
        ):
            with self.assertRaisesRegex(sqlite3.OperationalError, "checkpoint read"):
                saver.get_tuple({})

        connection.close()


if __name__ == "__main__":
    unittest.main()
