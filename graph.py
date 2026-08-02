"""Starter LangGraph workflow for graph engineering experiments."""

from typing import Literal, TypedDict

from langgraph.graph import END, START, StateGraph


class WorkflowState(TypedDict, total=False):
    """Shared state passed between workflow nodes."""

    task: str
    plan: list[str]
    files_touched: list[str]
    validation_passed: bool
    status: str


def planning(state: WorkflowState) -> WorkflowState:
    """Create a plan for the requested task."""

    return {
        "plan": [
            "Understand the task",
            "Implement the change",
            "Run validation",
        ],
        "status": "planned",
    }


def building(state: WorkflowState) -> WorkflowState:
    """Placeholder for the future coding/build node."""

    return {
        "files_touched": ["example.py"],
        "status": "built",
    }


def validation(state: WorkflowState) -> WorkflowState:
    """Placeholder for the future test/validation node."""

    return {
        "validation_passed": True,
        "status": "validated",
    }


def validation_decision(state: WorkflowState) -> WorkflowState:
    """Decide whether validation passed or the build should be retried."""

    return {
        "status": "validated" if state["validation_passed"] else "retrying",
    }


def route_after_validation(
    state: WorkflowState,
) -> Literal["building", "__end__"]:
    """Route successful work to the end and failed work back to building."""

    return "__end__" if state["validation_passed"] else "building"


def build_graph():
    """Build and compile the starter workflow."""

    builder = StateGraph(WorkflowState)
    builder.add_node("planning", planning)
    builder.add_node("building", building)
    builder.add_node("validation", validation)
    # The viewer renders nodes with kind=decision as diamonds.
    builder.add_node(
        "validation_decision",
        validation_decision,
        metadata={"kind": "decision"},
    )

    builder.add_edge(START, "planning")
    builder.add_edge("planning", "building")
    builder.add_edge("building", "validation")
    builder.add_edge("validation", "validation_decision")
    builder.add_conditional_edges(
        "validation_decision",
        route_after_validation,
        ["building", END],
    )

    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke({"task": "Build a simple workflow"})
    print(result)
