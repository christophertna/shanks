# Shanks

Shanks is a small LangGraph-based workflow project for running Ralph-style agent tasks.
It turns a task plan into a repeatable workflow that can plan work, build or revise it,
ask a critic for feedback, validate the result, and move on to the next item.
Runs perform preflight checks before asking whether to learn the codebase or
implement a feature.
The learn branch records reusable codebase context and returns to intake; the
implement branch continues through planning, building, review, validation, and
the next unfinished item.

The repository also includes a lightweight Mermaid viewer for seeing the main workflow
and its recovery paths.

## Project structure

```text
.
├── workflow/                  # LangGraph workflow core
│   ├── adapters.py            # Agent, repository, GitHub, critic, and test boundaries
│   ├── cli.py                 # Mode and run-management command handling
│   ├── contracts.py           # Adapter and node contracts
│   ├── critic_output.schema.json
│   ├── debugger_output.schema.json
│   ├── lifecycle.py           # Run records, leases, recovery, and retention
│   ├── mode.py                # Runtime, development, and dry-run modes
│   ├── nodes.py               # Orchestration, routing, retries, approvals, and handoff
│   ├── retries.py             # Retry policy helpers
│   ├── state.py               # Workflow state, migrations, cancellation, and manifests
│   └── workspaces.py          # Isolated branches and Git worktrees
├── graph.py                   # Compiles the workflow and configures SQLite checkpoints
├── serve_graph.py             # Serves the Mermaid workflow viewer
├── shanks                     # Shell entrypoint for the CLI
├── scripts/
│   ├── quality_gates.py       # Formatting, lint, typing, audit, and diff-size checks
│   ├── sandbox_claude.sh      # macOS filesystem sandbox for Claude runs
│   └── ralph/                 # Ralph loop, instructions, and PRD example
├── hooks/                     # Git and agent safety/automation hooks
│   └── test.hooks/            # Hook regression harnesses
├── tests/                     # Standard-library unittest suite
├── skills/                    # Shared project skill sources
├── .github/workflows/
│   ├── tests.yml              # CI tests and hook harnesses
│   └── agent-smoke-tests.yml  # Opt-in real-CLI smoke tests (workflow_dispatch)
├── requirements.txt           # Runtime dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml             # Python tool configuration
├── README.md                  # Project documentation
└── CLAUDE.md                  # Developer and agent guidance
```

## Main pieces

- `workflow/` contains the shared state, contracts, adapters, and workflow nodes.
- `graph.py` assembles the executable LangGraph workflow.
- `serve_graph.py` serves the live graph viewer.
- `scripts/ralph/` contains Ralph-oriented supporting instructions and examples.
- `scripts/quality_gates.py` runs the repository's formatting, typing, lint,
  dependency/security, and diff-size checks.
- `skills/` contains shared skill sources; `.agents/skills/` and `.claude/skills/`
  expose project-scoped Codex and Claude entrypoints.
- `.github/workflows/tests.yml` runs the unittest suite and the
  `hooks/test.hooks/` guard harnesses (`test-deny-dangerous.sh`, `test-secret-scan.sh`,
  `test-pre-push.sh`, `test-run-impacted-tests.sh`, `test-post-merge-checkout.sh`)
  on pushes and pull requests.
- `.github/workflows/agent-smoke-tests.yml` is an opt-in, manually-triggered
  (`workflow_dispatch`) job that runs `tests/test_agent_integration.py` against
  the real `claude`/`codex` CLIs. It needs the `ANTHROPIC_API_KEY` and
  `OPENAI_API_KEY` repository secrets configured first, scoped to this job only.
- `tests/` covers graph routing, node contracts, viewer output, quality gates,
  run isolation, lifecycle recovery, and injected failure behavior.

## Quick start

Create a fresh Python 3.11 environment and install the locked runtime and
development dependencies:

