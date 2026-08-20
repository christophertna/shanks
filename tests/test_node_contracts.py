import inspect
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from workflow.adapters import (
    CLAUDE_OPUS_48_EFFORT,
    CLAUDE_OPUS_48_MODEL,
    CheapCriticAdapter,
    ClaudeAdapter,
    ClaudeOpus48CriticAdapter,
    CodexAdapter,
    DebuggerAdapter,
    GPT56LunaCriticAdapter,
    GitHubAdapter,
    LocalTestAdapter,
    RalphAdapter,
    StubAgentAdapter,
    _run_subprocess,
    _scan_for_secrets,
)
from workflow.adapters import SubprocessAgentAdapter
from workflow.contracts import (
    AgentRequest,
    AgentResult,
    PreviewRepositoryAdapter,
    RepositoryAdapter,
)
from workflow.nodes import (
    NodeDependencies,
    _reconcile_recovered_state,
    claude_opus_4_8_dependencies,
    commit_item,
    create_nodes,
    default_dependencies,
    gpt_5_6_luna_dependencies,
)
from workflow.state import WorkflowState
from workflow.retries import classify_failure, retry_delay, retry_on_exception
from workflow.workspaces import (
    RunWorkspace,
    remaining_deadline_seconds,
    run_deadline_scope,
)


