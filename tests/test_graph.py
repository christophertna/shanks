import unittest
from dataclasses import dataclass, field

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graph import build_graph as compile_graph
from workflow.adapters import StubAgentAdapter
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import (
    NodeDependencies,
    commit_item,
    github_node,
    route_after_github,
    select_next_item,
)


def build_graph(*args, **kwargs):
    """Keep graph tests isolated from the shared production checkpoint store."""

    kwargs.setdefault("checkpointer", InMemorySaver())
    return compile_graph(*args, **kwargs)


@dataclass
class SequenceAdapter:
    model_name: str
    results: list[AgentResult]
    calls: int = field(default=0, init=False)
    requests: list[AgentRequest] = field(default_factory=list, init=False)

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        result = self.results[min(self.calls, len(self.results) - 1)]
        self.calls += 1
        return result


@dataclass
class RecordingRepository:
    commits: list[str] = field(default_factory=list)
    pull_requests: list[str] = field(default_factory=list)
    fail_commit: bool = False
    fail_publish: bool = False

    def commit_item(
        self,
        item_id: str,
        item_title: str,
        files_touched: list[str],
    ) -> AgentResult:
        self.commits.append(item_id)
        if self.fail_commit:
            return AgentResult(
                status="failed",
                assigned_model="test-github",
                error="commit failed",
            )
        return AgentResult(
            status="committed",
            assigned_model="test-github",
            files_touched=files_touched,
            commit_sha=f"sha-{item_id}",
        )

    def publish_pr(self, task: str) -> AgentResult:
        self.pull_requests.append(task)
        if self.fail_publish:
            return AgentResult(
                status="failed",
                assigned_model="test-github",
                error="publish failed",
            )
        return AgentResult(
            status="pr_created",
            assigned_model="test-github",
            pr_url="https://github.com/example/shanks/pull/1",
        )


