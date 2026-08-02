import unittest
from dataclasses import dataclass, field

from graph import build_graph
from workflow.adapters import StubAgentAdapter
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import NodeDependencies, select_next_item


@dataclass
class SequenceAdapter:
    model_name: str
    results: list[AgentResult]
    calls: int = field(default=0, init=False)

    def run(self, request: AgentRequest) -> AgentResult:
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return result


class GraphRoutingTests(unittest.TestCase):
    def test_default_graph_completes_an_item(self) -> None:
        result = build_graph().invoke(
            {
                "task": "Build a simple workflow",
                "prd_items": [
                    {"id": "item-1", "title": "First item", "passes": False}
                ],
            }
        )

        self.assertTrue(result["critic_passed"])
        self.assertTrue(result["validation_passed"])
        self.assertTrue(result["prd_items"][0]["passes"])
        self.assertEqual(result["current_item_id"], "item-1")

    def test_graph_advances_through_all_incomplete_items(self) -> None:
        result = build_graph().invoke(
            {
                "task": "Build the workflow",
                "prd_items": [
                    {"id": "item-1", "title": "First item", "passes": False},
                    {"id": "item-2", "title": "Second item", "passes": False},
                ],
            }
        )

        self.assertTrue(all(item["passes"] for item in result["prd_items"]))
        self.assertEqual(result["completed_items"], ["item-1", "item-2"])
        self.assertEqual(result["attempts_by_item"], {"item-1": 1, "item-2": 1})

    def test_completed_items_end_without_rebuilding(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [AgentResult(status="built", assigned_model="ralph")],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            {
                "task": "Already complete",
                "prd_items": [{"id": "done", "passes": True}],
            }
        )

        self.assertEqual(builder.calls, 0)
        self.assertEqual(result["status"], "complete")

    def test_attempt_limit_stops_repeated_critic_rejection(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [
                AgentResult(status="built", assigned_model="ralph"),
                AgentResult(status="built", assigned_model="ralph"),
            ],
        )
        critic = SequenceAdapter(
            "cheap-critic-model",
            [
                AgentResult(
                    status="critic_audited",
                    assigned_model="cheap-critic-model",
                    approved=False,
                )
            ],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=critic,
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            {**_initial_state(), "max_attempts": 2}
        )

        self.assertEqual(builder.calls, 2)
        self.assertEqual(result["status"], "attempt_limit_reached")
        self.assertFalse(result.get("validation_passed", False))

    def test_critic_rejection_rebuilds_the_same_item(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [
                AgentResult(status="built", assigned_model="ralph"),
                AgentResult(status="built", assigned_model="ralph"),
            ],
        )
        critic = SequenceAdapter(
            "cheap-critic-model",
            [
                AgentResult(
                    status="critic_audited",
                    assigned_model="cheap-critic-model",
                    approved=False,
                    feedback="Needs a test.",
                ),
                AgentResult(
                    status="critic_audited",
                    assigned_model="cheap-critic-model",
                    approved=True,
                ),
            ],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=critic,
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(_initial_state())

        self.assertEqual(builder.calls, 2)
        self.assertEqual(critic.calls, 2)
        self.assertEqual(result["attempts_count"], 2)
        self.assertEqual(result["current_item_id"], "item-1")
        self.assertTrue(result["validation_passed"])

    def test_validation_failure_debugs_and_retries_same_item(self) -> None:
        planner = SequenceAdapter(
            "planner",
            [
                AgentResult(
                    status="planned",
                    assigned_model="planner",
                    plan=["initial plan"],
                    builder_instructions="Build item one.",
                ),
                AgentResult(
                    status="planned",
                    assigned_model="planner",
                    plan=["revised plan"],
                    builder_instructions="Apply the debugger instructions.",
                ),
            ],
        )
        builder = SequenceAdapter(
            "ralph",
            [
                AgentResult(status="built", assigned_model="ralph"),
                AgentResult(status="built", assigned_model="ralph"),
            ],
        )
        critic = SequenceAdapter(
            "cheap-critic-model",
            [
                AgentResult(
                    status="critic_audited",
                    assigned_model="cheap-critic-model",
                    approved=True,
                )
            ],
        )
        validator = SequenceAdapter(
            "validator",
            [
                AgentResult(
                    status="failed",
                    assigned_model="validator",
                    validation_passed=False,
                    validation_errors=["test failed"],
                ),
                AgentResult(
                    status="validated",
                    assigned_model="validator",
                    validation_passed=True,
                ),
            ],
        )
        debugger = SequenceAdapter(
            "debugger",
            [
                AgentResult(
                    status="debugged",
                    assigned_model="debugger",
                    root_cause="Missing setup.",
                    builder_instructions="Add the missing setup.",
                )
            ],
        )
        dependencies = NodeDependencies(
            planner=planner,
            builder=builder,
            critic=critic,
            validator=validator,
            debugger=debugger,
        )

        result = build_graph(dependencies).invoke(_initial_state())

        self.assertEqual(planner.calls, 2)
        self.assertEqual(debugger.calls, 1)
        self.assertEqual(validator.calls, 2)
        self.assertEqual(result["current_item_id"], "item-1")
        self.assertEqual(result["root_cause"], "Missing setup.")
        self.assertTrue(result["prd_items"][0]["passes"])

    def test_item_selector_skips_completed_items(self) -> None:
        selected = select_next_item(
            {
                "prd_items": [
                    {"id": "done", "passes": True},
                    {"id": "next", "passes": False},
                ]
            }
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected[0], 1)
        self.assertEqual(selected[1]["id"], "next")


def _initial_state() -> dict[str, object]:
    return {
        "task": "Build the workflow",
        "prd_items": [
            {"id": "item-1", "title": "First item", "passes": False}
        ],
    }


if __name__ == "__main__":
    unittest.main()