class NodeContractTests(unittest.TestCase):
    def test_stub_roles_return_common_result_shape(self) -> None:
        request = AgentRequest(task="test task", item_id="item-1")

        for role in ("planner", "builder", "critic", "validator", "debugger"):
            with self.subTest(role=role):
                result = StubAgentAdapter(role, f"{role}-model").run(request)
                self.assertIsInstance(result, AgentResult)
                self.assertEqual(result.assigned_model, f"{role}-model")
                self.assertTrue(result.status)

    def test_failures_are_classified_before_routing(self) -> None:
        self.assertEqual(
            AgentResult(
                status="failed",
                assigned_model="test",
                error="connection reset by peer",
            ).failure_class,
            "transient",
        )
        self.assertEqual(
            AgentResult(
                status="failed",
                assigned_model="test",
                error="Refusing to run an unapproved executable: sh.",
            ).failure_class,
            "guardrail",
        )
        self.assertEqual(
            AgentResult(
                status="failed",
                assigned_model="test",
                validation_passed=False,
                validation_errors=["FAIL: test_example"],
            ).failure_class,
            "validation",
        )

    def test_retry_classifier_uses_bounded_exponential_backoff(self) -> None:
        self.assertTrue(retry_on_exception(ConnectionError("temporary network error")))
        self.assertFalse(retry_on_exception(ValueError("invalid request")))
        self.assertEqual(
            [retry_delay(index) for index in range(1, 5)],
            [0.5, 1.0, 2.0, 4.0],
        )
        self.assertEqual(classify_failure("status 503 from GitHub"), "transient")

    def test_reconcile_recovered_state_finds_nothing_with_no_prior_claims(
        self,
    ) -> None:
        workspace = RunWorkspace(
            "run-1", "shanks/run/run-1", Path("/tmp/shanks"), "main"
        )

        problems = _reconcile_recovered_state({}, workspace)

        self.assertEqual(problems, [])

    def test_reconcile_recovered_state_flags_a_pr_with_no_remote_branch(self) -> None:
        workspace = RunWorkspace(
            "run-1", "shanks/run/run-1", Path("/tmp/shanks"), "main"
        )
        current = {
            "pr_url": "https://github.com/example/shanks/pull/1",
            "run_branch": "shanks/run/run-1",
        }
        missing_ref = subprocess.CompletedProcess(
            args=(), returncode=0, stdout="", stderr=""
        )
        pr_ok = subprocess.CompletedProcess(
            args=(), returncode=0, stdout='{"state":"OPEN"}', stderr=""
        )

        with patch("workflow.nodes.subprocess.run", side_effect=[missing_ref, pr_ok]):
            problems = _reconcile_recovered_state(current, workspace)

        self.assertEqual(len(problems), 1)
        self.assertIn("no matching ref on origin", problems[0])

    def test_reconcile_recovered_state_flags_an_unverifiable_pull_request(
        self,
    ) -> None:
        workspace = RunWorkspace(
            "run-1", "shanks/run/run-1", Path("/tmp/shanks"), "main"
        )
        current = {
            "pr_url": "https://github.com/example/shanks/pull/1",
            "run_branch": "shanks/run/run-1",
        }
        ref_found = subprocess.CompletedProcess(
            args=(),
            returncode=0,
            stdout="abc123\trefs/heads/shanks/run/run-1\n",
            stderr="",
        )
        pr_missing = subprocess.CompletedProcess(
            args=(), returncode=1, stdout="", stderr="no pull requests found"
        )

        with patch(
            "workflow.nodes.subprocess.run", side_effect=[ref_found, pr_missing]
        ):
            problems = _reconcile_recovered_state(current, workspace)

        self.assertEqual(len(problems), 1)
        self.assertIn("could not be verified", problems[0])

    def test_github_adapter_satisfies_the_repository_protocol(self) -> None:
        members = sorted(
            name
            for name in vars(RepositoryAdapter)
            if not name.startswith("_") and callable(getattr(RepositoryAdapter, name))
        )
        self.assertIn("drift_report", members)

        for name in members:
            with self.subTest(member=name):
                implementation = getattr(GitHubAdapter, name, None)
                # Nodes reach these through getattr(repository, "<name>", None),
                # so a renamed or re-signed method disables the capability
                # silently instead of raising.
                self.assertTrue(
                    callable(implementation),
                    f"GitHubAdapter is missing RepositoryAdapter.{name}",
                )
                self.assertEqual(
                    inspect.signature(implementation),
                    inspect.signature(getattr(RepositoryAdapter, name)),
                )

        # Dry-run nodes narrow on isinstance(repository, PreviewRepositoryAdapter)
        # before calling the previews, and that runtime check only compares
        # member names - so signatures still need asserting here.
        previews = sorted(
            name
            for name in vars(PreviewRepositoryAdapter)
            if name.startswith("preview_")
        )
        self.assertEqual(len(previews), 3)
        for name in previews:
            with self.subTest(preview=name):
                implementation = getattr(GitHubAdapter, name, None)
                self.assertTrue(callable(implementation), f"GitHubAdapter lacks {name}")
                self.assertEqual(
                    inspect.signature(implementation),
                    inspect.signature(getattr(PreviewRepositoryAdapter, name)),
                )

    def test_partial_preview_adapters_fall_back_for_every_action(self) -> None:
        # The dry-run nodes narrow once, on the whole protocol, so an adapter
        # with only some previews falls back to the generic preview for all
        # three - not just the missing one, as the old per-action getattr
        # dispatch did. Nothing implements a partial set today; this pins the
        # behavior so a future partial adapter is a deliberate choice.
        class PartialPreviewRepository:
            def commit_item(
                self,
                item_id: str,
                item_title: str,
                files_touched: list[str],
            ) -> AgentResult:
                raise AssertionError("dry-run must not commit")

            def preview_commit_item(
                self,
                item_id: str,
                item_title: str,
                files_touched: list[str],
            ) -> AgentResult:
                raise AssertionError("a partial preview must stay unreachable")

        repository = PartialPreviewRepository()
        self.assertNotIsInstance(repository, PreviewRepositoryAdapter)

        stub = StubAgentAdapter(role="planner", model_name="stub")
        dependencies = NodeDependencies(
            planner=stub,
            builder=stub,
            critic=stub,
            validator=stub,
            debugger=stub,
            repository=repository,
        )
        state: WorkflowState = {
            "current_item_id": "item-1",
            "current_item_title": "Partial preview item",
            "files_touched_by_item": {"item-1": ["example.py"]},
        }

        with patch.dict(os.environ, {"SHANKS_MODE": "dry-run"}):
            update = commit_item(state, dependencies)

        # The generic preview, not the adapter's own: exactly two commands,
        # where GitHubAdapter.preview_commit_item emits a longer trail.
        self.assertEqual(update["status"], "commit_preview")
        self.assertEqual(
            [command[:2] for command in update["run_manifest"][0]["commands"]],
            [["git", "add"], ["git", "commit"]],
        )

        with TemporaryDirectory() as directory:
            adapter = GitHubAdapter(
                Path(directory),
                initial_dirty_files=(),
                stale_after_days=None,
            )
            self.assertIsInstance(adapter, PreviewRepositoryAdapter)

    def test_quick_read_only_lookups_use_a_short_subprocess_timeout(self) -> None:
        with TemporaryDirectory() as directory:
            adapter = GitHubAdapter(
                Path(directory),
                initial_dirty_files=(),
                stale_after_days=None,
            )
            timeouts: dict[tuple[str, ...], float] = {}

            def fake_run(command, *, cwd, timeout, env, **kwargs):
                timeouts[tuple(command)] = timeout
                return subprocess.CompletedProcess(command, 0, "", "")

            probes = (
                ("git", "branch", "--show-current"),
                ("git", "status", "--short", "--untracked-files=all"),
                ("git", "rev-parse", "HEAD"),
                ("git", "rev-list", "--count", "HEAD..origin/main"),
                ("git", "fetch", "--quiet", "origin", "main"),
                ("git", "diff", "HEAD", "--no-ext-diff", "--", "example.py"),
                (
                    "git",
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "--",
                    "example.py",
                ),
                ("gh", "auth", "status"),
                adapter._pull_request_list_command("shanks/run/1"),
            )
            slow = (
                ("git", "add", "--", "example.py"),
                adapter._quality_gate_command(),
                (
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    "main",
                    "--head",
                    "shanks/run/1",
                    "--title",
                    "feat: deliver",
                    "--body",
                    "why",
                ),
            )
            with patch("workflow.adapters._run_subprocess", side_effect=fake_run):
                for command in (*probes, *slow):
                    adapter._run(command)

        for command in probes:
            with self.subTest(command=command):
                self.assertEqual(timeouts[command], adapter.probe_timeout_seconds)
        for command in slow:
            with self.subTest(command=command):
                self.assertEqual(timeouts[command], adapter.timeout_seconds)
        self.assertLess(adapter.probe_timeout_seconds, adapter.timeout_seconds)

    def test_repository_subprocesses_are_clamped_to_the_remaining_run_budget(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            adapter = GitHubAdapter(
                Path(directory),
                initial_dirty_files=(),
                stale_after_days=None,
            )
            timeouts: dict[tuple[str, ...], float] = {}

            def fake_run(command, *, cwd, timeout, env, **kwargs):
                timeouts[tuple(command)] = timeout
                return subprocess.CompletedProcess(command, 0, "", "")

            probe = ("git", "branch", "--show-current")
            gate = adapter._quality_gate_command()
            handoff = ("git", "add", "--", "example.py")
            with (
                patch("workflow.adapters._run_subprocess", side_effect=fake_run),
                run_deadline_scope(5.0),
            ):
                for command in (probe, gate, handoff):
                    adapter._run(command)

        for command in (probe, gate, handoff):
            with self.subTest(command=command):
                self.assertLessEqual(timeouts[command], 5.0)
        self.assertLess(timeouts[gate], adapter.timeout_seconds)
        self.assertLess(timeouts[probe], adapter.probe_timeout_seconds)

    def test_repository_subprocesses_fail_before_launch_once_the_budget_is_gone(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            adapter = GitHubAdapter(
                Path(directory),
                initial_dirty_files=(),
                stale_after_days=None,
            )
            with (
                patch("workflow.adapters._run_subprocess") as run,
                run_deadline_scope(0.0),
            ):
                result = adapter._run(("git", "branch", "--show-current"))

        run.assert_not_called()
        self.assertEqual(result.status, "failed")
        self.assertIn("deadline has elapsed", result.error)

    def test_nodes_publish_the_remaining_run_budget_to_repository_adapters(
        self,
    ) -> None:
        observed: list[float | None] = []

        class BudgetProbeRepository:
            def preflight(self) -> AgentResult:
                observed.append(remaining_deadline_seconds())
                return AgentResult(status="completed", assigned_model="probe")

        stub = StubAgentAdapter("stub", "stub")
        node = create_nodes(
            NodeDependencies(
                planner=stub,
                builder=stub,
                critic=stub,
                validator=stub,
                debugger=stub,
                repository=BudgetProbeRepository(),
            )
        )["preflight"]

        node(
            {
                "task": "budgeted run",
                "run_started_at": time.time() - 100.0,
                "max_runtime_seconds": 120.0,
            },
            {"configurable": {"thread_id": "run/1"}},
        )

        self.assertEqual(len(observed), 1)
        remaining = observed[0]
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining, 15.0)
        self.assertLessEqual(remaining, 20.0)
        self.assertIsNone(remaining_deadline_seconds())

    def test_policy_gate_scan_is_clamped_to_the_remaining_run_budget(self) -> None:
        if shutil.which("gitleaks") is None:
            self.skipTest("gitleaks is not installed; see ./shanks doctor")
        with TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "example.py").write_text("value = 1\n", encoding="utf-8")
            completed = subprocess.CompletedProcess(("gitleaks",), 0, "", "")

            with (
                patch(
                    "workflow.adapters._run_subprocess",
                    return_value=completed,
                ) as run,
                run_deadline_scope(3.0),
            ):
                self.assertEqual(_scan_for_secrets(project, ["example.py"]), "")
            self.assertLessEqual(run.call_args.kwargs["timeout"], 3.0)

            with (
                patch("workflow.adapters._run_subprocess") as run,
                run_deadline_scope(0.0),
            ):
                self.assertIsNone(_scan_for_secrets(project, ["example.py"]))
            run.assert_not_called()

    def test_probe_timeout_seconds_must_be_positive(self) -> None:
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                GitHubAdapter(
                    Path(directory),
                    initial_dirty_files=(),
                    probe_timeout_seconds=0,
                )

    def test_cheap_critic_is_an_adapter_with_a_model_name(self) -> None:
        result = CheapCriticAdapter().run(AgentRequest(task="review this"))

        self.assertEqual(result.assigned_model, "cheap-critic-model")
        self.assertTrue(result.approved)

    def test_subprocess_adapter_returns_the_same_result_shape(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=(sys.executable, "-c", "print('adapter ok')"),
            model_name="test-cli",
        )

        result = adapter.run(AgentRequest(task="test task"))

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.assigned_model, "test-cli")
        self.assertIn("adapter ok", result.feedback)
        self.assertGreater(result.input_tokens, 0)
        self.assertGreater(result.output_tokens, 0)
        self.assertIn("Task: test task", result.prompt)
        self.assertEqual(result.commands[0][0], sys.executable)

    def test_subprocess_adapter_accepts_versioned_python_executables(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=("/usr/local/bin/python3.11", "-c", "print('adapter ok')"),
            model_name="versioned-python",
        )
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout="adapter ok",
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed) as run:
            result = adapter.run(AgentRequest(task="test versioned Python"))

        self.assertEqual(result.status, "completed")
        self.assertEqual(run.call_args.args[0], adapter.command)

    def test_subprocess_adapter_uses_remaining_runtime_budget(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=(sys.executable, "-c", "print('adapter ok')"),
            model_name="test-cli",
        )
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout="ok",
            stderr="",
        )

        with patch(
            "workflow.adapters._run_subprocess",
            return_value=completed,
        ) as run:
            adapter.run(AgentRequest(task="test task", timeout_seconds=2.5))

        self.assertEqual(run.call_args.kwargs["timeout"], 2.5)

    def test_agent_subprocesses_only_receive_allowlisted_environment_keys(
        self,
    ) -> None:
        adapter = SubprocessAgentAdapter(
            command=(sys.executable, "-c", "print('adapter ok')"),
            model_name="test-cli",
        )
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout="ok",
            stderr="",
        )

        with (
            patch.dict(
                os.environ,
                {
                    "GH_TOKEN": "ghp_agent_secret",
                    "GITHUB_TOKEN": "github_pat_agent_secret",
                    "AWS_SECRET_ACCESS_KEY": "unrelated_cloud_secret",
                    "PATH": "/usr/bin",
                    "ANTHROPIC_API_KEY": "sk-agent-key",
                },
                clear=True,
            ),
            patch(
                "workflow.adapters._run_subprocess",
                return_value=completed,
            ) as run,
        ):
            adapter.run(AgentRequest(task="test task"))

        environment = run.call_args.kwargs["env"]
        self.assertNotIn("GH_TOKEN", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", environment)
        self.assertEqual(environment["PATH"], "/usr/bin")
        self.assertEqual(environment["ANTHROPIC_API_KEY"], "sk-agent-key")

    def test_run_subprocess_kills_grandchildren_on_timeout(self) -> None:
        with TemporaryDirectory() as directory:
            script = "(sleep 30 & echo $! > grandchild.pid); sleep 30"

            with self.assertRaises(subprocess.TimeoutExpired):
                _run_subprocess(
                    ("bash", "-c", script),
                    cwd=Path(directory),
                    env=dict(os.environ),
                    timeout=0.5,
                )

            grandchild_pid = int(
                (Path(directory) / "grandchild.pid").read_text().strip()
            )
            time.sleep(0.3)
            with self.assertRaises(ProcessLookupError):
                os.kill(grandchild_pid, 0)

    def test_subprocess_adapter_rejects_unapproved_executables(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=("sh", "-c", "echo unsafe"),
            model_name="unsafe-cli",
        )

        with patch("workflow.adapters._run_subprocess") as run:
            result = adapter.run(AgentRequest(task="test task"))

        self.assertEqual(result.status, "failed")
        self.assertIn("unapproved executable", result.error)
        run.assert_not_called()

    def test_subprocess_adapter_rejects_working_directory_escape(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=(sys.executable, "-c", "print('adapter ok')"),
            model_name="test-cli",
            working_directory=Path("/tmp/shanks"),
            allowed_directories=(Path("/tmp/shanks"),),
        )

        with patch("workflow.adapters._run_subprocess") as run:
            result = adapter.run(
                AgentRequest(task="test task", working_directory=Path("/tmp"))
            )

        self.assertEqual(result.status, "failed")
        self.assertIn("outside the configured working directories", result.error)
        run.assert_not_called()

    def test_subprocess_adapter_redacts_credentials_from_output(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=(sys.executable, "-c", "print('adapter ok')"),
            model_name="test-cli",
        )
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout="ghp_test_secret_123456 api_key=private-value",
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed):
            result = adapter.run(AgentRequest(task="test task"))

        self.assertNotIn("ghp_test_secret_123456", result.feedback)
        self.assertNotIn("private-value", result.feedback)
        self.assertIn("[REDACTED]", result.feedback)

    def test_local_test_adapter_maps_a_failed_suite(self) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=1,
            stdout="FAIL: test_example",
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed) as run:
            result = adapter.run(AgentRequest(task="validate this"))

        self.assertEqual(result.status, "validation_failed")
        self.assertEqual(result.failure_class, "validation")
        self.assertFalse(result.validation_passed)
        self.assertEqual(result.validation_errors, ["FAIL: test_example"])
        self.assertEqual(
            run.call_args.args[0],
            (sys.executable, "-m", "unittest", "discover", "-s", "tests"),
        )

    def test_local_test_adapter_runs_the_item_validation_command(self) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout="item tests passed",
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed) as run:
            result = adapter.run(
                AgentRequest(
                    task="validate this item",
                    validation_command=(
                        f"{sys.executable} -m unittest tests.test_graph"
                    ),
                )
            )

        self.assertEqual(result.status, "validated")
        self.assertTrue(result.validation_passed)
        self.assertEqual(result.test_output, "item tests passed")
        self.assertEqual(
            run.call_args.args[0],
            (sys.executable, "-m", "unittest", "tests.test_graph"),
        )

    def test_local_test_adapter_accepts_versioned_python_validation_commands(
        self,
    ) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=(),
            returncode=0,
            stdout="item tests passed",
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed) as run:
            result = adapter.run(
                AgentRequest(
                    task="validate this item",
                    validation_command=(
                        "/usr/local/bin/python3.11 -m unittest tests.test_graph"
                    ),
                )
            )

        self.assertEqual(result.status, "validated")
        self.assertTrue(result.validation_passed)
        self.assertEqual(
            run.call_args.args[0],
            ("/usr/local/bin/python3.11", "-m", "unittest", "tests.test_graph"),
        )

    def test_local_test_adapter_rejects_shell_and_inline_code_commands(self) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        rejected = (
            'bash -c "rm -rf /"',
            "bash tests/run.sh",
            "/bin/sh -c true",
            f"{sys.executable} -c \"import os; os.system('id')\"",
            f"{sys.executable} -Ic print(1)",
        )

        for command in rejected:
            with self.subTest(command=command):
                with patch("workflow.adapters._run_subprocess") as run:
                    result = adapter.run(
                        AgentRequest(task="validate", validation_command=command)
                    )

                run.assert_not_called()
                self.assertEqual(result.status, "validation_failed")
                self.assertFalse(result.validation_passed)
                self.assertIn("Invalid validation command", result.error or "")

    def test_local_test_adapter_accepts_module_and_script_options_after_boundary(
        self,
    ) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        accepted = (
            (
                f"{sys.executable} -m pytest -c pytest.ini",
                (sys.executable, "-m", "pytest", "-c", "pytest.ini"),
            ),
            (
                f"{sys.executable} tests/run.py -c config.ini",
                (sys.executable, "tests/run.py", "-c", "config.ini"),
            ),
        )

        for command, expected in accepted:
            with self.subTest(command=command):
                completed = subprocess.CompletedProcess(
                    args=(),
                    returncode=0,
                    stdout="item tests passed",
                    stderr="",
                )
                with patch(
                    "workflow.adapters._run_subprocess",
                    return_value=completed,
                ) as run:
                    result = adapter.run(
                        AgentRequest(task="validate", validation_command=command)
                    )

                self.assertEqual(result.status, "validated")
                self.assertTrue(result.validation_passed)
                self.assertEqual(run.call_args.args[0], expected)

    def test_debugger_adapter_maps_structured_failure_analysis(self) -> None:
        adapter = DebuggerAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout=(
                '{"root_cause": "The handler uses the wrong field.", '
                '"builder_instructions": "Read the request field and add a '
                'regression test.", '
                '"feedback": "The failing assertion confirms the mismatch."}'
            ),
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed) as run:
            result = adapter.run(
                AgentRequest(
                    task="Fix the handler",
                    item_id="item-1",
                    item_title="Correct the handler",
                    item_description="The handler must use the request field.",
                    instructions="Validation failure:\nFAIL: expected request",
                )
            )

        self.assertEqual(result.status, "debugged")
        self.assertEqual(result.root_cause, "The handler uses the wrong field.")
        self.assertEqual(
            result.builder_instructions,
            "Read the request field and add a regression test.",
        )
        self.assertIn("FAIL: expected request", run.call_args.kwargs["input_text"])
        self.assertIn("read-only", run.call_args.kwargs["input_text"])
        self.assertIn(
            "The handler must use the request field.",
            run.call_args.kwargs["input_text"],
        )
        self.assertIn("read-only", adapter.command)
        self.assertIn("--output-schema", adapter.command)

    def test_debugger_adapter_claude_tool_uses_read_only_tools(self) -> None:
        adapter = DebuggerAdapter(Path("/tmp/shanks"), tool="claude")

        self.assertIn("--permission-mode", adapter.command)
        self.assertIn("plan", adapter.command)
        self.assertIn("--tools", adapter.command)
        self.assertIn("Read,Grep,Glob", adapter.command)
        self.assertIn("--json-schema", adapter.command)

    def test_policy_gate_passes_with_no_dirty_files(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        status = subprocess.CompletedProcess(
            args=(), returncode=0, stdout="", stderr=""
        )

        with patch("workflow.adapters._run_subprocess", side_effect=[status]):
            result = adapter.policy_gate("item-1", "First item", [])

        self.assertEqual(result.status, "policy_gate_passed")

    def test_policy_gate_blocks_guarded_dependency_files(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        status = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=" M requirements.txt\n", stderr=""
        )

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SHANKS_ALLOW_DEPENDENCY_EDIT", None)
            with patch("workflow.adapters._run_subprocess", side_effect=[status]):
                result = adapter.policy_gate("item-1", "First item", [])

        self.assertEqual(result.status, "policy_gate_failed")
        self.assertEqual(result.failure_class, "guardrail")
        self.assertIn("requirements.txt", result.error or "")

    def test_policy_gate_override_env_var_skips_guarded_check(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        status = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=" M requirements.txt\n", stderr=""
        )

        with patch.dict(os.environ, {"SHANKS_ALLOW_DEPENDENCY_EDIT": "1"}):
            with patch("workflow.adapters._run_subprocess", side_effect=[status]):
                with patch("workflow.adapters._scan_for_secrets", return_value=""):
                    result = adapter.policy_gate("item-1", "First item", [])

        self.assertEqual(result.status, "policy_gate_passed")

    def test_policy_gate_blocks_a_flagged_secret(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        status = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=" M app.py\n", stderr=""
        )

        with patch("workflow.adapters._run_subprocess", side_effect=[status]):
            with patch(
                "workflow.adapters._scan_for_secrets",
                return_value="generic-api-key in app.py",
            ):
                result = adapter.policy_gate("item-1", "First item", [])

        self.assertEqual(result.status, "policy_gate_failed")
        self.assertEqual(result.failure_class, "guardrail")
        self.assertIn("generic-api-key", result.error or "")

    def test_policy_gate_fails_closed_when_the_scan_cannot_run(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        status = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=" M app.py\n", stderr=""
        )

        with patch("workflow.adapters._run_subprocess", side_effect=[status]):
            with patch("workflow.adapters._scan_for_secrets", return_value=None):
                result = adapter.policy_gate("item-1", "First item", [])

        self.assertEqual(result.status, "policy_gate_failed")
        self.assertEqual(result.failure_class, "guardrail")

    def test_policy_gate_passes_a_clean_change(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        status = subprocess.CompletedProcess(
            args=(), returncode=0, stdout=" M app.py\n", stderr=""
        )

        with patch("workflow.adapters._run_subprocess", side_effect=[status]):
            with patch("workflow.adapters._scan_for_secrets", return_value=""):
                result = adapter.policy_gate("item-1", "First item", [])

        self.assertEqual(result.status, "policy_gate_passed")
        self.assertEqual(result.files_touched, ["app.py"])

    def test_github_adapter_commits_only_fresh_story_files(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=("existing.py",),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout=" M existing.py\n M workflow/new.py\n?? new.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(args=(), returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout="diff --git a/workflow/new.py b/workflow/new.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="Quality gates passed.\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout="[validation-node abc123] feat: item-1 - First item",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="abc123\n", stderr=""
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.commit_item(
                "item-1",
                "First item",
                ["existing.py", "workflow/new.py", "new.py"],
            )

        self.assertEqual(result.status, "committed")
        self.assertEqual(result.files_touched, ["workflow/new.py", "new.py"])
        self.assertIn("diff --git", result.diff)
        self.assertEqual(
            run.call_args_list[1].args[0],
            ("git", "add", "--", "workflow/new.py", "new.py"),
        )
        self.assertEqual(
            run.call_args_list[4].args[0],
            (
                "git",
                "commit",
                "--only",
                "-m",
                "feat: item-1 - First item",
                "--",
                "workflow/new.py",
                "new.py",
            ),
        )
        self.assertEqual(
            result.commands[2],
            [
                "git",
                "diff",
                "--cached",
                "--no-ext-diff",
                "--",
                "workflow/new.py",
                "new.py",
            ],
        )
        self.assertEqual(
            result.commands[3][:3],
            [sys.executable, "scripts/quality_gates.py", "--diff-base"],
        )

    def test_github_adapter_dry_run_previews_without_mutating(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="?? item.py\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout="",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout="item.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=1,
                stdout="diff --git a/item.py b/item.py\n",
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
        ]

        with (
            patch.dict("os.environ", {"SHANKS_MODE": "dry-run"}),
            patch("workflow.adapters._run_subprocess", side_effect=responses) as run,
        ):
            commit = adapter.commit_item("item-1", "First item", ["item.py"])
            push = adapter.push_branch()
            pull_request = adapter.open_pull_request(
                "Build the workflow",
                branch="validation-node",
            )

        self.assertEqual(commit.status, "commit_preview")
        self.assertIn("diff --git", commit.diff)
        self.assertEqual(push.status, "branch_push_preview")
        self.assertEqual(push.feedback, "validation-node")
        self.assertEqual(pull_request.status, "pull_request_preview")
        self.assertEqual(run.call_count, 5)
        executed = [call.args[0] for call in run.call_args_list]
        self.assertNotIn(("git", "add", "--", "item.py"), executed)
        self.assertNotIn(("git", "push", "-u", "origin", "validation-node"), executed)
        self.assertFalse(
            any(command[:3] == ("gh", "pr", "create") for command in executed)
        )

    def test_github_adapter_rejects_paths_outside_the_project(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            outside = Path(directory) / "outside.py"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            (root / "link.py").symlink_to(outside)
            adapter = GitHubAdapter(root, initial_dirty_files=())

            self.assertIsNone(adapter._normalize_file("../outside.py"))
            self.assertIsNone(adapter._normalize_file("link.py"))
            self.assertEqual(adapter._normalize_file("inside.py"), "inside.py")

    def test_github_adapter_rejects_unapproved_commands(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())

        with patch("workflow.adapters._run_subprocess") as run:
            result = adapter._run(("gh", "auth", "token"))

        self.assertEqual(result.status, "failed")
        self.assertIn("unapproved Git or GitHub command", result.error)
        run.assert_not_called()

    def test_github_adapter_enforces_branch_and_policy_boundaries(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
            reviewers=("alice",),
            labels=("needs-review",),
            reviewer_allowlist=("alice",),
            label_allowlist=("needs-review",),
        )

        with patch("workflow.adapters._run_subprocess") as run:
            protected_push = adapter._run(("git", "push", "-u", "origin", "main"))
            unapproved_label = adapter._run(
                (
                    "gh",
                    "pr",
                    "create",
                    "--base",
                    "main",
                    "--head",
                    "feature",
                    "--title",
                    "title",
                    "--body",
                    "body",
                    "--label",
                    "unsafe",
                )
            )

        self.assertEqual(protected_push.status, "failed")
        self.assertEqual(unapproved_label.status, "failed")
        run.assert_not_called()

    def test_github_adapter_rejects_policy_values_outside_the_allowlist(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside its configured allowlist"):
            GitHubAdapter(
                Path("/tmp/shanks"),
                initial_dirty_files=(),
                reviewers=("untrusted",),
                reviewer_allowlist=("alice",),
            )

    def test_github_quality_gate_command_is_allowlisted(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())

        with patch(
            "workflow.adapters._run_subprocess",
            return_value=subprocess.CompletedProcess(
                args=(), returncode=0, stdout="Quality gates passed.", stderr=""
            ),
        ) as run:
            result = adapter._run(adapter._quality_gate_command(staged=True))

        self.assertEqual(result.status, "completed")
        self.assertEqual(
            run.call_args.args[0],
            (
                sys.executable,
                "scripts/quality_gates.py",
                "--diff-base",
                "origin/main",
                "--staged",
            ),
        )

    def test_github_quality_gate_failure_stops_before_commit(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="?? item.py\n", stderr=""
            ),
            subprocess.CompletedProcess(args=(), returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="diff", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="diff is too large"
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.commit_item("item-1", "First item", ["item.py"])

        self.assertEqual(result.status, "failed")
        self.assertIn("diff is too large", result.error)
        self.assertEqual(run.call_count, 4)

    def test_github_preflight_checks_branch_auth_and_tests(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        responses = [
            AgentResult(
                status="completed", assigned_model="github", feedback="feature"
            ),
            AgentResult(status="completed", assigned_model="github", feedback=""),
            AgentResult(
                status="completed", assigned_model="github", feedback="auth ok"
            ),
            AgentResult(
                status="completed",
                assigned_model="github",
                feedback="Quality gates passed.",
            ),
        ]

        with (
            patch("workflow.adapters.shutil.which", return_value="/usr/bin/tool"),
            patch.object(
                GitHubAdapter,
                "_run",
                side_effect=responses,
            ) as run,
            patch.object(
                LocalTestAdapter,
                "run",
                return_value=AgentResult(
                    status="validated",
                    assigned_model="local-tests",
                    feedback="Ran 10 tests in 0.1s",
                ),
            ) as tests,
        ):
            result = adapter.preflight()

        self.assertEqual(result.status, "preflight_passed")
        self.assertEqual(result.test_output, "Ran 10 tests in 0.1s")
        self.assertEqual(run.call_count, 4)
        tests.assert_called_once()

    def test_github_preflight_rejects_missing_tools(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())

        def which(tool: str) -> str | None:
            return None if tool == "gitleaks" else "/usr/bin/tool"

        with (
            patch("workflow.adapters.shutil.which", side_effect=which),
            patch.object(GitHubAdapter, "_run") as run,
            patch.object(LocalTestAdapter, "run") as tests,
        ):
            result = adapter.preflight()

        self.assertEqual(result.status, "preflight_failed")
        self.assertIn("Missing required tools: gitleaks", result.error)
        run.assert_not_called()
        tests.assert_not_called()

    def test_github_preflight_rejects_dirty_worktree(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        responses = [
            AgentResult(
                status="completed", assigned_model="github", feedback="feature"
            ),
            AgentResult(
                status="completed", assigned_model="github", feedback=" M README.md"
            ),
        ]

        with (
            patch("workflow.adapters.shutil.which", return_value="/usr/bin/tool"),
            patch.object(
                GitHubAdapter,
                "_run",
                side_effect=responses,
            ) as run,
            patch.object(LocalTestAdapter, "run") as tests,
        ):
            result = adapter.preflight()

        self.assertEqual(result.status, "preflight_failed")
        self.assertIn("Working tree is not clean", result.error)
        self.assertEqual(run.call_count, 2)
        tests.assert_not_called()

    def test_github_adapter_redacts_pr_text_and_limits_environment(self) -> None:
        adapter = GitHubAdapter(Path("/tmp/shanks"), initial_dirty_files=())
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="branch", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed", stderr=""
            ),
            subprocess.CompletedProcess(args=(), returncode=0, stdout="[]", stderr=""),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout="https://github.com/example/shanks/pull/1",
                stderr="",
            ),
        ]

        with (
            patch.dict(
                "os.environ",
                {
                    "GH_TOKEN": "ghp_test_secret_123456",
                    "GITHUB_TOKEN": "github_pat_other_secret",
                    "UNRELATED_SECRET": "do-not-pass",
                },
                clear=True,
            ),
            patch(
                "workflow.adapters._run_subprocess",
                side_effect=responses,
            ) as run,
        ):
            result = adapter.publish_pr("Ship ghp_test_secret_123456")

        self.assertEqual(result.status, "pr_created")
        git_environment = run.call_args_list[0].kwargs["env"]
        github_environment = run.call_args_list[2].kwargs["env"]
        self.assertEqual(git_environment["GIT_TERMINAL_PROMPT"], "0")
        self.assertNotIn("GH_TOKEN", git_environment)
        self.assertEqual(github_environment["GH_TOKEN"], "ghp_test_secret_123456")
        self.assertNotIn("GITHUB_TOKEN", github_environment)
        self.assertEqual(github_environment["GH_PROMPT_DISABLED"], "1")
        self.assertNotIn("UNRELATED_SECRET", github_environment)
        create_command = run.call_args_list[-1].args[0]
        self.assertNotIn("ghp_test_secret_123456", create_command[-1])
        self.assertIn("[REDACTED]", create_command[-1])

    def test_github_adapter_pushes_then_creates_a_pr(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
            reviewers=("alice",),
            labels=("enhancement",),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="[]\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout="https://github.com/example/shanks/pull/1\n",
                stderr="",
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.publish_pr("Build the workflow")

        self.assertEqual(result.status, "pr_created")
        self.assertEqual(result.pr_url, "https://github.com/example/shanks/pull/1")
        self.assertEqual(result.pr_reviewers, ["alice"])
        self.assertEqual(result.pr_labels, ["enhancement"])
        self.assertEqual(
            run.call_args_list[1].args[0],
            ("git", "push", "-u", "origin", "validation-node"),
        )
        self.assertEqual(
            run.call_args_list[3].args[0][:5],
            ("gh", "pr", "create", "--base", "main"),
        )
        self.assertEqual(
            run.call_args_list[3].args[0][-4:],
            ("--label", "enhancement", "--reviewer", "alice"),
        )

    def test_github_adapter_reuses_an_existing_pr_for_the_branch(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout='[{"url":"https://github.com/example/shanks/pull/1"}]\n',
                stderr="",
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.publish_pr("Build the workflow")

        self.assertEqual(result.status, "pr_created")
        self.assertEqual(result.pr_url, "https://github.com/example/shanks/pull/1")
        self.assertEqual(run.call_count, 3)
        self.assertEqual(
            run.call_args_list[2].args[0],
            (
                "gh",
                "pr",
                "list",
                "--head",
                "validation-node",
                "--state",
                "all",
                "--json",
                "number,url,state,mergedAt,title,body,updatedAt,mergeStateStatus,"
                "labels,reviewRequests,latestReviews,headRefName",
                "--limit",
                "20",
            ),
        )

    def test_github_adapter_reconciles_open_pr_text_policy_and_staleness(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
            reviewers=("alice",),
            labels=("needs-review",),
            stale_after_days=None,
        )
        title, body = adapter._pull_request_text("Build the workflow")
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "number": 7,
                            "url": "https://github.com/example/shanks/pull/7",
                            "state": "OPEN",
                            "mergedAt": None,
                            "title": "Old title",
                            "body": "Old body",
                            "mergeStateStatus": "BEHIND",
                            "labels": [{"name": "existing"}],
                            "reviewRequests": [{"login": "alice"}],
                        }
                    ]
                ),
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="edited\n", stderr=""
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.publish_pr("Build the workflow")

        self.assertEqual(result.status, "pr_stale")
        self.assertEqual(result.pr_state, "open")
        self.assertTrue(result.pr_stale)
        self.assertEqual(result.pr_number, "7")
        self.assertEqual(
            run.call_args_list[3].args[0],
            (
                "gh",
                "pr",
                "edit",
                "7",
                "--title",
                title,
                "--body",
                body,
                "--add-label",
                "needs-review",
            ),
        )

    def test_github_adapter_policy_updates_are_idempotent(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
            reviewers=("alice",),
            labels=("needs-review",),
            stale_after_days=None,
        )
        title, body = adapter._pull_request_text("Build the workflow")
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "number": 7,
                            "url": "https://github.com/example/shanks/pull/7",
                            "state": "OPEN",
                            "title": title,
                            "body": body,
                            "mergeStateStatus": "CLEAN",
                            "labels": [{"name": "Needs-Review"}],
                            "reviewRequests": [],
                            "latestReviews": [{"author": {"login": "Alice"}}],
                        }
                    ]
                ),
                stderr="",
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.publish_pr("Build the workflow")

        self.assertEqual(result.status, "pr_created")
        self.assertFalse(result.pr_stale)
        self.assertEqual(run.call_count, 3)

    def test_github_adapter_reopens_closed_pr_but_stops_on_merged_pr(self) -> None:
        closed_adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
            stale_after_days=None,
            reopen_closed=True,
        )
        closed_responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout='[{"number":7,"url":"https://github.com/example/shanks/pull/7",'
                '"state":"CLOSED","mergedAt":null}]',
                stderr="",
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="reopened\n", stderr=""
            ),
        ]
        with patch(
            "workflow.adapters._run_subprocess", side_effect=closed_responses
        ) as run:
            closed = closed_adapter.publish_pr("Build the workflow")

        self.assertEqual(closed.status, "pr_reopened")
        self.assertEqual(closed.pr_state, "open")
        self.assertEqual(run.call_args_list[3].args[0], ("gh", "pr", "reopen", "7"))

        merged_adapter = GitHubAdapter(
            Path("/tmp/shanks"), initial_dirty_files=(), stale_after_days=None
        )
        merged_responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(),
                returncode=0,
                stdout='[{"number":7,"url":"https://github.com/example/shanks/pull/7",'
                '"state":"CLOSED","mergedAt":"2026-08-01T00:00:00Z"}]',
                stderr="",
            ),
        ]
        with patch(
            "workflow.adapters._run_subprocess", side_effect=merged_responses
        ) as run:
            merged = merged_adapter.publish_pr("Build the workflow")

        self.assertEqual(merged.status, "pr_merged")
        self.assertEqual(merged.pr_state, "merged")
        self.assertEqual(run.call_count, 3)

    def test_github_adapter_reports_commit_failure(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="?? item.py\n", stderr=""
            ),
            subprocess.CompletedProcess(args=(), returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="diff", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="Quality gates passed.", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="commit failed"
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.commit_item("item-1", "First item", ["item.py"])

        self.assertEqual(result.status, "failed")
        self.assertEqual(run.call_count, 5)

    def test_github_adapter_stops_after_push_failure(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="push failed"
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.publish_pr("Build the workflow")

        self.assertEqual(result.status, "failed")
        self.assertEqual(run.call_count, 2)

    def test_github_adapter_reports_pull_request_creation_failure(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="validation-node\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="pushed\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="PR failed"
            ),
        ]

        with patch("workflow.adapters._run_subprocess", side_effect=responses) as run:
            result = adapter.publish_pr("Build the workflow")

        self.assertEqual(result.status, "failed")
        self.assertEqual(run.call_count, 3)

    def test_default_dependencies_use_local_tests(self) -> None:
        dependencies = default_dependencies()
        self.assertIsInstance(dependencies.planner, CodexAdapter)
        self.assertIsInstance(dependencies.builder, RalphAdapter)
        self.assertIsInstance(dependencies.validator, LocalTestAdapter)
        self.assertIsInstance(dependencies.debugger, DebuggerAdapter)
        self.assertIsInstance(dependencies.repository, GitHubAdapter)

    def test_default_dependencies_share_the_configured_base_branch(self) -> None:
        dependencies = default_dependencies(base_branch="develop")

        self.assertEqual(dependencies.repository.base_branch, "develop")
        self.assertIn("develop", dependencies.repository.protected_branches)

    def test_default_dependencies_allow_a_claude_workflow(self) -> None:
        dependencies = default_dependencies(tool="claude")

        self.assertIsInstance(dependencies.planner, ClaudeAdapter)
        self.assertIsInstance(dependencies.builder, RalphAdapter)
        self.assertIn("--tool", dependencies.builder.command)
        self.assertEqual(
            dependencies.builder.command[
                dependencies.builder.command.index("--tool") + 1
            ],
            "claude",
        )
        self.assertEqual(dependencies.critic.model_name, CLAUDE_OPUS_48_MODEL)
        self.assertEqual(dependencies.debugger.model_name, "claude-debugger")

    def test_gpt_5_6_luna_critic_uses_read_only_max_reasoning(self) -> None:
        adapter = GPT56LunaCriticAdapter(Path("/tmp/shanks"))

        self.assertEqual(adapter.model_name, "gpt-5.6-luna")
        self.assertEqual(adapter.reasoning_effort, "max")
        self.assertIn("--sandbox", adapter.command)
        self.assertIn("read-only", adapter.command)
        self.assertIn("--model", adapter.command)
        self.assertIn("gpt-5.6-luna", adapter.command)
        self.assertIn('model_reasoning_effort="max"', adapter.command)

    def test_gpt_5_6_luna_critic_maps_structured_output(self) -> None:
        adapter = GPT56LunaCriticAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout='{"approved": false, "feedback": "Needs a test."}',
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed):
            result = adapter.run(AgentRequest(task="review this"))

        self.assertEqual(result.status, "critic_audited")
        self.assertEqual(result.assigned_model, "gpt-5.6-luna")
        self.assertFalse(result.approved)
        self.assertEqual(result.feedback, "Needs a test.")

    def test_claude_opus_4_8_critic_uses_read_only_medium_effort(self) -> None:
        adapter = ClaudeOpus48CriticAdapter(Path("/tmp/shanks"))

        self.assertEqual(adapter.model_name, CLAUDE_OPUS_48_MODEL)
        self.assertEqual(adapter.effort, CLAUDE_OPUS_48_EFFORT)
        self.assertIn("--model", adapter.command)
        self.assertIn("claude-opus-4-8", adapter.command)
        self.assertIn("--effort", adapter.command)
        self.assertIn("medium", adapter.command)
        self.assertIn("--permission-mode", adapter.command)
        self.assertIn("plan", adapter.command)
        self.assertIn("--tools", adapter.command)
        self.assertIn("Read,Grep,Glob", adapter.command)
        self.assertIn("--json-schema", adapter.command)

    def test_claude_opus_4_8_critic_maps_structured_output(self) -> None:
        adapter = ClaudeOpus48CriticAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout='{"approved": true, "feedback": "Looks good."}',
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed):
            result = adapter.run(AgentRequest(task="review this"))

        self.assertEqual(result.status, "critic_audited")
        self.assertEqual(result.assigned_model, CLAUDE_OPUS_48_MODEL)
        self.assertTrue(result.approved)
        self.assertEqual(result.feedback, "Looks good.")

    def test_hooks_md_matches_adapter_tool_scopes(self) -> None:
        repo_root = Path(__file__).parents[1]
        hooks_md = (repo_root / "hooks" / "HOOKS.md").read_text(encoding="utf-8")
        ralph_sh = (repo_root / "scripts" / "ralph" / "ralph.sh").read_text(
            encoding="utf-8"
        )

        def tools_value(command: tuple[str, ...]) -> str:
            return command[command.index("--tools") + 1]

        project = Path("/tmp/shanks")
        build_agent_tools = tools_value(ClaudeAdapter(project, read_only=False).command)
        read_only_claude_tools = tools_value(
            ClaudeAdapter(project, read_only=True).command
        )
        debugger_claude_tools = tools_value(
            DebuggerAdapter(project, tool="claude").command
        )
        critic_tools = tools_value(ClaudeOpus48CriticAdapter(project).command)

        self.assertEqual(read_only_claude_tools, debugger_claude_tools)
        self.assertEqual(read_only_claude_tools, critic_tools)

        self.assertIn(f"--tools {build_agent_tools}", ralph_sh)
        self.assertIn(f"--tools {build_agent_tools}", hooks_md)
        self.assertIn(f"--tools {read_only_claude_tools}", hooks_md)

        self.assertNotIn("--tools", GPT56LunaCriticAdapter(project).command)
        self.assertNotIn("--tools", DebuggerAdapter(project, tool="codex").command)

    def test_luna_dependency_factory_wires_the_critic_node(self) -> None:
        dependencies = gpt_5_6_luna_dependencies(Path("/tmp/shanks"))

        self.assertIsInstance(dependencies.critic, GPT56LunaCriticAdapter)

    def test_claude_dependency_factory_wires_the_critic_node(self) -> None:
        dependencies = claude_opus_4_8_dependencies(Path("/tmp/shanks"))

        self.assertIsInstance(dependencies.critic, ClaudeOpus48CriticAdapter)

    def test_ralph_adapter_selects_a_project_skill(self) -> None:
        adapter = RalphAdapter(
            Path("/tmp/target-project"),
            base_directory=Path("/tmp/agent-engine"),
            tool="codex",
            skill_name="ponytail",
            max_iterations=3,
        )

        self.assertEqual(adapter.model_name, "ralph:codex")
        self.assertEqual(adapter.working_directory, Path("/tmp/agent-engine"))
        self.assertEqual(
            adapter.command[2:4],
            ("--project-dir", "/tmp/target-project"),
        )
        self.assertEqual(adapter.command[-3:], ("--skill", "ponytail", "3"))

    def test_ralph_adapter_passes_the_enriched_requirement_to_ralph(self) -> None:
        adapter = RalphAdapter(
            Path("/tmp/target-project"),
            base_directory=Path("/tmp/agent-engine"),
        )
        request = AgentRequest(
            task="Fix the workflow",
            item_id="item-1",
            item_title="Repair validation",
            item_description="Root cause: the setup is missing.",
            prd_items=[
                {
                    "id": "item-1",
                    "title": "Repair validation",
                    "description": "Root cause: the setup is missing.",
                    "passes": True,
                    "validation": False,
                },
                {
                    "id": "item-2",
                    "title": "Next item",
                    "description": "Leave this requirement unchanged.",
                    "passes": False,
                    "validation": False,
                },
            ],
            instructions="Add the setup before rerunning tests.",
        )
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout=(
                "fixed\n"
                "RALPH_UNCERTAINTIES:\n"
                "- Chose a fallback when the requirement was ambiguous.\n"
                "RALPH_ERROR: none\n"
                "<promise>ITEM_BUILT</promise>\n"
            ),
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed) as run:
            result = adapter.run(request)

        self.assertEqual(
            result.uncertainties,
            ["Chose a fallback when the requirement was ambiguous."],
        )

        command = run.call_args.args[0]
        self.assertEqual(command[-4:-2], ("--graph-item-id", "item-1"))
        self.assertEqual(command[-2], "--graph-instructions")
        self.assertIn("PRD requirement: Root cause: the setup is missing.", command[-1])
        self.assertIn("Leave this requirement unchanged.", command[-1])
        self.assertIn("Add the setup before rerunning tests.", command[-1])

    def test_ralph_adapter_isolates_run_metadata_with_a_worktree(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            base = root / "engine"
            target.mkdir()
            base.mkdir()
            adapter = RalphAdapter(target, base_directory=base)
            request = AgentRequest(
                task="Isolate this run",
                item_id="item-1",
                prd_items=[{"id": "item-1", "title": "Item"}],
                working_directory=target,
            )
            completed = subprocess.CompletedProcess(
                args=adapter.command,
                returncode=0,
                stdout="<promise>ITEM_BUILT</promise>\n",
                stderr="",
            )

            with patch(
                "workflow.adapters._run_subprocess", return_value=completed
            ) as run:
                adapter.run(request)

            command = run.call_args.args[0]
            self.assertIn("--run-dir", command)
            self.assertEqual(
                Path(command[command.index("--run-dir") + 1]),
                target / ".shanks" / "ralph",
            )
            self.assertTrue((target / ".shanks" / "ralph" / "prd.json").exists())

    def test_ralph_adapter_requires_the_item_built_signal(self) -> None:
        adapter = RalphAdapter(
            Path("/tmp/target-project"),
            base_directory=Path("/tmp/agent-engine"),
        )
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout="work completed without the graph signal\n",
            stderr="",
        )

        with patch("workflow.adapters._run_subprocess", return_value=completed):
            result = adapter.run(AgentRequest(task="Build one item"))

        self.assertEqual(result.status, "failed")
        self.assertIn("ITEM_BUILT", result.error)

    def test_ralph_adapter_syncs_only_the_changed_prd_item(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            ralph_directory = root / "scripts" / "ralph"
            ralph_directory.mkdir(parents=True)
            prd_file = ralph_directory / "prd.json"
            prd_file.write_text(
                json.dumps(
                    {
                        "project": "Example",
                        "userStories": [
                            {
                                "id": "item-1",
                                "title": "First",
                                "description": "Old requirement",
                                "passes": True,
                                "validation": False,
                                "acceptanceCriteria": ["Keep this"],
                            },
                            {
                                "id": "item-2",
                                "title": "Second",
                                "description": "Unchanged requirement",
                                "passes": False,
                                "validation": False,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            adapter = RalphAdapter(root, base_directory=root)
            request = AgentRequest(
                task="Example",
                item_id="item-1",
                item_description="New debugger requirement",
                acceptance_criteria=["Debugger guidance is covered."],
                validation_command=".venv/bin/python -m unittest tests.test_graph",
                prd_items=[
                    {
                        "id": "item-1",
                        "title": "First",
                        "description": "New debugger requirement",
                        "acceptance_criteria": ["Debugger guidance is covered."],
                        "validation_command": ".venv/bin/python -m unittest tests.test_graph",
                        "passes": True,
                        "validation": False,
                    },
                    {
                        "id": "item-2",
                        "title": "Second",
                        "description": "Unchanged requirement",
                        "passes": False,
                        "validation": False,
                    },
                ],
            )
            completed = subprocess.CompletedProcess(
                args=adapter.command,
                returncode=0,
                stdout="<promise>ITEM_BUILT</promise>\n",
                stderr="",
            )

            with patch(
                "workflow.adapters._run_subprocess",
                return_value=completed,
            ):
                result = adapter.run(request)

            payload = json.loads(prd_file.read_text(encoding="utf-8"))
            self.assertEqual(result.status, "completed")
            self.assertEqual(
                payload["userStories"][0]["description"],
                "New debugger requirement",
            )
            self.assertEqual(
                payload["userStories"][0]["acceptanceCriteria"],
                ["Debugger guidance is covered."],
            )
            self.assertEqual(
                payload["userStories"][0]["validationCommand"],
                ".venv/bin/python -m unittest tests.test_graph",
            )
            self.assertNotIn("acceptance_criteria", payload["userStories"][0])
            self.assertNotIn("validation_command", payload["userStories"][0])
            self.assertEqual(
                payload["userStories"][1]["description"],
                "Unchanged requirement",
            )
