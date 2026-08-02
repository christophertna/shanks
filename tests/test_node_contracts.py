import unittest
import sys

from workflow.adapters import CheapCriticAdapter, StubAgentAdapter
from workflow.adapters import SubprocessAgentAdapter
from workflow.contracts import AgentRequest, AgentResult


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
