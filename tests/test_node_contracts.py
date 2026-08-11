import json
import os
import subprocess
import sys
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
)
from workflow.adapters import SubprocessAgentAdapter
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import (
    claude_opus_4_8_dependencies,
    default_dependencies,
    gpt_5_6_luna_dependencies,
)
from workflow.retries import classify_failure, retry_delay, retry_on_exception


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
            "workflow.adapters.subprocess.run",
            return_value=completed,
        ) as run:
            adapter.run(AgentRequest(task="test task", timeout_seconds=2.5))

        self.assertEqual(run.call_args.kwargs["timeout"], 2.5)

    def test_agent_subprocesses_do_not_receive_github_tokens(self) -> None:
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
                    "SAFE_SETTING": "kept",
                },
                clear=True,
            ),
            patch(
                "workflow.adapters.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            adapter.run(AgentRequest(task="test task"))

        environment = run.call_args.kwargs["env"]
        self.assertNotIn("GH_TOKEN", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertEqual(environment["SAFE_SETTING"], "kept")

    def test_subprocess_adapter_rejects_unapproved_executables(self) -> None:
        adapter = SubprocessAgentAdapter(
            command=("sh", "-c", "echo unsafe"),
            model_name="unsafe-cli",
        )

        with patch("workflow.adapters.subprocess.run") as run:
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

        with patch("workflow.adapters.subprocess.run") as run:
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

        with patch("workflow.adapters.subprocess.run", return_value=completed):
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

        with patch("workflow.adapters.subprocess.run", return_value=completed) as run:
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

        with patch("workflow.adapters.subprocess.run", return_value=completed) as run:
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

        with patch("workflow.adapters.subprocess.run", return_value=completed) as run:
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
        self.assertIn("FAIL: expected request", run.call_args.kwargs["input"])
        self.assertIn("read-only", run.call_args.kwargs["input"])
        self.assertIn(
            "The handler must use the request field.", run.call_args.kwargs["input"]
        )
        self.assertIn("read-only", adapter.command)
        self.assertIn("--output-schema", adapter.command)

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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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
            patch("workflow.adapters.subprocess.run", side_effect=responses) as run,
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

        with patch("workflow.adapters.subprocess.run") as run:
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

        with patch("workflow.adapters.subprocess.run") as run:
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
            "workflow.adapters.subprocess.run",
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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
                "workflow.adapters.subprocess.run",
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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
            "workflow.adapters.subprocess.run", side_effect=closed_responses
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
            "workflow.adapters.subprocess.run", side_effect=merged_responses
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
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

        with patch("workflow.adapters.subprocess.run", return_value=completed):
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
        self.assertIn("Read", adapter.command)
        self.assertIn("--json-schema", adapter.command)

    def test_claude_opus_4_8_critic_maps_structured_output(self) -> None:
        adapter = ClaudeOpus48CriticAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=0,
            stdout='{"approved": true, "feedback": "Looks good."}',
            stderr="",
        )

        with patch("workflow.adapters.subprocess.run", return_value=completed):
            result = adapter.run(AgentRequest(task="review this"))

        self.assertEqual(result.status, "critic_audited")
        self.assertEqual(result.assigned_model, CLAUDE_OPUS_48_MODEL)
        self.assertTrue(result.approved)
        self.assertEqual(result.feedback, "Looks good.")

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

        with patch("workflow.adapters.subprocess.run", return_value=completed) as run:
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
                "workflow.adapters.subprocess.run", return_value=completed
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

        with patch("workflow.adapters.subprocess.run", return_value=completed):
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
                "workflow.adapters.subprocess.run",
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
