import sqlite3
import unittest

from graph import VersionedSqliteSaver, build_graph
from langgraph.types import Command
from workflow.adapters import StubAgentAdapter
from workflow.lifecycle import RunBusyError, RunLifecycleManager
from workflow.nodes import NodeDependencies, create_nodes


def dependencies(lifecycle: RunLifecycleManager) -> NodeDependencies:
    return NodeDependencies(
        planner=StubAgentAdapter("planner", "planner"),
        builder=StubAgentAdapter("builder", "builder"),
        critic=StubAgentAdapter("critic", "critic"),
        validator=StubAgentAdapter("validator", "validator"),
        debugger=StubAgentAdapter("debugger", "debugger"),
        lifecycle_manager=lifecycle,
    )


class LifecycleTests(unittest.TestCase):
    def test_live_lease_blocks_and_expired_lease_recovers(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        first = RunLifecycleManager(connection, lease_ttl_seconds=10, owner_id="first")
        second = RunLifecycleManager(
            connection,
            lease_ttl_seconds=10,
            owner_id="second",
        )

        lease = first.acquire("run-1", now=100)
        self.assertEqual(lease.owner_id, "first")
        with self.assertRaises(RunBusyError):
            second.acquire("run-1", now=105)

        recovered = second.acquire("run-1", now=111)
        self.assertTrue(recovered.recovered)
        self.assertEqual(recovered.previous_owner, "first")
        self.assertEqual(second.get_run("run-1").recovery_count, 1)
        self.assertTrue(second.release("run-1", status="complete", now=112))
        self.assertEqual(second.get_run("run-1").status, "complete")
        connection.close()

    def test_interrupted_run_can_resume_with_the_same_owner(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        lifecycle = RunLifecycleManager(
            connection,
            lease_ttl_seconds=10,
            owner_id="owner",
        )

        lifecycle.acquire("run-1", now=100)
        lifecycle.mark_interrupted("run-1", now=101)
        self.assertEqual(lifecycle.get_run("run-1").status, "interrupted")
        lifecycle.acquire("run-1", now=102)
        self.assertEqual(lifecycle.get_run("run-1").status, "running")
        connection.close()

    def test_graph_rejects_a_second_owner_before_running_a_node(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        first_lifecycle = RunLifecycleManager(connection, owner_id="first")
        second_lifecycle = RunLifecycleManager(connection, owner_id="second")
        first_preflight = create_nodes(dependencies(first_lifecycle))["preflight"]
        second_preflight = create_nodes(dependencies(second_lifecycle))["preflight"]
        state = {"task": "locked", "state_schema_version": 6}
        config = {"configurable": {"thread_id": "run-1"}}

        self.assertEqual(first_preflight(state, config)["status"], "preflight_skipped")
        blocked = second_preflight(state, config)

        self.assertEqual(blocked["status"], "run_locked")
        self.assertEqual(blocked["run_lifecycle_status"], "blocked")
        self.assertEqual(blocked["failure_node"], "lease")
        first_lifecycle.release("run-1", status="failed")
        connection.close()

    def test_checkpoint_cleanup_keeps_recent_terminal_history(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        saver = VersionedSqliteSaver(connection, retention_limit=100)
        config = {
            "configurable": {
                "thread_id": "run-1",
                "checkpoint_ns": "",
            }
        }
        for index in range(3):
            saver.put(
                config,
                {
                    "v": 1,
                    "id": f"checkpoint-{index}",
                    "ts": f"2026-08-07T00:00:0{index}+00:00",
                    "channel_values": {"status": "complete"},
                    "channel_versions": {},
                    "versions_seen": {},
                    "updated_channels": None,
                },
                {},
                {},
            )

        result = saver.cleanup(keep_latest=2, thread_id="run-1")

        self.assertEqual(result.checkpoints_deleted, 1)
        self.assertEqual(len(list(saver.list(config))), 2)
        connection.close()

    def test_graph_marks_interrupt_and_releases_after_resume(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        saver = VersionedSqliteSaver(connection)
        lifecycle = saver.lifecycle_manager
        graph = build_graph(
            dependencies(lifecycle),
            checkpointer=saver,
        )
        config = {"configurable": {"thread_id": "interrupted-run"}}

        paused = graph.invoke({"task": "pause me"}, config)
        self.assertIn("__interrupt__", paused)
        self.assertEqual(lifecycle.get_run("interrupted-run").status, "interrupted")

        result = graph.invoke(Command(resume="implement"), config)

        self.assertEqual(result["status"], "complete")
        self.assertEqual(lifecycle.get_run("interrupted-run").status, "complete")
        connection.close()


if __name__ == "__main__":
    unittest.main()
