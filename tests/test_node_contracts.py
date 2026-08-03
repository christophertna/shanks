import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.adapters import (
    CLAUDE_OPUS_48_EFFORT,
    CLAUDE_OPUS_48_MODEL,
    CheapCriticAdapter,
    ClaudeOpus48CriticAdapter,
    GPT56LunaCriticAdapter,
    RalphAdapter,
    StubAgentAdapter,
)
from workflow.adapters import SubprocessAgentAdapter
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import (
    claude_opus_4_8_dependencies,
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
            Path("/tmp/shanks"),
            tool="codex",
            skill_name="ponytail",
            max_iterations=3,
        )

        self.assertEqual(adapter.model_name, "ralph:codex")
        self.assertEqual(adapter.command[-3:], ("--skill", "ponytail", "3"))