```bash
python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

Point Git at the repo's tracked hooks so `graphify-out/` (generated, gitignored)
refreshes automatically after every pull or checkout, and `git push` is gated
on `scripts/quality_gates.py`:

```bash
git config core.hooksPath hooks
```

`./shanks doctor` checks this is set, so a skipped step surfaces as a
diagnostic instead of silently disabling local push gating.

Run the tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

Run every quality gate from a feature branch:

```bash
.venv/bin/python scripts/quality_gates.py --diff-base origin/main
```

The diff gate allows at most 50 changed files and 2,000 changed lines. Use
`--staged` with `--diff-base` to check the exact staged diff before committing.
Derived `graphify-out/` files are excluded from the source-diff limit.

Start the graph viewer:

```bash
.venv/bin/python serve_graph.py
```

Then open `http://127.0.0.1:8765/graph.html`.

## Supported toolchain

| Tool | Minimum version | Verified by |
| --- | --- | --- |
| Python | 3.11 | `./shanks doctor`, `pyproject.toml` (`target-version`/`mypy`), CI |
| Git | 2.30 | `./shanks doctor` |
| GitHub CLI (`gh`) | 2.40 | `./shanks doctor` (also checks `gh auth status`) |

Runtime and development dependencies are pinned in `requirements.txt` and
`requirements-dev.txt`; `./shanks doctor` verifies the installed versions
match. `.github/workflows/tests.yml` runs the same Python version in CI.

### GitHub token permissions

The GitHub handoff (`GitHubAdapter`, driven by `gh`) needs a token with:

- **Contents**: Read and write — push commits and branches.
- **Pull requests**: Read and write — open and update PRs.

For a fine-grained PAT, grant both on the target repository. For a classic
PAT, the `repo` scope covers both.

