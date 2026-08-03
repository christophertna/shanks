# Shanks

Shanks is a small LangGraph-based workflow project for running Ralph-style agent tasks.
It turns a task plan into a repeatable workflow that can plan work, build or revise it,
ask a critic for feedback, validate the result, and move on to the next item.

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
