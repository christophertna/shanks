from dataclasses import dataclass, field
import unittest
from unittest.mock import patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from graph import TARGETED_RETRY_POLICY
from graph import build_graph as compile_graph
from workflow.adapters import StubAgentAdapter
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import (
    NodeDependencies,
    commit_item,
    create_nodes,
    github_node,
    route_after_github,
    route_after_preflight,
    route_after_pull_request,
    select_next_item,
)
from workflow.state import cancel_run


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
    pushes: list[str] = field(default_factory=list)
    pull_requests: list[str] = field(default_factory=list)
    fail_commit: bool = False
    fail_publish: bool = False
    transient_push_failures: int = 0
    transient_pr_failures: int = 0

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

    def push_branch(self) -> AgentResult:
        self.pushes.append("branch")
        if self.transient_push_failures > 0:
            self.transient_push_failures -= 1
            return AgentResult(
                status="failed",
                assigned_model="test-github",
                error="connection reset by peer",
            )
        return AgentResult(
            status="branch_pushed",
            assigned_model="test-github",
            feedback="feature/test",
        )

    def open_pull_request(self, task: str, *, branch: str = "") -> AgentResult:
        self.pull_requests.append(task)
        if self.fail_publish:
            return AgentResult(
                status="failed",
                assigned_model="test-github",
                error="publish failed",
            )
        if self.transient_pr_failures > 0:
            self.transient_pr_failures -= 1
            return AgentResult(
                status="failed",
                assigned_model="test-github",
                error="secondary rate limit exceeded",
            )
        return AgentResult(
            status="pr_created",
            assigned_model="test-github",
            pr_url="https://github.com/example/shanks/pull/1",
            pr_state="open",
        )

    def publish_pr(self, task: str) -> AgentResult:
        """Keep the legacy test-double API covered while the graph splits handoffs."""

        pushed = self.push_branch()
        if pushed.status != "branch_pushed":
            return pushed
        return self.open_pull_request(task, branch=pushed.feedback)


@dataclass
class PreflightOnlyRepository:
    result: AgentResult
    calls: int = 0

    def preflight(self) -> AgentResult:
        self.calls += 1
        return self.result


