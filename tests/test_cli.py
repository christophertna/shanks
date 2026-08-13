import json
import io
import re
import subprocess
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from langgraph.types import Interrupt

from graph import VersionedSqliteSaver
from workflow.adapters import GitHubAdapter
from workflow.cli import _REQUIRED_TOOLS, main
from workflow.lifecycle import RunLifecycleManager
from workflow.workspaces import RunWorkspaceManager


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
                    side_effect=lambda command, **kwargs: subprocess.CompletedProcess(
                        args=command,
                        returncode=0,
                        stdout=(
                            "hooks"
                            if command[:2] == ("git", "config")
                            else "authenticated"
                        ),
                        stderr="",
                    ),
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["doctor"]), 0)

        self.assertIn("[OK] mode", output.getvalue())
        self.assertIn("[OK] dependencies", output.getvalue())
        self.assertIn("[OK] authentication", output.getvalue())
        self.assertIn("[OK] hooks", output.getvalue())
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

    def test_doctor_fails_on_outdated_git_or_gh(self) -> None:
        output = io.StringIO()

        def fake_run(
            command: tuple[str, ...], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if command == ("git", "--version"):
                return subprocess.CompletedProcess(command, 0, "git version 2.10.1", "")
            if command == ("gh", "--version"):
                return subprocess.CompletedProcess(command, 0, "gh version 2.20.0", "")
            if command[:2] == ("git", "config"):
                return subprocess.CompletedProcess(command, 0, "hooks", "")
            return subprocess.CompletedProcess(command, 0, "authenticated", "")

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict(
                    "os.environ",
                    {
                        "SHANKS_MODE": "runtime",
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
                    side_effect=lambda name: {
                        "langgraph": "1.2.10",
                        "langgraph-checkpoint-sqlite": "3.1.1",
                        "black": "26.5.1",
                        "mypy": "1.20.2",
                        "pip-audit": "2.10.1",
                        "ruff": "0.16.1",
                    }[name],
                ),
                patch("workflow.cli.subprocess.run", side_effect=fake_run),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["doctor"]), 1)

        self.assertIn("[FAIL] tools", output.getvalue())
        self.assertIn("git 2.30+ (found 2.10)", output.getvalue())
        self.assertIn("gh 2.40+ (found 2.20)", output.getvalue())

    def test_doctor_fails_when_hooks_path_is_unconfigured(self) -> None:
        output = io.StringIO()

        def fake_run(
            command: tuple[str, ...], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            if command[:2] == ("git", "config"):
                return subprocess.CompletedProcess(command, 1, "", "")
            return subprocess.CompletedProcess(command, 0, "authenticated", "")

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict(
                    "os.environ",
                    {
                        "SHANKS_MODE": "runtime",
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
                    side_effect=lambda name: {
                        "langgraph": "1.2.10",
                        "langgraph-checkpoint-sqlite": "3.1.1",
                        "black": "26.5.1",
                        "mypy": "1.20.2",
                        "pip-audit": "2.10.1",
                        "ruff": "0.16.1",
                    }[name],
                ),
                patch("workflow.cli.subprocess.run", side_effect=fake_run),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["doctor"]), 1)

        self.assertIn("[FAIL] hooks", output.getvalue())
        self.assertIn("git config core.hooksPath hooks", output.getvalue())

    def test_doctor_and_github_preflight_tool_lists_match(self) -> None:
        self.assertEqual(set(_REQUIRED_TOOLS), set(GitHubAdapter.REQUIRED_TOOLS))

    def test_tests_md_counts_match_actual_test_methods(self) -> None:
        repo_root = Path(__file__).parents[1]
        tests_md = (repo_root / "tests" / "tests.md").read_text(encoding="utf-8")

        documented = re.findall(r"\[`(test_\w+\.py)`\]\(\1\) \| (\d+) \|", tests_md)
        self.assertTrue(documented)

        for filename, count in documented:
            source = (repo_root / "tests" / filename).read_text(encoding="utf-8")
            actual = len(re.findall(r"^\s*def test_", source, re.MULTILINE))
            self.assertEqual(
                actual,
                int(count),
                f"tests/tests.md documents {count} tests for {filename}, "
                f"but it has {actual}",
            )

    def test_tests_md_shell_check_counts_match_harness_output(self) -> None:
        repo_root = Path(__file__).parents[1]
        tests_md = (repo_root / "tests" / "tests.md").read_text(encoding="utf-8")

        documented = re.findall(
            r"\[`(\.\./hooks/test\.hooks/[\w.-]+\.sh)`\]\(\1\) \| (\d+) shell checks \|",
            tests_md,
        )
        self.assertTrue(documented)

        for relative_path, count in documented:
            harness = (repo_root / "tests" / relative_path).resolve()
            result = subprocess.run(
                ["bash", str(harness)],
                capture_output=True,
                text=True,
                cwd=repo_root,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"{harness.name} failed:\n{result.stdout}{result.stderr}",
            )
            self.assertEqual(
                result.stdout.strip().splitlines()[-1],
                f"passed: {count}, failed: 0",
                f"tests/tests.md documents {count} shell checks for "
                f"{harness.name}, but it reported {result.stdout.strip()}",
            )

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

    def test_runs_status_surfaces_interrupt_drift_and_recent_events(self) -> None:
        prompt = {
            "type": "intake",
            "question": "What would you like to do?",
            "options": [{"value": "learn", "label": "Learn the codebase"}],
        }
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "checkpoints.sqlite"
            self._seed_run(
                database,
                "run-paused",
                status="interrupted",
                interrupt=prompt,
                values={
                    "repo_drift": "This branch is 2 commit(s) behind origin/main.",
                    "run_manifest": [
                        {"timestamp": "t0", "type": "agent", "node": "planning"},
                        {
                            "timestamp": "t1",
                            "type": "repository",
                            "node": "drift_check",
                            "status": "drift_checked",
                        },
                    ],
                },
            )
            arguments = [
                "runs",
                "status",
                "run-paused",
                "--checkpoint-db",
                str(database),
            ]

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([*arguments, "--json"]), 0)
            payload = json.loads(output.getvalue())

            human = io.StringIO()
            with redirect_stdout(human):
                self.assertEqual(main(arguments), 0)

        self.assertEqual(payload["interrupts"][0]["value"], prompt)
        self.assertEqual(
            payload["checkpoint"]["repo_drift"],
            "This branch is 2 commit(s) behind origin/main.",
        )
        self.assertEqual(
            [event["node"] for event in payload["recent_events"]],
            ["planning", "drift_check"],
        )
        self.assertIn("What would you like to do?", human.getvalue())
        self.assertIn("- learn: Learn the codebase", human.getvalue())
        self.assertIn("2 commit(s) behind origin/main", human.getvalue())
        self.assertIn("drift_check", human.getvalue())

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

    def test_prune_reports_and_removes_orphan_worktrees_and_branches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            self._git(root, "init", "-b", "main")
            self._git(root, "config", "user.email", "tests@example.com")
            self._git(root, "config", "user.name", "Tests")
            (root / "README.md").write_text("initial\n", encoding="utf-8")
            self._git(root, "add", "README.md")
            self._git(root, "commit", "-m", "initial")

            database = Path(directory) / "checkpoints.sqlite"
            self._seed_run(database, "live-run", status="running")
            self._seed_run(database, "done-run", status="complete")

            manager = RunWorkspaceManager(root)
            manager.ensure("live-run")
            manager.ensure("done-run")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "prune",
                            "--json",
                            "--checkpoint-db",
                            str(database),
                            "--project-dir",
                            str(root),
                        ]
                    ),
                    0,
                )
            report = json.loads(output.getvalue())
            self.assertFalse(report["applied"])
            worktrees = {item["id"]: item["orphan"] for item in report["worktrees"]}
            self.assertEqual(worktrees, {"live-run": False, "done-run": True})
            self.assertTrue((root / ".shanks" / "worktrees" / "done-run").exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "runs",
                            "prune",
                            "--apply",
                            "--json",
                            "--checkpoint-db",
                            str(database),
                            "--project-dir",
                            str(root),
                        ]
                    ),
                    0,
                )
            report = json.loads(output.getvalue())
            actions = {item["id"]: item["action"] for item in report["worktrees"]}
            self.assertEqual(actions["done-run"], "removed")
            self.assertEqual(actions["live-run"], "skipped: active run")
            self.assertFalse((root / ".shanks" / "worktrees" / "done-run").exists())
            self.assertTrue((root / ".shanks" / "worktrees" / "live-run").exists())

    @staticmethod
    def _git(directory: Path, *args: str) -> str:
        result = subprocess.run(
            ("git", *args),
            cwd=directory,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

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
    def _seed_run(
        database: Path,
        run_id: str,
        *,
        status: str,
        interrupt: dict[str, object] | None = None,
        values: dict[str, object] | None = None,
    ) -> None:
        connection = sqlite3.connect(str(database), check_same_thread=False)
        lifecycle = RunLifecycleManager(connection, owner_id="seed")
        lifecycle.acquire(run_id)
        saver = VersionedSqliteSaver(connection, lifecycle_manager=lifecycle)
        config = saver.put(
            {"configurable": {"thread_id": run_id, "checkpoint_ns": ""}},
            {
                "v": 1,
                "id": f"{run_id}-checkpoint",
                "ts": "2026-08-08T00:00:00+00:00",
                "channel_values": {
                    "status": status,
                    "run_branch": f"shanks/run/{run_id}",
                    "workspace_directory": str(database.parent / "worktree"),
                    **(values or {}),
                },
                "channel_versions": {},
                "versions_seen": {},
                "updated_channels": None,
            },
            {},
            {},
        )
        if interrupt is not None:
            saver.put_writes(
                config,
                [("__interrupt__", [Interrupt(value=interrupt)])],
                "seed-task",
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
