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
- `critic_auditor` checks the code with the configured critic adapter.
- If the critic rejects it, the code goes back to `building`.
- If the critic approves it, the code goes to `validation`.
- If validation fails, `debugger` studies the problem.
- The problem then goes back to `planning` for the same PRD item.
- If validation passes, the next PRD item starts.
- When all items pass, the graph ends.

There is a limit on build attempts. This helps stop endless loops.

## Critic

The `critic_auditor` node reviews the current PRD item after building. The
default graph uses a deterministic cheap critic, but real model adapters can be
selected explicitly.

### GPT-5.6 Luna

This uses a read-only Codex subagent with the `gpt-5.6-luna` model and `max`
reasoning effort:

```python
from pathlib import Path

from graph import build_graph
from workflow.nodes import gpt_5_6_luna_dependencies

graph = build_graph(gpt_5_6_luna_dependencies(Path.cwd()))
```

The subagent must be authenticated for the local `codex` CLI. It returns a
structured approval and feedback object and runs with `read-only` sandbox
access, so the critic cannot modify the repository.

### Claude Opus 4.8

To use Claude instead, select its dependency factory. It uses
`claude-opus-4-8` at `medium` effort in Claude Code plan mode with read-only
tools:

```python
from pathlib import Path

from graph import build_graph
from workflow.nodes import claude_opus_4_8_dependencies

graph = build_graph(claude_opus_4_8_dependencies(Path.cwd()))
```

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

### `graphify-out/`

This is the local map of the codebase.

Graphify is installed as a separate command-line tool. On another machine, install it with:

```bash
uv tool install graphifyy
```

Agents should query it before reading lots of source files:

```bash
graphify query "What connects graph.py to the workflow nodes?"
graphify explain "critic_auditor"
graphify path "graph.py" "workflow/nodes.py"
```

After code changes, update the map:

```bash
graphify update .
```

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
bash scripts/ralph/ralph.sh --project-dir ./target-project --tool codex 10
```

The number is the maximum number of loops. Use `--project-dir` to point Ralph
at the project whose files should be edited. The base directory still owns the
Ralph runner, prompts, PRD, progress log, metadata, skills, and graph engine;
the target directory becomes the agent's working directory for edits, Git, and
Graphify. If `--project-dir` is omitted, the target defaults to the base
directory for backward compatibility.

Ralph now loads the project-local `ponytail` skill by default and prepends its
instructions to every iteration:

- Target-project overrides: `$RALPH_PROJECT_DIR/.agents/skills/ponytail/SKILL.md`,
  `$RALPH_PROJECT_DIR/.claude/skills/ponytail/SKILL.md`, or
  `$RALPH_PROJECT_DIR/skills/ponytail/SKILL.md`
- Base-engine fallback: `$RALPH_BASE_DIR/.agents/skills/ponytail/SKILL.md`,
  `$RALPH_BASE_DIR/.claude/skills/ponytail/SKILL.md`, or
  `$RALPH_BASE_DIR/skills/ponytail/SKILL.md`

The behavior is implemented in `scripts/ralph/ralph.sh`: `SKILL_NAME` defaults
to `ponytail`, `resolve_skill_file()` finds the project-local `SKILL.md`, and
`run_agent()` prepends its contents to the selected tool's prompt.

```bash
bash scripts/ralph/ralph.sh --tool codex --skill ponytail 10
```

Use `--skill <name>` for another project-local skill, or `--no-skill` to disable
skill loading for a run. Ralph searches the target project's `.agents/skills/`,
`.claude/skills/`, and `skills/` directories first, then the same directories
under the base engine directory.

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
