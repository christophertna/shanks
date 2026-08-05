# Shanks

Shanks is a small LangGraph-based workflow project for running Ralph-style agent tasks.
It turns a task plan into a repeatable workflow that can plan work, build or revise it,
ask a critic for feedback, validate the result, and move on to the next item.
Runs begin with an intake choice: learn the codebase or implement a feature.
The learn branch records reusable codebase context and returns to intake; the
implement branch continues through planning, building, review, validation, and
the next unfinished item.

The repository also includes a lightweight Mermaid viewer for seeing the main workflow
and its recovery paths.

## Main pieces

- `workflow/` contains the shared state, contracts, adapters, and workflow nodes.
- `graph.py` assembles the executable LangGraph workflow.
- `serve_graph.py` serves the live graph viewer.
- `scripts/ralph/` contains Ralph-oriented supporting instructions and examples.
- `skills/` contains shared skill sources; `.agents/skills/` and `.claude/skills/`
  expose project-scoped Codex and Claude entrypoints.
- `.github/workflows/tests.yml` runs the unittest suite on pushes and pull requests.
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

Workflow checkpoints are stored in `.shanks/checkpoints.sqlite`, so the viewer
can inspect runs started by another process. Set `SHANKS_CHECKPOINT_DB` in both
processes to use a different shared database path.

Checkpoint state carries a `state_schema_version`. Older unversioned checkpoints
are treated as v0 and migrated to the current schema when loaded; new checkpoints
are written with the current version. Checkpoints from a newer unsupported version
fail clearly instead of being interpreted incorrectly.

The viewer's Live execution panel accepts the workflow's `thread_id` and polls
the current node, PRD item, attempt count, last error, model, and checkpoint
history. Use the same thread ID when starting the workflow and inspecting it.

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

Critic feedback is included in the next builder attempt when a review rejects
an item. A failed build follows the explicit failed-build terminal route and
does not proceed to critic or validation.

When validation fails, the read-only debugger analyzes the failure, records its
root cause and repair instructions in the current PRD item, then planning sends
the enriched requirement to the builder.

In each PRD item, `passes` means Ralph finished the build and `validation`
means the graph’s authoritative test gate passed.

Validated implement runs pause for human approval before committing each item.
After the last item, they pause again before pushing the branch and opening a
pull request. Resume an approval interrupt with `Command(resume="approve")` or
end the run without the side effect with `Command(resume="reject")`.

Security guardrails keep subprocesses on approved executables and configured
directories, resolve GitHub file paths through the project root (including
symlinks), redact common credentials from command output and PR text, and limit
the GitHub adapter to the required read/commit/push/PR commands. The repo-local
`hooks/deny-dangerous.sh` hook adds a denylist for catastrophic shell commands;
run `hooks/test-guard.sh` to check it.

Ralph records only genuinely uncertain implementation decisions reported by the
builder. They are parsed from the `RALPH_UNCERTAINTIES` output section and stored
per PRD item for later review.

For implement runs, each validated item is committed locally. After the last
item passes, the final GitHub handoff pushes the current non-`main` branch and
creates a pull request with the GitHub CLI (`gh`). Persisted commit and PR IDs
make commit and pull-request handoff safe to resume without duplicating those
side effects; authenticate `gh` before starting the run.