class GraphRoutingTests(unittest.TestCase):
    def test_preflight_routes_to_intake_only_after_success(self) -> None:
        repository = PreflightOnlyRepository(
            AgentResult(status="preflight_passed", assigned_model="github")
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
            repository=repository,
        )

        result = build_graph(dependencies).invoke(
            {"task": "preflight first"},
            {"configurable": {"thread_id": "preflight-success"}},
        )

        self.assertEqual(repository.calls, 1)
        self.assertEqual(result["__interrupt__"][0].value["type"], "intake")
        self.assertEqual(
            route_after_preflight({"status": "preflight_passed"}), "intake"
        )

    def test_preflight_failure_stops_before_intake(self) -> None:
        repository = PreflightOnlyRepository(
            AgentResult(
                status="preflight_failed",
                assigned_model="github",
                error="not authenticated",
            )
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
            repository=repository,
        )

        result = build_graph(dependencies).invoke(
            {"task": "preflight first"},
            {"configurable": {"thread_id": "preflight-failure"}},
        )

        self.assertEqual(result["status"], "preflight_failed")
        self.assertNotIn("__interrupt__", result)
        self.assertEqual(route_after_preflight(result), "__end__")

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
                "prd_items": [{"id": "item-1", "title": "First item", "passes": False}],
            },
            {"configurable": {"thread_id": "default-completes"}},
        )

        self.assertTrue(result["critic_passed"])
        self.assertTrue(result["validation_passed"])
        self.assertTrue(result["prd_items"][0]["passes"])
        self.assertEqual(result["current_item_id"], "item-1")

    def test_item_metadata_reaches_planning_and_validation(self) -> None:
        planner = SequenceAdapter(
            "planner",
            [
                AgentResult(
                    status="planned",
                    assigned_model="planner",
                    plan=["Build the item"],
                    builder_instructions="Implement the item.",
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
            planner=planner,
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=validator,
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        build_graph(dependencies).invoke(
            {
                "task": "Build the item",
                "workflow_mode": "implement",
                "prd_items": [
                    {
                        "id": "item-1",
                        "title": "First item",
                        "description": "Build the item.",
                        "acceptanceCriteria": ["The item is covered."],
                        "validationCommand": ".venv/bin/python -m unittest tests.test_graph",
                        "passes": False,
                        "validation": False,
                    }
                ],
            },
            {"configurable": {"thread_id": "item-metadata"}},
        )

        for request in (planner.requests[0], validator.requests[0]):
            self.assertEqual(request.acceptance_criteria, ["The item is covered."])
            self.assertEqual(
                request.validation_command,
                ".venv/bin/python -m unittest tests.test_graph",
            )

    def test_run_manifest_records_prompts_models_and_pull_request_id(self) -> None:
        repository = RecordingRepository()

        result = invoke_with_approvals(
            build_graph(_stub_dependencies(repository)),
            _initial_state(),
            {"configurable": {"thread_id": "run-manifest"}},
        )

        planning_event = next(
            event for event in result["run_manifest"] if event["node"] == "planning"
        )
        github_event = next(
            event for event in result["run_manifest"] if event["node"] == "github_node"
        )
        pull_request_event = next(
            event
            for event in result["run_manifest"]
            if event["node"] == "pull_request_node"
        )
        self.assertEqual(planning_event["type"], "agent")
        self.assertEqual(planning_event["model"], "planner")
        self.assertEqual(planning_event["prompt"]["item_id"], "item-1")
        self.assertEqual(github_event["status"], "branch_pushed")
        self.assertEqual(pull_request_event["pull_request_id"], "1")
        self.assertEqual(pull_request_event["pull_request_state"], "open")
        self.assertEqual(result["pr_state"], "open")

    def test_cancel_run_stops_before_builder(self) -> None:
        builder = SequenceAdapter(
            "builder",
            [AgentResult(status="built", assigned_model="builder")],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            {**_initial_state(), **cancel_run("Operator stopped this run.")},
            {"configurable": {"thread_id": "cancel-run"}},
        )

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["last_error"], "Operator stopped this run.")
        self.assertEqual(builder.calls, 0)

    def test_checkpoint_cancellation_resumes_to_terminal_stop(self) -> None:
        graph = build_graph(_stub_dependencies())
        config = {"configurable": {"thread_id": "checkpoint-cancel"}}

        paused = graph.invoke({"task": "Stop this run"}, config)
        self.assertIn("__interrupt__", paused)

        graph.update_state(config, cancel_run("User requested a stop."))
        result = graph.invoke(None, config)

        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["last_error"], "User requested a stop.")

    def test_runtime_budget_stops_before_external_adapters(self) -> None:
        builder = SequenceAdapter(
            "builder",
            [AgentResult(status="built", assigned_model="builder")],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        with patch("workflow.nodes.time.time", return_value=100.0):
            result = build_graph(dependencies).invoke(
                {
                    **_initial_state(),
                    "run_started_at": 1.0,
                    "max_runtime_seconds": 10.0,
                },
                {"configurable": {"thread_id": "runtime-budget"}},
            )

        self.assertEqual(result["status"], "budget_exceeded")
        self.assertIn("Maximum runtime exceeded", result["last_error"])
        self.assertEqual(builder.calls, 0)

    def test_token_and_cost_budgets_accumulate_adapter_usage(self) -> None:
        builder = SequenceAdapter(
            "builder",
            [
                AgentResult(
                    status="built",
                    assigned_model="builder",
                    input_tokens=3,
                    output_tokens=4,
                    cost_usd=0.25,
                )
            ],
        )
        critic = SequenceAdapter(
            "critic",
            [AgentResult(status="critic_audited", assigned_model="critic")],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=critic,
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            {
                **_initial_state(),
                "max_tokens": 6,
                "max_cost_usd": 0.20,
            },
            {"configurable": {"thread_id": "usage-budget"}},
        )

        self.assertEqual(result["status"], "budget_exceeded")
        self.assertEqual(result["total_tokens"], 7)
        self.assertEqual(result["total_cost_usd"], 0.25)
        self.assertEqual(critic.calls, 0)

    def test_total_attempt_budget_stops_before_critic(self) -> None:
        builder = SequenceAdapter(
            "builder",
            [AgentResult(status="built", assigned_model="builder")],
        )
        critic = SequenceAdapter(
            "critic",
            [AgentResult(status="critic_audited", assigned_model="critic")],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=critic,
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            {**_initial_state(), "max_total_attempts": 1},
            {"configurable": {"thread_id": "total-attempt-budget"}},
        )

        self.assertEqual(result["status"], "budget_exceeded")
        self.assertEqual(result["total_attempts"], 1)
        self.assertEqual(critic.calls, 0)

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
        self.assertEqual(result["failure_class"], "permanent")
        self.assertEqual(result["retry_counts"], {"building": 1})
        self.assertEqual(builder.calls, 1)
        self.assertEqual(critic.calls, 0)
        self.assertEqual(validator.calls, 0)

    def test_transient_build_failure_retries_build_with_backoff(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [
                AgentResult(
                    status="failed",
                    assigned_model="ralph",
                    error="connection reset by peer",
                ),
                AgentResult(status="built", assigned_model="ralph"),
            ],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        with patch("workflow.nodes.time.sleep") as sleep:
            result = build_graph(dependencies).invoke(
                _initial_state(),
                {"configurable": {"thread_id": "transient-build-retry"}},
            )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(builder.calls, 2)
        self.assertEqual(result["retry_counts"], {"building": 1})
        sleep.assert_called_once_with(0.5)
        self.assertEqual(
            [
                event["type"]
                for event in result["run_manifest"]
                if event.get("type") == "retry"
            ],
            ["retry"],
        )
        self.assertEqual(
            [
                event["failure_class"]
                for event in result["run_manifest"]
                if event.get("type") == "agent"
                and event.get("node") == "building"
                and "failure_class" in event
            ],
            ["transient"],
        )

    def test_transient_critic_failure_retries_critic_without_rebuilding(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [AgentResult(status="built", assigned_model="ralph")],
        )
        critic = SequenceAdapter(
            "critic",
            [
                AgentResult(
                    status="failed",
                    assigned_model="critic",
                    error="service unavailable",
                ),
                AgentResult(
                    status="critic_audited",
                    assigned_model="critic",
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

        with patch("workflow.nodes.time.sleep") as sleep:
            result = build_graph(dependencies).invoke(
                _initial_state(),
                {"configurable": {"thread_id": "transient-critic-retry"}},
            )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(builder.calls, 1)
        self.assertEqual(critic.calls, 2)
        self.assertEqual(result["retry_counts"], {"critic_auditor": 1})
        sleep.assert_called_once_with(0.5)

    def test_transient_validation_failure_retries_validation_without_debugging(
        self,
    ) -> None:
        validator = SequenceAdapter(
            "validator",
            [
                AgentResult(
                    status="failed",
                    assigned_model="validator",
                    error="timed out while running tests",
                    validation_passed=False,
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
            [AgentResult(status="debugged", assigned_model="debugger")],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=validator,
            debugger=debugger,
        )

        with patch("workflow.nodes.time.sleep") as sleep:
            result = build_graph(dependencies).invoke(
                _initial_state(),
                {"configurable": {"thread_id": "transient-validation-retry"}},
            )

        self.assertEqual(result["status"], "complete")
        self.assertEqual(validator.calls, 2)
        self.assertEqual(debugger.calls, 0)
        self.assertEqual(result["retry_counts"], {"validation": 1})
        sleep.assert_called_once_with(0.5)

    def test_builder_uncertainties_are_stored_by_item(self) -> None:
        builder = SequenceAdapter(
            "ralph",
            [
                AgentResult(
                    status="built",
                    assigned_model="ralph",
                    uncertainties=["Kept the fallback behavior."],
                )
            ],
        )
        dependencies = NodeDependencies(
            planner=StubAgentAdapter("planner", "planner"),
            builder=builder,
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "uncertainties-by-item"}},
        )

        self.assertEqual(
            result["uncertainties_by_item"],
            {"item-1": ["Kept the fallback behavior."]},
        )

    def test_every_create_node_has_the_targeted_retry_policy(self) -> None:
        graph = build_graph(_stub_dependencies())
        for name in create_nodes().keys():
            with self.subTest(node=name):
                self.assertEqual(
                    graph.nodes[name].retry_policy, (TARGETED_RETRY_POLICY,)
                )

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

    def test_permanent_planning_exception_uses_failure_handler(self) -> None:
        class FailingPlanner:
            model_name = "failing-planner"

            def run(self, request: AgentRequest) -> AgentResult:
                raise ValueError("invalid planner response")

        dependencies = NodeDependencies(
            planner=FailingPlanner(),
            builder=StubAgentAdapter("builder", "builder"),
            critic=StubAgentAdapter("critic", "critic"),
            validator=StubAgentAdapter("validator", "validator"),
            debugger=StubAgentAdapter("debugger", "debugger"),
        )

        result = build_graph(dependencies).invoke(
            _initial_state(),
            {"configurable": {"thread_id": "planning-exception"}},
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failure_class"], "permanent")
        self.assertEqual(result["failure_node"], "planning")
        self.assertEqual(result["last_error"], "invalid planner response")

    def test_graph_advances_through_all_incomplete_items(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))
        config = {"configurable": {"thread_id": "advances-items"}}
        result = invoke_with_approvals(
            graph,
            {
                "task": "Build the workflow",
                "workflow_mode": "implement",
                "prd_items": [
                    {"id": "item-1", "title": "First item", "passes": False},
                    {"id": "item-2", "title": "Second item", "passes": False},
                ],
            },
            config,
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

        result = invoke_with_approvals(
            build_graph(dependencies),
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

        result = invoke_with_approvals(
            build_graph(_stub_dependencies(repository)),
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

        result = invoke_with_approvals(
            build_graph(_stub_dependencies(repository, debugger=debugger)),
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

    def test_transient_learning_failure_retries_learning_with_backoff(self) -> None:
        planner = SequenceAdapter(
            "planner",
            [
                AgentResult(
                    status="failed",
                    assigned_model="planner",
                    error="temporarily unavailable",
                ),
                AgentResult(
                    status="learned",
                    assigned_model="planner",
                    feedback="The workflow uses LangGraph.",
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
        config = {"configurable": {"thread_id": "transient-learning-retry"}}

        graph.invoke({"task": "Understand this codebase"}, config)
        with patch("workflow.nodes.time.sleep") as sleep:
            result = graph.invoke(Command(resume="learn"), config)

        self.assertEqual(planner.calls, 2)
        self.assertEqual(result["status"], "learned")
        self.assertEqual(result["retry_counts"], {"learning": 1})
        sleep.assert_called_once_with(0.5)

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
        self.assertEqual(
            route_after_github({"status": "branch_pushed"}),
            "pull_request_node",
        )
        self.assertEqual(
            route_after_github({"status": "retry_scheduled"}), "retry_backoff"
        )

    def test_pull_request_failure_routes_to_end_or_retry(self) -> None:
        self.assertEqual(route_after_pull_request({"status": "failed"}), "__end__")
        self.assertEqual(route_after_pull_request({"status": "pr_created"}), "__end__")
        self.assertEqual(
            route_after_pull_request({"status": "retry_scheduled"}),
            "retry_backoff",
        )

    def test_transient_push_failure_retries_github_node_with_backoff(self) -> None:
        repository = RecordingRepository(transient_push_failures=1)

        with patch("workflow.nodes.time.sleep") as sleep:
            result = invoke_with_approvals(
                build_graph(_stub_dependencies(repository)),
                _initial_state(),
                {"configurable": {"thread_id": "transient-push-retry"}},
            )

        self.assertEqual(result["status"], "pr_created")
        self.assertEqual(len(repository.pushes), 2)
        self.assertEqual(len(repository.pull_requests), 1)
        self.assertEqual(result["retry_counts"]["github_node"], 1)
        sleep.assert_called_once_with(0.5)

    def test_transient_pr_failure_retries_pull_request_node_with_backoff(
        self,
    ) -> None:
        repository = RecordingRepository(transient_pr_failures=1)

        with patch("workflow.nodes.time.sleep") as sleep:
            result = invoke_with_approvals(
                build_graph(_stub_dependencies(repository)),
                _initial_state(),
                {"configurable": {"thread_id": "transient-pr-retry"}},
            )

        self.assertEqual(result["status"], "pr_created")
        self.assertEqual(len(repository.pushes), 1)
        self.assertEqual(len(repository.pull_requests), 2)
        self.assertEqual(result["retry_counts"]["pull_request_node"], 1)
        sleep.assert_called_once_with(0.5)

    def test_commit_requires_approval_before_side_effect(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))
        config = {"configurable": {"thread_id": "commit-approval"}}

        with patch.dict("os.environ", {"SHANKS_MODE": "runtime"}):
            paused = graph.invoke(_initial_state(), config)
            approval = paused["__interrupt__"][0].value
            self.assertEqual(approval["type"], "approval")
            self.assertIn("not in development mode", approval["message"])
            self.assertEqual(approval["action"], "commit")
            self.assertEqual(repository.commits, [])

            paused = graph.invoke(Command(resume="approve"), config)

            self.assertEqual(repository.commits, ["item-1"])
            self.assertEqual(
                paused["__interrupt__"][0].value["action"],
                "push",
            )
            self.assertEqual(
                paused["__interrupt__"][0].value["operations"],
                ["push"],
            )

            paused = graph.invoke(Command(resume="approve"), config)
            self.assertEqual(
                paused["__interrupt__"][0].value["action"],
                "open_pull_request",
            )
            self.assertEqual(
                paused["__interrupt__"][0].value["operations"],
                ["open_pull_request"],
            )

            result = graph.invoke(Command(resume="approve"), config)

        self.assertEqual(result["status"], "pr_created")

    def test_development_mode_still_requires_side_effect_approvals(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))
        config = {"configurable": {"thread_id": "development-mode"}}

        with patch.dict("os.environ", {"SHANKS_MODE": "development"}):
            paused = graph.invoke(_initial_state(), config)
            self.assertIn(
                "Development mode is enabled",
                paused["__interrupt__"][0].value["message"],
            )
            self.assertEqual(paused["__interrupt__"][0].value["action"], "commit")

            paused = graph.invoke(Command(resume="approve"), config)
            self.assertEqual(paused["__interrupt__"][0].value["action"], "push")

            paused = graph.invoke(Command(resume="approve"), config)
            self.assertEqual(
                paused["__interrupt__"][0].value["action"],
                "open_pull_request",
            )

            result = graph.invoke(Command(resume="approve"), config)

        self.assertNotIn("__interrupt__", result)
        self.assertEqual(repository.commits, ["item-1"])
        self.assertEqual(repository.pull_requests, ["Build the workflow"])
        self.assertEqual(result["status"], "pr_created")

    def test_dry_run_previews_delivery_without_repository_side_effects(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))

        with patch.dict("os.environ", {"SHANKS_MODE": "dry-run"}):
            result = graph.invoke(
                _initial_state(),
                {"configurable": {"thread_id": "dry-run"}},
            )

        self.assertNotIn("__interrupt__", result)
        self.assertEqual(result["status"], "pull_request_preview")
        self.assertEqual(repository.commits, [])
        self.assertEqual(repository.pushes, [])
        self.assertEqual(repository.pull_requests, [])
        preview_events = [
            event
            for event in result["run_manifest"]
            if event.get("status", "").endswith("_preview")
        ]
        self.assertEqual(
            [event["status"] for event in preview_events],
            ["commit_preview", "branch_push_preview", "pull_request_preview"],
        )
        self.assertTrue(
            any(
                command[:2] == ["git", "commit"]
                for command in preview_events[0]["commands"]
            )
        )
        self.assertTrue(
            any(
                command[:3] == ["git", "push", "-u"]
                for command in preview_events[1]["commands"]
            )
        )
        self.assertTrue(
            any(
                command[:2] == ["gh", "pr"] for command in preview_events[2]["commands"]
            )
        )

    def test_rejected_commit_ends_without_commit_or_pull_request(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))
        config = {"configurable": {"thread_id": "commit-rejection"}}

        with patch.dict("os.environ", {"SHANKS_MODE": "runtime"}):
            result = graph.invoke(_initial_state(), config)
            self.assertEqual(result["__interrupt__"][0].value["action"], "commit")
            result = graph.invoke(Command(resume="reject"), config)

        self.assertEqual(result["status"], "approval_denied")
        self.assertEqual(repository.commits, [])
        self.assertEqual(repository.pull_requests, [])

    def test_rejected_publish_ends_without_push_or_pull_request(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))
        config = {"configurable": {"thread_id": "publish-rejection"}}

        with patch.dict("os.environ", {"SHANKS_MODE": "runtime"}):
            result = graph.invoke(
                {
                    "task": "Already complete",
                    "workflow_mode": "implement",
                    "prd_items": [{"id": "done", "passes": True}],
                },
                config,
            )
            self.assertEqual(
                result["__interrupt__"][0].value["operations"],
                ["push"],
            )

            result = graph.invoke(Command(resume="reject"), config)

        self.assertEqual(result["status"], "approval_denied")
        self.assertEqual(repository.pushes, [])
        self.assertEqual(repository.pull_requests, [])

    def test_rejected_pull_request_ends_after_approved_push(self) -> None:
        repository = RecordingRepository()
        graph = build_graph(_stub_dependencies(repository))
        config = {"configurable": {"thread_id": "pull-request-rejection"}}

        with patch.dict("os.environ", {"SHANKS_MODE": "runtime"}):
            result = graph.invoke(
                {
                    "task": "Already complete",
                    "workflow_mode": "implement",
                    "prd_items": [{"id": "done", "passes": True}],
                },
                config,
            )
            result = graph.invoke(Command(resume="approve"), config)
            self.assertEqual(
                result["__interrupt__"][0].value["action"],
                "open_pull_request",
            )
            result = graph.invoke(Command(resume="reject"), config)

        self.assertEqual(result["status"], "approval_denied")
        self.assertEqual(repository.pushes, ["branch"])
        self.assertEqual(repository.pull_requests, [])


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


def invoke_with_approvals(graph, input_state, config):
    result = graph.invoke(input_state, config)
    while "__interrupt__" in result:
        result = graph.invoke(Command(resume="approve"), config)
    return result


if __name__ == "__main__":
    unittest.main()
