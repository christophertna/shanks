"""LangGraph workflow assembled from standardized agent nodes."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from workflow.nodes import (
    NodeDependencies,
    create_nodes,
    default_dependencies,
    route_after_building,
    route_after_item_router,
    route_after_planning,
    route_after_validation,
)
from workflow.state import WorkflowState


def build_graph(
    dependencies: NodeDependencies | None = None,
):
    """Build the workflow with optional provider adapters."""

    nodes = create_nodes(dependencies or default_dependencies())
    builder = StateGraph(WorkflowState)
    builder.add_node("planning", nodes["planning"])
    builder.add_node("critic_auditor", nodes["critic_auditor"])
    builder.add_node("building", nodes["building"])
    # The viewer renders the validation decision node as a diamond.
    builder.add_node("validation", nodes["validation"], metadata={"kind": "decision"})
    builder.add_node("debugger", nodes["debugger"])
    builder.add_node("item_router", nodes["item_router"])
    builder.add_node("attempt_limit", nodes["attempt_limit"])

    builder.add_edge(START, "planning")
    builder.add_conditional_edges(
        "planning",
        route_after_planning,
        ["building", "item_router"],
    )
    builder.add_conditional_edges(
        "building",
        route_after_building,
        ["critic_auditor", "validation", "attempt_limit"],
    )
    builder.add_edge("critic_auditor", "building")
    builder.add_conditional_edges(
        "validation",
        route_after_validation,
        ["debugger", "item_router"],
    )
    builder.add_edge("debugger", "planning")
    builder.add_conditional_edges(
        "item_router",
        route_after_item_router,
        ["planning", END],
    )
    builder.add_edge("attempt_limit", END)

    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke({"task": "Build a simple workflow"})
    print(result)