class GraphRoutingTests(unittest.TestCase):
    def test_commit_sha_is_a_resume_guard(self) -> None:
        repository = RecordingRepository()
        dependencies = _stub_dependencies(repository)

        result = commit_item(
            {
                "current_item_id": "item-1",
                "current_item_title": "First item",
                "commit_sha": "sha-item-1",
            },
            dependencies,
        )

        self.assertEqual(result["status"], "committed")
        self.assertEqual(result["commit_sha"], "sha-item-1")
        self.assertEqual(repository.commits, [])

    def test_pr_url_is_a_resume_guard(self) -> None:
        repository = RecordingRepository()

        result = github_node(
            {"pr_url": "https://github.com/example/shanks/pull/1"},
            _stub_dependencies(repository),
        )

        self.assertEqual(result["status"], "pr_created")
        self.assertEqual(result["pr_url"], "https://github.com/example/shanks/pull/1")
        self.assertEqual(repository.pull_requests, [])

    def test_default_graph_completes_an_item(self) -> None:
        result = build_graph(_stub_dependencies()).invoke(
            {
                "task": "Build a simple workflow",
                "workflow_mode": "implement",
                "prd_items": [
                    {"id": "item-1", "title": "First item", "passes": False}
                ],
            },
            {"configurable": {"thread_id": "default-completes"}},
        )

        self.assertTrue(result["critic_passed"])
        self.assertTrue(result["validation_passed"])
        self.assertTrue(result["prd_items"][0]["passes"])
        self.assertEqual(result["current_item_id"], "item-1")

    def test_failed_build_stops_before_critic_or_validation(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [
                AgentResult(
                    status="failed",
                    assigned_model="ralph",
                    error="build failed",
                )
            ],
        )
        critic = SequenceAdapter(
            "critic",
            [
                AgentResult(
                    status="critic_audited",
                    assigned_model="critic",
                    approved=True,
                )
            ],
        )
        validator = SequenceAdapter(
            "validator",
            [
                AgentResult(
                    status="validated",
                    assigned_model="validator",
                    validation_passed=True,
                )
            ],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=critic,
            validator=validator,
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "failed-build-result"}},
        )

        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["build_completed"])
        self.assertEqual(builder.calls, 1)
        self.assertEqual(critic.calls, 0)
        self.assertEqual(validator.calls, 0)

    def test_exhausted_build_node_error_uses_failed_build_route(self) -> None:
        class FailingBuilder:
            model_name = "failing-builder"

            def __init__(self) -> None:
                self.calls = 0

            def run(self, request: AgentRequest) -> AgentResult:
                self.calls += 1
                raise ValueError("builder exploded")

        builder = FailingBuilder()
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "failed-build-error"}},
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["last_error"], "builder exploded")
        self.assertFalse(result["build_completed"])
        self.assertEqual(builder.calls, 1)

    def test_graph_advances_through_all_incomplete_items(self) -> None:
        repository = RecordingRepository()
        result = build_graph(_stub_dependencies(repository)).invoke(
            {
                "task": "Build the workflow",
                "workflow_mode": "implement",
                "prd_items": [
                    {"id": "item-1", "title": "First item", "passes": False},
                    {"id": "item-2", "title": "Second item", "passes": False},
                ],
            },
            {"configurable": {"thread_id": "advances-items"}},
        )

        self.assertTrue(all(item["passes"] for item in result["prd_items"]))
        self.assertTrue(all(item["validation"] for item in result["prd_items"]))
        self.assertEqual(result["completed_items"], ["item-1", "item-2"])
        self.assertEqual(result["attempts_by_item"], {"item-1": 1, "item-2": 1})
        self.assertEqual(repository.commits, ["item-1", "item-2"])
        self.assertEqual(repository.pull_requests, ["Build the workflow"])
        self.assertEqual(result["pr_url"], "https://github.com/example/shanks/pull/1")

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
                "workflow_mode": "implement",
                "prd_items": [{"id": "done", "passes": True}],
            },
            {"configurable": {"thread_id": "already-complete"}},
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
            {**_initial_state(), "max_attempts": 2},
            {"configurable": {"thread_id": "attempt-limit"}},
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

        result = build_graph(dependencies).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "critic-rejection"}},
        )

        self.assertEqual(builder.calls, 2)
        self.assertEqual(critic.calls, 2)
        self.assertEqual(result["attempts_count"], 2)
        self.assertEqual(result["current_item_id"], "item-1")
        self.assertIn(
            "Critic feedback:\nNeeds a test.",
            builder.requests[1].instructions,
        )
        self.assertTrue(result["validation_passed"])

    def test_validation_failure_debugs_and_retries_same_item(self) -> None:
        repository = RecordingRepository()
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
            repository=repository,
        )

        result = build_graph(dependencies).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "validation-retry"}},
        )

        self.assertEqual(planner.calls, 2)
        self.assertEqual(debugger.calls, 1)
        self.assertEqual(validator.calls, 2)
        self.assertEqual(result["current_item_id"], "item-1")
        self.assertEqual(result["root_cause"], "Missing setup.")
        self.assertEqual(
            debugger.requests[0].instructions,
            "Validation failure:\ntest failed",
        )
        self.assertIn("Add the missing setup.", planner.requests[1].instructions)
        self.assertEqual(planner.requests[1].context, "Missing setup.")
        self.assertIn(
            "Root cause: Missing setup.",
            result["prd_items"][0]["description"],
        )
        self.assertIn(
            "Repair instructions: Add the missing setup.",
            result["prd_items"][0]["description"],
        )
        self.assertEqual(
            planner.requests[1].item_description,
            result["prd_items"][0]["description"],
        )
        self.assertIn(
            "Apply the debugger instructions.",
            builder.requests[1].instructions,
        )
        self.assertEqual(
            builder.requests[1].item_description,
            result["prd_items"][0]["description"],
        )
        self.assertTrue(result["prd_items"][0]["passes"])
        self.assertTrue(result["prd_items"][0]["validation"])
        self.assertEqual(repository.commits, ["item-1"])
        self.assertEqual(repository.pull_requests, ["Build the workflow"])
        self.assertIn("/grill-with-docs", planner.requests[0].instructions)

    def test_failed_item_commit_stops_before_the_pull_request(self) -> None:
        repository = RecordingRepository(fail_commit=True)

        result = build_graph(_stub_dependencies(repository)).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "commit-failure"}},
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(repository.commits, ["item-1"])
        self.assertEqual(repository.pull_requests, [])

    def test_failed_github_handoff_stops_without_debugging_code(self) -> None:
        repository = RecordingRepository(fail_publish=True)
        debugger = SequenceAdapter(
            "debugger",
            [AgentResult(status="debugged", assigned_model="debugger")],
        )

        result = build_graph(
            _stub_dependencies(repository, debugger=debugger)
        ).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "github-failure"}},
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(repository.commits, ["item-1"])
        self.assertEqual(repository.pull_requests, ["Build the workflow"])
        self.assertEqual(debugger.calls, 0)

    def test_intake_learn_returns_to_the_same_question(self) -> None:
        graph = build_graph(_stub_dependencies())
        config = {"configurable": {"thread_id": "learn-then-choose"}}

        paused = graph.invoke({"task": "Understand this codebase"}, config)

        self.assertEqual(paused["__interrupt__"][0].value["type"], "intake")
        learned = graph.invoke(Command(resume="learn"), config)

        self.assertEqual(learned["status"], "learned")
        self.assertIsNone(learned["workflow_mode"])
        self.assertEqual(learned["__interrupt__"][0].value["type"], "intake")

    def test_intake_implement_enters_the_existing_workflow(self) -> None:
        graph = build_graph(_stub_dependencies())
        config = {"configurable": {"thread_id": "implement-feature"}}

        graph.invoke({"task": "Add a feature"}, config)
        result = graph.invoke(Command(resume={"choice": "implement"}), config)

        self.assertNotIn("__interrupt__", result)
        self.assertEqual(result["workflow_mode"], "implement")
        self.assertEqual(result["prd_items"][0]["title"], "Add a feature")
        self.assertTrue(result["prd_items"][0]["passes"])

    def test_implementation_reuses_learning_notes(self) -> None:
        planner = SequenceAdapter(
            "planner",
            [
                AgentResult(
                    status="learned",
                    assigned_model="planner",
                    feedback="The workflow is assembled in graph.py.",
                ),
                AgentResult(
                    status="planned",
                    assigned_model="planner",
                    plan=["Implement the requested change"],
                    builder_instructions="Build the feature.",
                ),
            ],
        )
        dependencies = NodeDependencies(
            planner=planner,
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )
        graph = build_graph(dependencies)
        config = {"configurable": {"thread_id": "learn-then-implement"}}

        graph.invoke({"task": "Understand and change the workflow"}, config)
        graph.invoke(Command(resume="learn"), config)
        graph.invoke(Command(resume="implement"), config)

        self.assertIn(
            "The workflow is assembled in graph.py.",
            planner.requests[1].instructions,
        )

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

    def test_item_selector_retries_a_built_but_unvalidated_item(self) -> None:
        selected = select_next_item(
            {
                "prd_items": [
                    {"id": "built", "passes": True, "validation": False},
                    {"id": "next", "passes": False, "validation": False},
                ]
            }
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected[0], 0)
        self.assertEqual(selected[1]["id"], "built")

    def test_github_failure_stops_without_routing_to_debugger(self) -> None:
        self.assertEqual(route_after_github({"status": "failed"}), "__end__")
        self.assertEqual(route_after_github({"status": "complete"}), "__end__")


def _initial_state() -> dict[str, object]:
    return {
        "task": "Build the workflow",
        "workflow_mode": "implement",
        "prd_items": [
            {
                "id": "item-1",
                "title": "First item",
                "passes": False,
                "validation": False,
            }
        ],
    }


def _stub_dependencies(
    repository: RecordingRepository | None = None,
    debugger: SequenceAdapter | None = None,
) -> NodeDependencies:
    return NodeDependencies(
        planner=StubAgentAdapter("planner", "planner"),
        builder=StubAgentAdapter("builder", "builder"),
        critic=StubAgentAdapter("critic", "critic"),
        validator=StubAgentAdapter("validator", "validator"),
        debugger=debugger or StubAgentAdapter("debugger", "debugger"),
        repository=repository,
    )


if __name__ == "__main__":
    unittest.main()