Pushing changes to `.github/workflows/*` needs its own, separate permission:
a classic PAT needs the `workflow` scope, and a fine-grained PAT needs
"Workflows: Read and write" — otherwise `git push` is rejected outright
("refusing to allow a Personal Access Token to create or update workflow
... without `workflow` scope"). For a `gh`-managed token, fix it with:

```bash
gh auth refresh -h github.com -s workflow
```

## Commands

| Command | Explanation |
| --- | --- |
| `python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt` | Create a fresh environment with locked runtime and development dependencies. |
| `./shanks --mode` | Show the current mode. `-mode` and `mode` are aliases. |
| `./shanks -mode` | Show the current mode. |
| `./shanks mode` | Show the current mode. |
| `./shanks doctor` | Check tools and versions, pinned dependencies, GitHub authentication, environment variables, SQLite setup, and `core.hooksPath`. |
| `./shanks runs list` | List checkpointed runs. |
| `./shanks runs status RUN_ID` | Show a run's persisted lifecycle and checkpoint status, the prompt it is paused on, its repository drift note, and its newest run-manifest events. |
| `./shanks runs resume RUN_ID RESPONSE` | Resume a run with a response such as `implement`, `learn`, `approve`, or `reject`. |
| `./shanks runs cancel RUN_ID` | Request cancellation at the next safe boundary. |
| `./shanks runs recover` | Mark expired leases as abandoned. |
| `./shanks runs cleanup --keep-latest COUNT` | Prune terminal checkpoint history; add `--delete-records --max-age SECONDS` to prune old lifecycle records too. |
| `SHANKS_MODE=development ./shanks runs remove RUN_ID --delete-branch` | Remove a completed run worktree and local branch; use `--force` for unmerged or failed/cancelled runs. |
| `./shanks runs prune` | Report orphaned run worktrees and branches. |
| `./shanks runs prune --apply` | Remove reported orphaned run worktrees and branches. |
| `./shanks runs prune --apply --delete-branches --include-remote` | Also remove local and remote branches; requires `SHANKS_MODE=development`. |
| `SHANKS_MODE=dry-run ./shanks --mode` | Inspect the delivery-preview mode. |
| `.venv/bin/python -m pip install -r requirements-dev.txt` | Install development dependencies. |
| `.venv/bin/python -m unittest discover -s tests` | Run the full test suite. |
| `bash hooks/test.hooks/test-deny-dangerous.sh` | Test the dangerous-command guard. |
| `.venv/bin/python scripts/quality_gates.py --diff-base origin/main` | Run all quality gates against `origin/main`. |
| `.venv/bin/python scripts/quality_gates.py --diff-base origin/main --staged` | Run all quality gates against the staged diff. |
| `.venv/bin/python serve_graph.py` | Start the workflow viewer; add `--port PORT` to choose a port. |
| `./scripts/ralph/ralph.sh [options]` | Run the Ralph agent loop. |
| `graphify query "<question>"` | Inspect a scoped graph for a codebase question. |
| `graphify path "<A>" "<B>"` | Inspect the relationship between two graph nodes. |
| `graphify explain "<concept>"` | Inspect a focused graph concept. |
| `graphify update .` | Refresh the generated project graph. |
| `git status -sb` | Show branch and worktree status. |
| `git diff --check` | Check for whitespace errors. |
| `git commit` | Create a reviewed local commit. |
| `git push` | Push reviewed changes. |
| `gh pr create` | Open a pull request. |

See the local `dev/commands.md` reference for detailed command capabilities and options.

Workflow checkpoints are stored in `.shanks/checkpoints.sqlite`, so the viewer
can inspect runs started by another process. Set `SHANKS_CHECKPOINT_DB` in both
processes to use a different shared database path.

Each checkpoint also carries a persisted `run_manifest`. Its redacted audit
events record agent prompts and model names, executed commands, validation/test
output, staged diffs, commit SHAs, and pull-request URLs/IDs. The manifest is
available from the viewer's Live execution panel and survives checkpointed
retries.

Checkpoint state carries a `state_schema_version`. Older unversioned checkpoints
are treated as v0 and migrated to the current schema when loaded; new checkpoints
are written with the current version. Checkpoints from a newer unsupported version
fail clearly instead of being interpreted incorrectly.

Default graphs derive a run identity from the configured `thread_id`. Each run gets
an isolated branch and Git worktree under `.shanks/worktrees/`, and the persisted
state records `run_id`, `run_branch`, and `workspace_directory`. Agent and GitHub
subprocesses use that worktree for the run, so separate runs do not share a mutable
project directory.

The shared SQLite checkpoint store also owns a durable run lease. A live lease
blocks a second owner of the same thread, an interrupted run remains resumable,
and an expired lease is marked abandoned before a later owner recovers it. Lease
duration is configurable with `SHANKS_RUN_LEASE_SECONDS`. Terminal checkpoints
release their lease and use the configured retention limit (default 100); call
`VersionedSqliteSaver.cleanup(...)` for explicit count/age-based cleanup, or set
`SHANKS_CHECKPOINT_RETENTION` for the automatic limit.

The `runs` CLI exposes the same lifecycle controls to operators. `list` and
`status` report persisted lifecycle and latest-checkpoint details; `resume`
passes an interrupt response such as `implement`, `learn`, `approve`, or
`reject`; `cancel` writes a safe-boundary cancellation request and lets a live
owner finish it; `recover` marks expired leases abandoned. Cleanup is
terminal-only by default. Worktree removal requires a finished terminal run,
rejects active leases, verifies the persisted path and branch against the
configured run workspace, and requires `SHANKS_MODE=development` plus
`--delete-branch` before deleting a local branch.

Agent failures are classified as `transient`, `validation`, `guardrail`,
`budget`, `cancelled`, or `permanent`. Safe agent and validation nodes retry only
`transient` failures with bounded exponential backoff (0.5, 1, 2 seconds, capped
at 8 seconds), recording per-node retry counts in the checkpoint and run manifest.
Validation failures still go to the debugger. The branch push and pull-request
handoff also retry `transient` failures (network interruptions, GitHub rate
limits) the same way: a re-pushed branch is a no-op once the remote already has
the commits, and a re-run pull-request handoff looks up and reconciles an
already-created PR instead of opening a duplicate. Commit creation is not
retried automatically because a partial commit failure needs operator review.

Runs have persisted safety budgets: one hour of wall time, three build attempts
per item, twenty total build attempts, and an estimated 100,000-token ceiling by
default. Set `max_runtime_seconds`, `max_attempts`, `max_total_attempts`,
`max_tokens`, or `max_cost_usd` in the initial state to override them. CLI
adapters estimate token usage from their prompt and output; custom adapters can
report exact `input_tokens`, `output_tokens`, and `cost_usd` in `AgentResult`.

Default limits are: `max_runtime_seconds=3600`, `max_attempts=3` per item,
`max_total_attempts=20`, `max_tokens=100000`, and `max_cost_usd=0.0` (cost
enforcement disabled until a positive limit is configured). Each CLI and GitHub
subprocess also has a 3600-second adapter timeout.

Stop a checkpointed run cleanly at its next safe boundary:

```python
from workflow.state import cancel_run

graph.update_state(config, cancel_run("Operator stopped the run."))
graph.invoke(None, config)
```

The run ends with `status="cancelled"` and records the reason instead of
starting another backend or side-effecting node.

The viewer's Live execution panel accepts the workflow's `thread_id` and polls
the current node, PRD item, attempt count, budget usage, last error, model,
the prompt a paused run is waiting on, the repository drift note, checkpoint
history, and run manifest. Expand an audit event to inspect its
recorded prompt, commands, output, diff, commit, or pull-request details. Use
the same thread ID when starting the workflow and inspecting it.

For local Shanks development, set `SHANKS_MODE=development`. This enables
guarded local capabilities such as deletion of local run-scoped branches
through `RunWorkspaceManager.delete_branch(...)`; it does not approve side
effects. Human approval is still required separately before each commit, push,
and pull-request creation. The mode does not disable quality gates,
project/path checks, secret redaction, base-branch protection, or the
catastrophic-command hook. Unset the variable or set it to `runtime` to
restore safe/normal mode.

Set `SHANKS_MODE=dry-run` to run through delivery while previewing the
side-effecting handoff. Commit, push, and pull-request operations are skipped;
the run manifest records the planned commands, changed/new-file diff, commit
message, push, and PR details. The terminal run status is
`pull_request_preview`. The workflow still uses its isolated run workspace for
agent and validation work.

## Preflight checks

The default GitHub-backed graph checks that `git`, `gh`, `bash`, `jq`, and
`gitleaks` are available (the last two are also required by the secret-scan
hook, so a missing one now fails fast at preflight instead of stalling the
build agent's first tool call), the run is on a non-`main` clean branch,
GitHub CLI authentication works, the unittest suite passes, and all quality
gates pass. The gates run
Black in check mode, Ruff, Mypy, pip-audit across runtime and development
requirements, and the diff-size limit. A failed check ends with
`status="preflight_failed"` before intake or agent work. Lightweight injected
test repositories can omit the preflight capability and are explicitly marked
`preflight_skipped`.

Planning then refreshes a repository drift note once per PRD item: it fetches
`origin/main`, reports how many commits the run branch is behind it and which
worktree changes are already uncommitted, stores that in the persisted
`repo_drift` state field, and puts it in front of every downstream agent
prompt. It is advisory context rather than a gate, so a failed fetch records
the reason and the run continues.

## Interactive workflow

### Start a run

The first graph invocation runs preflight and then pauses at intake. Resume the
same thread with the user's label:

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

### Workflow paths

| Path | Sequence |
| --- | --- |
| Learn | `preflight → intake → learn → intake` |
| Implement | `preflight → intake → implement → planning → building → critic/auditor → validation → commit → push → pull request → next item or stop` |
| Validation recovery | `validation → debugger → planning → building` |
| Transient failure | Retry the exact failed node after bounded backoff. |

### Recovery and validation

| Event | Behavior |
| --- | --- |
| Critic rejection | Feedback is included in the next builder attempt. |
| Permanent build failure | Follows the explicit failed-build terminal route and skips critic and validation. |
| Transient failure | Preflight, learning, planning, building, critic, validation, and debugger failures retry at the exact failed node. |
| Guardrail failure | Stops in a terminal failure route instead of retrying. |
| Validation failure | The read-only debugger records the root cause and repair instructions in the PRD item; planning sends the enriched requirement back to the builder. |
| `passes` | Means Ralph finished the build for the current PRD item. |
| `validation` | Means the graph's authoritative test gate passed. |
| `validationCommand` | Runs from the project directory when provided; otherwise the full `.venv/bin/python -m unittest discover -s tests` suite runs. Commands are tokenized and executed without a shell. |

### Delivery approvals

- **Validated implement runs:** Pause for human approval before committing each
  item, then pause again before pushing the branch and reconciling its pull
  request after the final item passes.
- **Approval responses:** Resume with `Command(resume="approve")`, or end the
  run without the side effect with `Command(resume="reject")`.
- **Dry-run implement runs:** Skip approval pauses and finish with the same
  handoff details in the run manifest without committing, pushing, or changing
  a pull request.

### Safety and hooks

- **Subprocess and GitHub boundaries:** Security guardrails keep subprocesses on
  approved executables and configured directories, resolve GitHub file paths
  through the project root (including symlinks), redact common credentials from
  command output and PR text, and limit the GitHub adapter to required
  read/commit/push and pull-request lifecycle commands.
- **Credentials and branches:** GitHub credentials are passed only to the `gh`
  adapter boundary. Agent and test subprocesses do not receive `GH_TOKEN` or
  `GITHUB_TOKEN`, GitHub CLI prompts are disabled, and Shanks protects `main`,
  `master`, and its configured base branch from direct pushes or local deletion.
  Reviewer and label values are validated before a pull-request command can
  run. CI requests only `contents: read`; write-capable GitHub operations use
  the operator's authenticated `gh` session after separate approvals.
- **Dangerous commands and paths:** `hooks/deny-dangerous.sh` blocks
  catastrophic shell commands; `hooks/guard-dependency-files.sh` blocks
  Write/Edit on lockfiles, pinned dependency manifests, and `.env` files. See
  `hooks/guarded-paths.txt`; set `SHANKS_ALLOW_DEPENDENCY_EDIT=1` to override
  the dependency-path guard. Run
  `hooks/test.hooks/test-deny-dangerous.sh` to test the dangerous-command
  guard.
- **Secret scanning:** `hooks/secret-scan.sh` scans Write/Edit content and Bash
  command text with `gitleaks` and blocks matches before they are written or
  run. It fails closed when `jq` or `gitleaks` is unavailable; `./shanks doctor`
  checks for both. The Bash path catches secrets typed literally into command
  text, not values assembled from existing files or variables at runtime. Run
  `hooks/test.hooks/test-secret-scan.sh` to test it.
- **Graph and impacted-test hooks:** `hooks/graphify-update.sh` refreshes the
  graphify graph in the background after each Write/Edit. `hooks/run-impacted-tests.sh`
  runs the matching unittest module for a touched Python file or the matching
  shell harness for a touched hook, and skips silently when no match exists.
  Run `hooks/test.hooks/test-run-impacted-tests.sh` to test it. These hooks are
  wired through the gitignored `.claude/settings.json`, which contains a
  machine-specific `graphify` path.

### Agent decisions and GitHub handoff

- **Uncertainties:** Ralph records only genuinely uncertain implementation
  decisions reported by the builder. They come from the `RALPH_UNCERTAINTIES`
  output section and are stored per PRD item for later review.
- **Implement handoff:** Each validated item is committed locally. After the
  last item passes, the final handoff pushes the current non-`main` branch and
  reconciles its pull request with `gh`.
- **Pull-request reconciliation:** Open PRs have generated text and configured
  reviewer/label policy updated only when needed. Closed unmerged PRs are
  reported without reopening by default; merged PRs are reported as complete;
  behind or aged PR branches are marked stale. Set `reopen_closed=True` on
  `GitHubAdapter` when reopening is explicitly desired.
- **Resumability:** Persisted commit and PR IDs make commit and pull-request
  handoff safe to resume without duplicating side effects. Handoff details are
  also added to the run manifest. Authenticate `gh` before starting the run.
