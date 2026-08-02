# This Project, In Simple Words

This project is a small test system for using AI agents in a work flow.

It uses **LangGraph** to connect steps together.

## The main flow

```text
planning
   ↓
building
   ↓
critic_auditor
   ↓
building again
   ↓
validation
```

- `planning` picks the next unfinished PRD item.
- `building` writes or changes code.
- `critic_auditor` checks the code with a cheaper model.
- If the critic rejects it, the code goes back to `building`.
- If the critic approves it, the code goes to `validation`.
- If validation fails, `debugger` studies the problem.
- The problem then goes back to `planning` for the same PRD item.
- If validation passes, the next PRD item starts.
- When all items pass, the graph ends.

There is a limit on build attempts. This helps stop endless loops.

## Important files

### `graph.py`

Builds the LangGraph flow.

It connects the nodes and controls where each step goes next.

Only `validation` is shown as a diamond in the viewer because it is a decision step.

### `workflow/state.py`

Defines the shared state.

Think of the state as a shared notebook. It stores things like:

- The current PRD item.
- The plan.
- Files changed.
- Critic feedback.
- Validation errors.
- Debugger findings.
- Attempt counts.
- Which model was used.

### `workflow/contracts.py`

Defines the common shape for agents.

Every agent gets an `AgentRequest` and returns an `AgentResult`.

This lets different agents fit into the same graph.

### `workflow/adapters.py`

Contains the agent wrappers.

There are adapters for:

- Ralph.
- Codex.
- Claude.
- The cheap critic.
- Test-only fake agents.

The default graph uses fake agents. They do not call an outside AI service.
Real agents must be passed into `build_graph()` on purpose.

### `workflow/nodes.py`

Contains the work done by each graph node:

- Planning.
- Building.
- Critic review.
- Validation.
- Debugging.

It also selects the next unfinished PRD item and handles retries.

### `graph.html`

Shows the graph in a browser.

The nodes are white. Decision nodes are diamonds.

### `serve_graph.py`

Runs the local graph viewer.

It reads `graph.py`, creates a Mermaid diagram, and sends it to `graph.html`.
The browser updates when `graph.py` changes.

### `tests/`

Checks that the graph works.

The tests cover retries, validation failures, item progress, attempt limits, and agent adapters.

## Ralph

Ralph is the long-running coding loop in `scripts/ralph/`.

It reads a PRD file and works on one unfinished user story at a time.

Main Ralph files:

- `ralph.sh` — starts the loop.
- `prd.json.example` — example PRD format.
- `progress.txt` — work notes made by Ralph.
- `metadata.txt` — attempt and file tracking made by the runner.
- `CODEX.md` and `CLAUDE.md` — instructions for those tools.

To use Ralph, make a PRD file first:

```bash
cp scripts/ralph/prd.json.example scripts/ralph/prd.json
```

Then run one of these:

```bash
bash scripts/ralph/ralph.sh --tool codex 10
bash scripts/ralph/ralph.sh --tool claude 10
```

The number is the maximum number of loops.

## Useful commands

Run the graph:

```bash
.venv/bin/python graph.py
```

Start the graph viewer:

```bash
.venv/bin/python serve_graph.py
```

Then open:

```text
http://127.0.0.1:8765/graph.html
```

Run the tests:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Current limits

- The default agents are fake test agents.
- The graph does not yet call a real model by default.
- Ralph, Codex, and Claude adapters are ready to be connected deliberately.
- Git push and final human approval are not graph nodes yet.
