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


def debugger(state: WorkflowState) -> WorkflowState:
    """Inspect a failed validation and prepare the workflow for replanning."""

    return {
        "status": "debugged",
    }


def route_after_validation(
    state: WorkflowState,
) -> Literal["debugger", "__end__"]:
    """Route successful work to the end and failures through debugging."""

    return "__end__" if state["validation_passed"] else "debugger"


def build_graph():
    """Build and compile the starter workflow."""

    builder = StateGraph(WorkflowState)
    builder.add_node("planning", planning)
    builder.add_node("building", building)
    builder.add_node("debugger", debugger)
    # The viewer renders the validation decision node as a diamond.
    builder.add_node("validation", validation, metadata={"kind": "decision"})

    builder.add_edge(START, "planning")
    builder.add_edge("planning", "building")
    builder.add_edge("building", "validation")
    builder.add_conditional_edges(
        "validation",
        route_after_validation,
        ["debugger", END],
    )
    builder.add_edge("debugger", "planning")

    return builder.compile()


if __name__ == "__main__":
    graph = build_graph()
    result = graph.invoke({"task": "Build a simple workflow"})
    print(result)
