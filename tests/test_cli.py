import json
import io
import subprocess
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from graph import VersionedSqliteSaver
from workflow.cli import main
from workflow.lifecycle import RunLifecycleManager


class ShanksCliTests(unittest.TestCase):
    def test_mode_reports_safe_runtime(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "runtime"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["--mode"]), 0)

        self.assertIn("safe/normal (runtime)", output.getvalue())
        self.assertIn("human approval required", output.getvalue())

    def test_mode_reports_development_capability_without_consent(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "development"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["-mode"]), 0)

        self.assertIn("development", output.getvalue())
        self.assertIn("human approval still required", output.getvalue())

    def test_mode_reports_dry_run_preview(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "dry-run"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["--mode"]), 0)

        self.assertIn("dry-run", output.getvalue())
        self.assertIn("previewed and skipped", output.getvalue())

    def test_mode_subcommand_is_supported(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "runtime"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["mode"]), 0)

        self.assertIn("safe/normal (runtime)", output.getvalue())

    def test_doctor_reports_a_healthy_environment(self) -> None:
        output = io.StringIO()
        versions = {
            "langgraph": "1.2.10",
            "langgraph-checkpoint-sqlite": "3.1.1",
            "black": "26.5.1",
            "mypy": "1.20.2",
            "pip-audit": "2.10.1",
            "ruff": "0.16.1",
        }

        def installed_version(name: str) -> str:
            return versions[name]

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict(
                    "os.environ",
                    {
                        "SHANKS_MODE": "development",
                        "SHANKS_CHECKPOINT_DB": str(
                            Path(directory) / "checkpoints.sqlite"
                        ),
                        "SHANKS_RUN_LEASE_SECONDS": "3600",
                        "SHANKS_CHECKPOINT_RETENTION": "100",
                        "HOME": "/tmp",
                        "PATH": "/usr/bin",
                    },
                    clear=True,
                ),
                patch("workflow.cli.shutil.which", return_value="/usr/bin/tool"),
                patch(
                    "workflow.cli.importlib_metadata.version",
                    side_effect=installed_version,
                ),
                patch(
                    "workflow.cli.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        args=("gh", "auth", "status"),
                        returncode=0,
                        stdout="authenticated",
                        stderr="",
                    ),
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["doctor"]), 0)

        self.assertIn("[OK] mode", output.getvalue())
        self.assertIn("[OK] dependencies", output.getvalue())
        self.assertIn("[OK] authentication", output.getvalue())
        self.assertIn("Doctor: PASS", output.getvalue())

    def test_doctor_fails_invalid_environment(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(
                "os.environ",
                {
                    "SHANKS_MODE": "unknown",
                    "SHANKS_RUN_LEASE_SECONDS": "0",
                    "SHANKS_CHECKPOINT_RETENTION": "nope",
                    "SHANKS_CHECKPOINT_DB": "",
                },
                clear=True,
            ),
            patch("workflow.cli.shutil.which", return_value="/usr/bin/tool"),
            patch(
                "workflow.cli.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=("gh", "auth", "status"),
                    returncode=1,
                    stdout="",
                    stderr="not authenticated",
                ),
            ),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["doctor"]), 1)

        self.assertIn("[FAIL] mode", output.getvalue())
        self.assertIn("[FAIL] environment", output.getvalue())
        self.assertIn("[FAIL] checkpoint", output.getvalue())
        self.assertIn("Doctor: FAIL", output.getvalue())

    def test_runs_list_and_status_support_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            self._seed_run(database, "run-1", status="complete")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "list",
                            "--json",
                            "--checkpoint-db",
                            str(database),
                        ]
                    ),
                    0,
                )
            listed = json.loads(output.getvalue())
            self.assertEqual(listed[0]["run_id"], "run-1")
            self.assertEqual(listed[0]["status"], "complete")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "status",
                            "run-1",
                            "--json",
                            "--checkpoint-db",
                            str(database),
                        ]
                    ),
                    0,
                )
            status = json.loads(output.getvalue())
            self.assertEqual(status["lifecycle"]["status"], "complete")
            self.assertEqual(status["checkpoint"]["status"], "complete")

    def test_runs_cleanup_removes_old_checkpoint_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            connection = sqlite3.connect(str(database), check_same_thread=False)
            lifecycle = RunLifecycleManager(connection, owner_id="seed")
            lifecycle.acquire("run-1")
            saver = VersionedSqliteSaver(connection, lifecycle_manager=lifecycle)
            config = {"configurable": {"thread_id": "run-1", "checkpoint_ns": ""}}
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
            connection.close()

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "cleanup",
                            "--keep-latest",
                            "2",
                            "--run-id",
                            "run-1",
                            "--json",
                            "--checkpoint-db",
                            str(database),
                        ]
                    ),
                    0,
                )
            result = json.loads(output.getvalue())
            self.assertEqual(result["checkpoints_deleted"], 1)

    def test_cancel_requests_stop_without_stealing_a_live_lease(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            self._seed_run(database, "run-1", status="interrupted")
            fake_graph = _FakeGraph()
            with patch("graph.build_graph", return_value=fake_graph):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(
                            [
                                "runs",
                                "cancel",
                                "run-1",
                                "--checkpoint-db",
                                str(database),
                            ]
                        ),
                        0,
                    )

            self.assertEqual(len(fake_graph.updates), 1)
            self.assertEqual(fake_graph.invocations, [])
            self.assertIn("Cancellation requested", output.getvalue())

    def test_resume_passes_the_operator_response_to_the_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            self._seed_run(database, "run-1", status="interrupted")
            fake_graph = _FakeGraph()
            with patch("graph.build_graph", return_value=fake_graph):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "resume",
                            "run-1",
                            "approve",
                            "--checkpoint-db",
                            str(database),
                        ]
                    ),
                    0,
                )

            self.assertEqual(len(fake_graph.invocations), 1)
            self.assertEqual(fake_graph.invocations[0][0].resume, "approve")

    def test_recover_marks_expired_leases_from_the_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            connection = sqlite3.connect(str(database), check_same_thread=False)
            RunLifecycleManager(
                connection,
                lease_ttl_seconds=1,
                owner_id="seed",
            ).acquire("run-1", now=100)
            connection.close()

            output = io.StringIO()
            with (
                patch.dict("os.environ", {"SHANKS_RUN_LEASE_SECONDS": "1"}),
                redirect_stdout(output),
            ):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "recover",
                            "--json",
                            "--checkpoint-db",
                            str(database),
                        ]
                    ),
                    0,
                )

            self.assertEqual(json.loads(output.getvalue())["runs_marked_abandoned"], 1)

    def test_remove_rejects_non_terminal_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            self._seed_run(database, "run-1", status="running")
            error = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(error):
                result = main(
                    [
                        "runs",
                        "remove",
                        "run-1",
                        "--checkpoint-db",
                        str(database),
                    ]
                )
            self.assertEqual(result, 1)
            self.assertIn("only terminal runs", error.getvalue())

    @staticmethod
    def _seed_run(database: Path, run_id: str, *, status: str) -> None:
        connection = sqlite3.connect(str(database), check_same_thread=False)
        lifecycle = RunLifecycleManager(connection, owner_id="seed")
        lifecycle.acquire(run_id)
        saver = VersionedSqliteSaver(connection, lifecycle_manager=lifecycle)
        saver.put(
            {"configurable": {"thread_id": run_id, "checkpoint_ns": ""}},
            {
                "v": 1,
                "id": f"{run_id}-checkpoint",
                "ts": "2026-08-08T00:00:00+00:00",
                "channel_values": {
                    "status": status,
                    "run_branch": f"shanks/run/{run_id}",
                    "workspace_directory": str(database.parent / "worktree"),
                },
                "channel_versions": {},
                "versions_seen": {},
                "updated_channels": None,
            },
            {},
            {},
        )
        if status == "interrupted":
            lifecycle.mark_interrupted(run_id)
        connection.close()


class _FakeGraph:
    def __init__(self) -> None:
        self.updates = []
        self.invocations = []

    def update_state(self, config, update):
        self.updates.append((config, update))

    def invoke(self, value, config):
        self.invocations.append((value, config))
        return {"status": "cancelled"}


if __name__ == "__main__":
    unittest.main()
