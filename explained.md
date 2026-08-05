# This Project, In Simple Words

This project is a small test system for using AI agents in a work flow.

It uses **LangGraph** to connect steps together.

This file is for human orientation only. Ralph and other agents do not load it
as prompt context, and Graphify excludes it from the code map.

## The main flow

```text
intake
   ├─ learn ──→ learning ──→ intake
   └─ implement
          ↓
planning
   ↓
building
   ↓
critic_auditor
   ├─ reject ──→ building again with critic feedback
   └─ approve
          ↓
validation
   ├─ fail ──→ debugger ──→ planning for the same item
   └─ pass
          ↓
more items? ──→ Complete
   └──────────→ planning
```

- `intake` asks whether the run should learn the codebase or implement a feature.
- `learning` records reusable codebase context and returns to `intake`.
- `planning` picks the next unfinished PRD item.
- `building` writes or changes code.
- `critic_auditor` checks the code with the configured critic adapter.
- If the critic rejects it, its feedback is passed into the next `building` attempt.
- If the critic approves it, the code goes to `validation`.
- If validation fails, `debugger` studies the problem.
- The problem then goes back to `planning` for the same PRD item.
- If validation passes, the `more items` decision sends the next PRD item to
  `planning`.
- When no items remain, `more items` sends the graph to `Complete`.
- Failed builds use an explicit terminal `failed_build` route and do not run
  critic or validation.

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

## Project skills

The project keeps reusable skills under `.agents/skills/`:

- `domain-modeling` records shared terminology, context, and architecture decisions.
- `grilling` stress-tests plans and decisions before implementation.
- `decisions` lists genuinely uncertain choices made during the current work;
  it is invoked manually.
- `github-commit-pr` provides shared commit and pull-request conventions for
  Codex and Claude.

The shared `decisions` skill source lives in `skills/decisions/` and is exposed
through symlinked project entrypoints under `.agents/skills/` and `.claude/skills/`.
## Important files

### `graph.py`

Builds the LangGraph flow.

It connects the nodes and controls where each step goes next.

`validation` and `more items` are shown as diamonds in the viewer because they
are decision steps. The default graph uses a shared SQLite checkpoint store at
`.shanks/checkpoints.sqlite`; set `SHANKS_CHECKPOINT_DB` to override the path.

### `workflow/state.py`

Defines the shared state.

Think of the state as a shared notebook. It stores things like:

- The selected learn or implement mode.
- The current PRD item.
- Whether each item passed building and validation.
- The plan.
- Files changed.
- The state schema version used to read and resume checkpoints.
- Whether each item passed building and validation.
- Critic feedback.
- Validation errors.
- Debugger findings.
- Genuine builder uncertainties, grouped by PRD item.
- Attempt counts.
- Which model was used.

### Checkpoint compatibility

The workflow stores state in `.shanks/checkpoints.sqlite`. Each state has a
`state_schema_version` so the workflow can tell how to read persisted data.

Older checkpoints without a version are treated as v0 and migrated to v1 when
they are loaded. New checkpoints are stamped with the current version. If a
checkpoint comes from a newer version than this code understands, the workflow
stops with a clear error instead of guessing at the state shape.

The authoritative validator currently runs the local unittest suite. The
workflow tracks validation per PRD item, but item-specific acceptance criteria
and validation commands are future work.

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

`LocalTestAdapter` is the default validation adapter for real project runs and
reports test failures back to the graph as structured validation errors.
`RalphAdapter` parses the builder's `RALPH_UNCERTAINTIES` section into the
current item's uncertainty list.

Security guardrails are enforced at the adapter boundary. Agent subprocesses
use an executable allowlist and configured working-directory roots. The GitHub
adapter resolves candidate files through the project root, rejects symlink or
traversal escapes, allows only the Git and `gh` commands needed by the graph,
passes a minimal GitHub environment, and redacts common credentials from output
and PR text. The repo-local `hooks/deny-dangerous.sh` hook provides an
additional denylist for catastrophic shell commands issued inside a CLI agent;
`hooks/test-guard.sh` exercises its high-risk and ordinary cases.

### `workflow/nodes.py`

Contains the work done by each graph node:

- Planning.
- Building.
- Critic review.
- Validation.
- Debugging.
- The `more items` routing decision.

It also selects the next unfinished PRD item and handles retries.

### `graph.html`

Shows the graph in a browser.

The nodes are white. Decision nodes are diamonds.

It also has a Live execution panel. Enter a workflow `thread_id` to see the
current node, PRD item, attempt count, last error, model, and recent
checkpoints while the workflow runs.

### `serve_graph.py`

Runs the local graph viewer.

It reads `graph.py`, creates a Mermaid diagram, and sends it to `graph.html`.
The browser updates when `graph.py` changes. Its `/graph-state` endpoint reads
`get_state()` and `get_state_history()` for the selected thread.

The workflow and viewer share checkpoints through
`.shanks/checkpoints.sqlite`, which allows separate Python processes to see
the same run. Set `SHANKS_CHECKPOINT_DB` in both processes to use a different
shared database path.

Validated items are committed by `commit_item`. The final `github_node` pushes
the branch and opens the pull request. Persisted commit and PR IDs act as
replay guards when a run resumes after a failure.

### `tests/`

Checks that the graph works.

The tests cover retries, validation failures, item progress, attempt limits,
failed-build routing, idempotent GitHub handoff, viewer state inspection, and
agent adapters. GitHub Actions runs the unittest suite on pushes and pull
requests.

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
the target directory becomes the agent's working directory for edits and
Graphify. If `--project-dir` is omitted, the target defaults to the base
directory for backward compatibility, so this agent repository's Git tracking
also remains at the base directory. A separately supplied target uses its own
Git repository when it is a different repository.

Each builder iteration reports only real uncertainty about an implemented
choice. The runner stores those bullets by PRD item and omits routine or
confident decisions.

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
- Human approval gates before commit, push, and pull-request side effects are
  not implemented yet.
- Pull-request lifecycle management, such as updating existing PRs and
  assigning reviewers, is not implemented yet.
