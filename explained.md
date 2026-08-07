# This Project, In Simple Words

This project is a small test system for using AI agents in a work flow.

It uses **LangGraph** to connect steps together.

This file is for human orientation only. Ralph and other agents do not load it
as prompt context, and Graphify excludes it from the code map.

## The main flow

```text
preflight
   ├─ fail ──→ Complete
   └─ pass
          ↓
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

- `preflight` checks the tools, branch, GitHub authentication, test suite, and
  all repository quality gates.
- `intake` asks whether the run should learn the codebase or implement a feature.
- `learning` records reusable codebase context and returns to `intake`.
- `planning` picks the next unfinished PRD item.
- `building` writes or changes code.
- `critic_auditor` checks the code with the configured critic adapter.
- If the critic rejects it, its feedback is passed into the next `building` attempt.
- If the critic approves it, the code goes to `validation`.
- If validation fails, `debugger` studies the problem.
- Transient failures in safe agent or validation nodes return to that same node
  after bounded exponential backoff; permanent and guardrail failures stop.
- The problem then goes back to `planning` for the same PRD item.
- If validation passes, the `more items` decision sends the next PRD item to
  `planning`.
- When no items remain, `more items` sends the graph to `Complete`.
- Permanent build failures use an explicit terminal `failed_build` route and do
  not run critic or validation.

There are per-item and whole-run attempt limits. The workflow also tracks a
wall-clock deadline, estimated token usage, and reported cost. When a limit is
reached, or when `cancel_run(...)` is applied to a checkpoint, the graph takes
the terminal `stop_run` path without invoking another backend.

Every checkpoint also carries a `run_manifest`, which is the run's append-only
audit history. Events are redacted before persistence and include the agent
prompt and model, commands, validation/test output, staged diffs, commit SHA,
and pull-request URL/ID when those operations occur. This keeps execution
history with the same SQLite checkpoint that supports resume.

Runs are isolated by their configured `thread_id`. Each run gets a persisted
`run_id`, its own Git branch, and a reusable worktree under
`.shanks/worktrees/`; agent, Ralph, and GitHub subprocesses use that worktree
as their working directory. The checkpoint store also keeps a durable lease:
a live lease prevents two owners from running the same thread at once, an
interrupted run can be resumed, and an expired lease is recovered by the next
owner. Terminal checkpoints release the lease. Set
`SHANKS_RUN_LEASE_SECONDS` to change the default one-hour lease, and
`SHANKS_CHECKPOINT_RETENTION` to change the default retention of 100 recent
checkpoints. `VersionedSqliteSaver.cleanup(...)` can perform explicit
count- or age-based cleanup, including the associated checkpoint writes.

## LIMITS

These defaults are defined in `workflow/state.py` and apply to new or migrated
runs:

| Limit | Default | Meaning |
| --- | ---: | --- |
| `max_runtime_seconds` | `3600` (1 hour) | Wall-clock budget for the whole run. |
| `max_attempts` | `3` per item | Build/rework attempts allowed for one PRD item. |
| `max_total_attempts` | `20` | Build attempts allowed across the whole run. |
| `max_tokens` | `100000` estimated tokens | Combined estimated input and output token budget. |
| `max_cost_usd` | `0.0` (disabled) | Enabled only when set to a positive value and adapters report cost. |
| CLI/GitHub subprocess timeout | `3600` seconds | Per-command adapter timeout, also capped by remaining run time for agent adapters. |
| `cancel_requested` | `False` | Set with `cancel_run(...)` to stop at the next safe checkpoint. |

The lease and checkpoint-retention settings are configured through the
environment variables described above rather than through the per-run budget
fields in this table.

Adapters that do not expose provider usage use a conservative text estimate;
custom adapters can report exact token and cost values through `AgentResult`.

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

`preflight`, `validation`, and `more items` are shown as decision steps in the
viewer because they can route to another node or stop. The default graph uses a
shared SQLite checkpoint store at
`.shanks/checkpoints.sqlite`; set `SHANKS_CHECKPOINT_DB` to override the path.
The graph also wires the run workspace manager and lifecycle manager into the
nodes so each `thread_id` has an isolated worktree and a durable lease.

### `workflow/state.py`

Defines the shared state.

Think of the state as a shared notebook. It stores things like:

- The selected learn or implement mode.
- Whether preflight passed before intake.
- The current PRD item.
- Each item's acceptance criteria and optional validation command.
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
- Failure classifications and per-node retry counts.
- Run time, total-attempt, token, and cost budgets.
- Cumulative adapter usage.
- A cancellation request and its reason.
- Which model was used.
- The persisted run manifest and audit history.
- The run identity, branch, and isolated workspace directory.
- The lifecycle status, lease expiry, heartbeat, and recovery count.

### Checkpoint compatibility

The workflow stores state in `.shanks/checkpoints.sqlite`. Each state has a
`state_schema_version` so the workflow can tell how to read persisted data.

Older checkpoints without a version are treated as v0 and migrated through the
supported versions when they are loaded. New checkpoints are stamped with the
current version. If a checkpoint comes from a newer version than this code
understands, the workflow stops with a clear error instead of guessing at the
state shape.

The current schema version is 6. The v4-to-v5 migration adds run identity,
branch, and workspace fields; the v5-to-v6 migration adds lease, heartbeat,
and recovery metadata.

The authoritative validator runs the current PRD item's `validationCommand`
when one is present and falls back to the local unittest suite otherwise.
`acceptanceCriteria` is carried with the current item into planning, building,
critic review, and debugging requests.

### `workflow/contracts.py`

Defines the common shape for agents.

Every agent gets an `AgentRequest` and returns an `AgentResult`.

This lets different agents fit into the same graph.

`AgentRequest` carries the current item's acceptance criteria, optional
validation command, and remaining run timeout. `AgentResult` can report input
tokens, output tokens, cost, the redacted prompt, executed commands, and a
staged diff, and a classified failure; CLI adapters estimate tokens from text
when a provider does not expose usage directly.

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

`LocalTestAdapter` is the default validation adapter for real project runs. It
runs an item's validation command when present, otherwise the full local
unittest suite, and reports failures back to the graph as structured validation
errors.
`RalphAdapter` parses the builder's `RALPH_UNCERTAINTIES` section into the
current item's uncertainty list.
Agent and GitHub adapters honor the active run workspace. When Ralph runs in a
worktree, it receives a per-run `--run-dir`, so its PRD, progress log, metadata,
and archive stay under that run's `.shanks/ralph/` directory instead of being
shared with another run.
`GitHubAdapter.preflight()` checks required tools, the current branch and
working tree, GitHub CLI authentication, the local unittest suite, and the
repository quality gates before intake. `commit_item()` repeats the quality
gates against the staged diff before creating a commit. `publish_pr()` pushes
the branch, reconciles existing pull requests, and creates one only when no
matching request exists. Open requests receive text and configured reviewer or
label updates only when needed; closed and merged requests are distinguished,
stale branches are reported, and closed requests remain closed unless
`reopen_closed=True` is explicitly configured.

### `scripts/quality_gates.py`

This is the single command used by CI and GitHub handoff checks. It runs Black
format verification, Ruff linting, Mypy typing, a pip-audit scan of runtime and
development requirements, and a diff-size check. The default diff limit is 50
files or 2,000 changed lines; generated `graphify-out/` files are excluded.
The script uses argument lists rather than a shell, and the GitHub adapter
allowlists its exact command shape.

GitHub commit operations capture the staged diff and command trail before the
commit. Pull-request handoff events retain the commit/PR metadata, including a
pull-request ID extracted from its URL. Local validation output is recorded as
test output in the manifest.

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

- Preflight.
- Planning.
- Building.
- Critic review.
- Validation.
- Debugging.
- The `more items` routing decision.

It also selects the next unfinished PRD item and handles retries.

Failures are classified before routing. Only transient failures from safe
learning, planner, builder, critic, validator, debugger, and preflight operations
use the targeted backoff path. Commit and GitHub publication failures are
recorded but are not automatically retried because they can create side effects.

The `_versioned_node` wrapper starts the run clock, accumulates usage, checks
budgets before and after each node, and routes cancellation or budget exhaustion
to `stop_run`. It also acquires or renews the run lease, creates or reuses the
run worktree, scopes adapter requests to that workspace, records interruptions,
and handles stale-lease recovery.

### `graph.html`

Shows the graph in a browser.

The nodes are white. Decision nodes are diamonds.

It also has a Live execution panel. Enter a workflow `thread_id` to see the
current node, PRD item, attempt count, run budgets, usage totals, last error,
model, run identity, branch, workspace, lifecycle/lease metadata, recent
checkpoints, and the persisted run manifest while the workflow runs. Manifest
entries can be expanded to inspect their recorded details.

### `serve_graph.py`

Runs the local graph viewer.

It reads `graph.py`, creates a Mermaid diagram, and sends it to `graph.html`.
The browser updates when `graph.py` changes. Its `/graph-state` endpoint reads
`get_state()` and `get_state_history()` for the selected thread.
The `/graph-state` response also includes the current run identity, branch,
workspace, lifecycle metadata, and `run_manifest`.

The workflow and viewer share checkpoints through
`.shanks/checkpoints.sqlite`, which allows separate Python processes to see
the same run. Set `SHANKS_CHECKPOINT_DB` in both processes to use a different
shared database path.

Validated items are committed by `commit_item`. The final `github_node` pushes
the branch and reconciles its pull request. Persisted commit and PR IDs act as
replay guards when a run resumes after a failure, and each operation appends an
audit event to the run manifest, including pull-request state and staleness.

### `tests/`

Checks that the graph works.

The tests cover retries, validation failures, item progress, attempt limits,
failed-build routing, idempotent GitHub handoff, run isolation, lease and stale
run recovery, checkpoint cleanup, viewer state inspection, agent adapters, the
quality-gate parser/runner, and fault-injection behavior. The fault suite
injects Git/GitHub, validation, checkpoint, and agent failures.
GitHub Actions installs the development quality tools, runs the unittest suite,
and runs every quality gate on pushes and pull requests.

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

During a graph run, Ralph receives `--run-dir` pointing into the run's
worktree. Its `RALPH_PRD_FILE` and related progress/metadata files therefore
stay with that run, so concurrent or resumed worktrees do not overwrite the
base runner's state.

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
- Approval gates are present before commit and publish side effects; a caller
  must resume with an explicit approval response to continue.
- Run worktrees can be removed by the workspace manager, but completed-run
  worktree and branch cleanup remains an explicit operation.
- Pull-request lifecycle management is implemented for GitHub CLI handoff;
  real temporary-repository and fake-`gh` integration coverage remains on the
  roadmap.
