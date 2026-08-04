import json
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


class NodeContractTests(unittest.TestCase):
    def test_stub_roles_return_common_result_shape(self) -> None:
        request = AgentRequest(task="test task", item_id="item-1")

        for role in ("planner", "builder", "critic", "validator", "debugger"):
            with self.subTest(role=role):
                result = StubAgentAdapter(role, f"{role}-model").run(request)
                self.assertIsInstance(result, AgentResult)
                self.assertEqual(result.assigned_model, f"{role}-model")
                self.assertTrue(result.status)

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

    def test_local_test_adapter_maps_a_failed_suite(self) -> None:
        adapter = LocalTestAdapter(Path("/tmp/shanks"))
        completed = subprocess.CompletedProcess(
            args=adapter.command,
            returncode=1,
            stdout="FAIL: test_example",
            stderr="",
        )

        with patch("workflow.adapters.subprocess.run", return_value=completed):
            result = adapter.run(AgentRequest(task="validate this"))

        self.assertEqual(result.status, "validation_failed")
        self.assertFalse(result.validation_passed)
        self.assertEqual(result.validation_errors, ["FAIL: test_example"])

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
        self.assertIn("The handler must use the request field.", run.call_args.kwargs["input"])
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
        self.assertEqual(
            run.call_args_list[1].args[0],
            ("git", "add", "--", "workflow/new.py", "new.py"),
        )
        self.assertEqual(
            run.call_args_list[2].args[0],
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

    def test_github_adapter_pushes_then_creates_a_pr(self) -> None:
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
        self.assertEqual(
            run.call_args_list[1].args[0],
            ("git", "push", "-u", "origin", "validation-node"),
        )
        self.assertEqual(
            run.call_args_list[3].args[0][:5],
            ("gh", "pr", "create", "--base", "main"),
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
                "url",
                "--limit",
                "1",
            ),
        )

    def test_github_adapter_reports_commit_failure(self) -> None:
        adapter = GitHubAdapter(
            Path("/tmp/shanks"),
            initial_dirty_files=(),
        )
        responses = [
            subprocess.CompletedProcess(
                args=(), returncode=0, stdout="?? item.py\n", stderr=""
            ),
            subprocess.CompletedProcess(
                args=(), returncode=1, stdout="", stderr="commit failed"
            ),
        ]

        with patch("workflow.adapters.subprocess.run", side_effect=responses) as run:
            result = adapter.commit_item("item-1", "First item", ["item.py"])

        self.assertEqual(result.status, "failed")
        self.assertEqual(run.call_count, 2)

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
            stdout="fixed\n<promise>ITEM_BUILT</promise>\n",
            stderr="",
        )

        with patch("workflow.adapters.subprocess.run", return_value=completed) as run:
            adapter.run(request)

        command = run.call_args.args[0]
        self.assertEqual(command[-4:-2], ("--graph-item-id", "item-1"))
        self.assertEqual(command[-2], "--graph-instructions")
        self.assertIn("PRD requirement: Root cause: the setup is missing.", command[-1])
        self.assertIn("Leave this requirement unchanged.", command[-1])
        self.assertIn("Add the setup before rerunning tests.", command[-1])

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
                prd_items=[
                    {
                        "id": "item-1",
                        "title": "First",
                        "description": "New debugger requirement",
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
                ["Keep this"],
            )
            self.assertEqual(
                payload["userStories"][1]["description"],
                "Unchanged requirement",
            )
