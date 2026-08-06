import sqlite3
import unittest

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph import VersionedSqliteSaver, build_graph
from workflow.adapters import StubAgentAdapter
from workflow.nodes import NodeDependencies
from workflow.state import (
    CURRENT_STATE_SCHEMA_VERSION,
    StateSchemaError,
    migrate_state,
)


class StateSchemaTests(unittest.TestCase):
    @staticmethod
    def _stub_dependencies() -> NodeDependencies:
        return NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

    def test_unversioned_state_migrates_to_current_schema(self) -> None:
        legacy = {"task": "resume this run", "attempts_count": 2}

        migrated = migrate_state(legacy)

        self.assertEqual(migrated["state_schema_version"], CURRENT_STATE_SCHEMA_VERSION)
        self.assertNotIn("state_schema_version", legacy)
        self.assertEqual(migrated["task"], "resume this run")
        self.assertEqual(migrated["max_total_attempts"], 20)

    def test_newer_state_schema_is_rejected(self) -> None:
        with self.assertRaises(StateSchemaError):
            migrate_state({"state_schema_version": CURRENT_STATE_SCHEMA_VERSION + 1})

    def test_v1_state_migrates_run_budget_defaults(self) -> None:
        migrated = migrate_state({"state_schema_version": 1})

        self.assertEqual(
            migrated["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )
        self.assertEqual(migrated["max_total_attempts"], 20)
        self.assertEqual(migrated["max_tokens"], 100_000)
        self.assertEqual(migrated["total_tokens"], 0)
        self.assertFalse(migrated["cancel_requested"])

    def test_v2_state_migrates_run_manifest(self) -> None:
        migrated = migrate_state({"state_schema_version": 2})

        self.assertEqual(
            migrated["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )
        self.assertEqual(migrated["run_manifest"], [])

    def test_v3_state_migrates_failure_and_retry_fields(self) -> None:
        migrated = migrate_state({"state_schema_version": 3})

        self.assertEqual(
            migrated["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )
        self.assertEqual(migrated["failure_class"], "")
        self.assertEqual(migrated["retry_counts"], {})
        self.assertEqual(migrated["retry_target"], "")
        self.assertEqual(migrated["retry_delay_seconds"], 0.0)

    def test_sqlite_saver_migrates_legacy_checkpoint_on_read(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        legacy_saver = SqliteSaver(connection)
        config = {
            "configurable": {
                "thread_id": "legacy-run",
                "checkpoint_ns": "",
            }
        }
        checkpoint = {
            "v": 1,
            "id": "checkpoint-1",
            "ts": "2026-08-05T00:00:00+00:00",
            "channel_values": {"task": "resume this run"},
            "channel_versions": {},
            "versions_seen": {},
            "updated_channels": None,
        }
        legacy_saver.put(config, checkpoint, {}, {})

        saver = VersionedSqliteSaver(connection)
        loaded = saver.get_tuple(config)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.checkpoint["channel_values"]["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )
        connection.close()

    def test_sqlite_saver_stamps_new_checkpoint(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        saver = VersionedSqliteSaver(connection)
        config = {
            "configurable": {
                "thread_id": "new-run",
                "checkpoint_ns": "",
            }
        }
        checkpoint = {
            "v": 1,
            "id": "checkpoint-1",
            "ts": "2026-08-05T00:00:00+00:00",
            "channel_values": {"task": "new run"},
            "channel_versions": {},
            "versions_seen": {},
            "updated_channels": None,
        }

        saver.put(config, checkpoint, {}, {})
        loaded = saver.get_tuple(config)

        self.assertIsNotNone(loaded)
        self.assertEqual(
            loaded.checkpoint["channel_values"]["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )
        connection.close()

    def test_legacy_checkpoint_can_resume_through_current_graph(self) -> None:
        connection = sqlite3.connect(":memory:", check_same_thread=False)
        legacy_graph = build_graph(
            self._stub_dependencies(),
            checkpointer=SqliteSaver(connection),
        )
        config = {"configurable": {"thread_id": "legacy-resume"}}

        paused = legacy_graph.invoke({"task": "resume this run"}, config)
        self.assertIn("__interrupt__", paused)

        current_graph = build_graph(
            self._stub_dependencies(),
            checkpointer=VersionedSqliteSaver(connection),
        )
        snapshot = current_graph.get_state(config)
        self.assertEqual(
            snapshot.values["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )

        result = current_graph.invoke(
            Command(resume={"choice": "implement"}),
            config,
        )
        self.assertEqual(
            result["state_schema_version"],
            CURRENT_STATE_SCHEMA_VERSION,
        )
        connection.close()


if __name__ == "__main__":
    unittest.main()
