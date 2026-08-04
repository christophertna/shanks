"""LangGraph workflow assembled from standardized agent nodes."""

from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from workflow.nodes import (
    NodeDependencies,
    build_error_handler,
    create_nodes,
    default_dependencies,
    route_after_building,
    route_after_commit,
    route_after_github,
    route_after_intake,
    route_after_item_router,
    route_after_planning,
    route_after_validation,
)
from workflow.state import WorkflowState


def build_graph(
    dependencies: NodeDependencies | None = None,
    *,
    checkpointer=None,
    tool: Literal["claude", "codex"] = "codex",
):
    """Build the workflow with optional adapters or a Claude/Codex choice."""

    nodes = create_nodes(
        dependencies or default_dependencies(tool=tool)
    )
    builder = StateGraph(WorkflowState)
    builder.add_node("intake", nodes["intake"])
    builder.add_node("learning", nodes["learning"])
    builder.add_node("planning", nodes["planning"])
    builder.add_node("critic_auditor", nodes["critic_auditor"])
    builder.add_node(
        "building",
        nodes["building"],
        retry_policy=RetryPolicy(),
        error_handler=build_error_handler,
    )
    builder.add_node("failed_build", nodes["failed_build"])
    # The viewer renders the validation decision node as a diamond.
    builder.add_node("validation", nodes["validation"], metadata={"kind": "decision"})
    builder.add_node("commit_item", nodes["commit_item"])
    builder.add_node("debugger", nodes["debugger"])
    builder.add_node("item_router", nodes["item_router"])
    builder.add_node("github_node", nodes["github_node"])
    builder.add_node("attempt_limit", nodes["attempt_limit"])

    builder.add_edge(START, "intake")
    builder.add_conditional_edges(
        "intake",
        route_after_intake,
        ["learning", "planning"],
    )
    builder.add_edge("learning", "intake")
    builder.add_conditional_edges(
        "planning",
        route_after_planning,
        ["building", "item_router"],
    )
    builder.add_conditional_edges(
        "building",
        route_after_building,
        ["critic_auditor", "validation", "attempt_limit", "failed_build"],
    )
    builder.add_edge("critic_auditor", "building")
    builder.add_conditional_edges(
        "validation",
        route_after_validation,
        ["debugger", "commit_item"],
    )
    builder.add_conditional_edges(
        "commit_item",
        route_after_commit,
        ["item_router", END],
    )
    builder.add_edge("debugger", "planning")
    builder.add_conditional_edges(
        "item_router",
        route_after_item_router,
        ["planning", "github_node"],
    )
    builder.add_conditional_edges(
        "github_node",
        route_after_github,
        [END],
    )
    builder.add_edge("attempt_limit", END)
    builder.add_edge("failed_build", END)

    return builder.compile(
        checkpointer=checkpointer if checkpointer is not None else InMemorySaver()
    )


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke(
        {"task": "Build a simple workflow"},
        config={"configurable": {"thread_id": "cli-demo"}},
    )
    print(result)
