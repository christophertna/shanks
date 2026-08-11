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

## Main pieces

- `workflow/` contains the shared state, contracts, adapters, and workflow nodes.
- `graph.py` assembles the executable LangGraph workflow.
- `serve_graph.py` serves the live graph viewer.
- `scripts/ralph/` contains Ralph-oriented supporting instructions and examples.
- `scripts/quality_gates.py` runs the repository's formatting, typing, lint,
  dependency/security, and diff-size checks.
- `skills/` contains shared skill sources; `.agents/skills/` and `.claude/skills/`
  expose project-scoped Codex and Claude entrypoints.
- `.github/workflows/tests.yml` runs the unittest suite and the `hooks/test-guard.sh`/
  `hooks/test-secret-scan.sh` guard harnesses on pushes and pull requests.
- `tests/` covers graph routing, node contracts, viewer output, quality gates,
  run isolation, lifecycle recovery, and injected failure behavior.

## Quick start

Create a fresh Python 3.11 environment and install the locked runtime and
development dependencies:

```bash
python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

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

## Commands

- `python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt` — create a fresh environment with locked dependencies.
- `./shanks --mode` / `./shanks -mode` / `./shanks mode` — show the current mode.
- `./shanks doctor` — check tool presence and versions (see Supported toolchain), pinned dependencies, GitHub authentication, environment variables, and SQLite checkpoint setup.
- `./shanks runs list|status RUN_ID|resume RUN_ID RESPONSE|cancel RUN_ID` — manage checkpointed runs.
- `./shanks runs recover` — mark expired leases as abandoned.
- `./shanks runs cleanup --keep-latest COUNT` — prune terminal checkpoint history; add `--delete-records --max-age SECONDS` to prune old lifecycle records too.
- `SHANKS_MODE=development ./shanks runs remove RUN_ID --delete-branch` — remove a completed run worktree and its local branch (use `--force` for unmerged or failed/cancelled runs).
- `./shanks runs prune` / `./shanks runs prune --apply` — report, then optionally remove, orphaned run worktrees and branches; add `--delete-branches --include-remote` (requires `SHANKS_MODE=development`) to also clean up branches.
- `SHANKS_MODE=dry-run ./shanks --mode` — inspect the delivery-preview mode.
- `.venv/bin/python -m pip install -r requirements-dev.txt` — install development dependencies.
- `.venv/bin/python -m unittest discover -s tests` — run all tests.
- `bash hooks/test-guard.sh` — test dangerous-command guard behavior.
- `.venv/bin/python scripts/quality_gates.py --diff-base origin/main` — run all quality gates.
- `.venv/bin/python scripts/quality_gates.py --diff-base origin/main --staged` — check staged changes.
- `.venv/bin/python serve_graph.py [--port PORT]` — start the workflow viewer.
- `./scripts/ralph/ralph.sh [options]` — run the Ralph agent loop.
- `graphify query|path|explain|update .` — inspect or refresh the project graph.
- `git status -sb`, `git diff --check`, `git commit`, `git push`, `gh pr create` — inspect and hand off reviewed changes.

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
checkpoint history, and run manifest. Expand an audit event to inspect its
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

## Interactive workflow

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

Critic feedback is included in the next builder attempt when a review rejects
an item. A permanent failed build follows the explicit failed-build terminal
route and does not proceed to critic or validation.

Transient preflight, learning, planner, builder, critic, validator, and debugger
failures return to the exact failed node after backoff. Permanent and guardrail
failures stop in a terminal failure route instead of receiving the same retry
treatment.

When validation fails, the read-only debugger analyzes the failure, records its
root cause and repair instructions in the current PRD item, then planning sends
the enriched requirement to the builder.

In each PRD item, `passes` means Ralph finished the build and `validation`
means the graph’s authoritative test gate passed.

Each PRD item may also include an `acceptanceCriteria` list and a
`validationCommand`. The validation node runs the current item's command from
the project directory when one is provided; otherwise it falls back to the
full `.venv/bin/python -m unittest discover -s tests` suite. Commands are
tokenized and executed without a shell.

Validated implement runs pause for human approval before committing each item.
After the last item, they pause again before pushing the branch and reconciling
its pull request. Resume an approval interrupt with `Command(resume="approve")` or
end the run without the side effect with `Command(resume="reject")`.

Dry-run implement runs skip those approval pauses and finish with the same
handoff details as previews in the run manifest without committing, pushing, or
changing a pull request.

Security guardrails keep subprocesses on approved executables and configured
directories, resolve GitHub file paths through the project root (including
symlinks), redact common credentials from command output and PR text, and limit
the GitHub adapter to the required read/commit/push and PR-lifecycle commands.
GitHub credentials are passed only to the `gh` adapter boundary; agent and test
subprocesses do not receive `GH_TOKEN` or `GITHUB_TOKEN`, and GitHub CLI prompts
are disabled. Shanks protects `main`, `master`, and its configured base branch
from direct pushes or local deletion. Reviewer and label values are
validated against their configured allowlists before a PR command can run. The
CI test workflow requests only `contents: read`; write-capable GitHub operations
use the operator's authenticated `gh` session after the separate approvals.
The repo-local
`hooks/deny-dangerous.sh` hook adds a denylist for catastrophic shell commands;
run `hooks/test-guard.sh` to check it. `hooks/guard-dependency-files.sh` blocks
Write/Edit on lockfiles, pinned dependency manifests, and `.env` files (patterns
in `hooks/guarded-paths.txt`; override with `SHANKS_ALLOW_DEPENDENCY_EDIT=1`).
`hooks/secret-scan.sh` scans Write/Edit content and Bash command text with
`gitleaks` and blocks outright on a match, rather than flagging it after
it's already on disk (or already run) and possibly committed; run
`hooks/test-secret-scan.sh` to check it. It fails closed (blocks) if `jq` or
`gitleaks` aren't installed, and `./shanks doctor` checks for both. The Bash
path only catches secrets typed literally into the command text, not ones
assembled from existing files/variables at runtime.
`hooks/graphify-update.sh` refreshes the graphify graph in the background after
each Write/Edit (AST-only, no LLM cost). All are wired via a local
`.claude/settings.json`, which is gitignored since it hardcodes a
machine-specific `graphify` path.

Ralph records only genuinely uncertain implementation decisions reported by the
builder. They are parsed from the `RALPH_UNCERTAINTIES` output section and stored
per PRD item for later review.

For implement runs, each validated item is committed locally. After the last
item passes, the final GitHub handoff pushes the current non-`main` branch and
reconciles its pull request with the GitHub CLI (`gh`). Existing open PRs have
their generated text and configured reviewer/label policy updated only when
needed; closed unmerged PRs are reported without reopening by default, merged
PRs are reported as complete, and behind or aged PR branches are marked stale.
Set `reopen_closed=True` on `GitHubAdapter` when reopening is explicitly desired.
Persisted commit and PR IDs
make commit and pull-request handoff safe to resume without duplicating those
side effects; the same handoff details are added to the run manifest. Authenticate
`gh` before starting the run.
