# Shanks

Shanks is a small LangGraph-based workflow project for running Ralph-style agent tasks.
It turns a task plan into a repeatable workflow that can plan work, build or revise it,
ask a critic for feedback, validate the result, and move on to the next item.
Runs begin with an intake choice: learn the codebase or implement a feature.

The repository also includes a lightweight Mermaid viewer for seeing the main workflow
and its recovery paths.

## Main pieces

- `workflow/` contains the shared state, contracts, adapters, and workflow nodes.
- `graph.py` assembles the executable LangGraph workflow.
- `serve_graph.py` serves the live graph viewer.
- `scripts/ralph/` contains Ralph-oriented supporting instructions and examples.
- `tests/` covers graph routing, node contracts, and viewer output.

## Quick start

Run the tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

Start the graph viewer:

```bash
.venv/bin/python serve_graph.py
```

Then open `http://127.0.0.1:8765/graph.html`.

## Interactive workflow

The first graph invocation pauses at intake. Resume the same thread with the
user's label:

```python
from langgraph.types import Command

from graph import build_graph

graph = build_graph(tool="codex")  # use "claude" for the Claude workflow
config = {"configurable": {"thread_id": "session-1"}}
graph.invoke({"task": "Add a feature"}, config=config)
result = graph.invoke(Command(resume="implement"), config=config)
```

Use `"learn"` to run the documentation branch; it returns to intake afterward.
Choose `tool="codex"` or `tool="claude"` when building the graph to use that
CLI throughout the agent workflow.

When validation fails, the read-only debugger analyzes the failure, records its
root cause and repair instructions in the current PRD item, then planning sends
the enriched requirement to the builder.

In each PRD item, `passes` means Ralph finished the build and `validation`
means the graph’s authoritative test gate passed.

For implement runs, each validated item is committed locally. After the last
item passes, the final GitHub handoff pushes the current non-`main` branch and
creates a pull request with the GitHub CLI (`gh`); authenticate `gh` before
starting the run.
