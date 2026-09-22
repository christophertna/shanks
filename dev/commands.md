# Shanks commands

Run these commands from the repository root. Use `.venv/bin/python` instead of
system `python` so Shanks uses the project environment.

## Modes

### Inspect the current mode

```bash
./shanks --mode
./shanks -mode
./shanks mode
```

These aliases only report the current `SHANKS_MODE`; they do not change it. The
default is `safe/normal (runtime)`. Development mode enables guarded local
capabilities, but human approval is still required before every commit, push,
and pull-request creation.

### Override the mode for one command

```bash
SHANKS_MODE=development ./shanks --mode
SHANKS_MODE=runtime ./shanks --mode
```

The `SHANKS_MODE=...` assignment applies only to that command. It does not
change the mode for the next command.

### Keep development mode enabled for the current shell

```bash
export SHANKS_MODE=development
./shanks --mode

unset SHANKS_MODE
./shanks --mode
```

`export` keeps development mode enabled for the current shell and commands it
launches until you run `unset` or close the shell. A new terminal starts with
the default safe/runtime mode unless you explicitly configure it otherwise.

Development mode does not disable dangerous-command hooks, quality gates, path
checks, secret redaction, or base-branch protection.

### Diagnose the local setup

```bash
./shanks doctor
```

Checks the effective mode, required tools, pinned dependencies, GitHub CLI
authentication, supported `SHANKS_*` settings, and SQLite checkpoint setup.
The command exits non-zero when a check fails.

## Run management

```bash
./shanks runs list
./shanks runs status RUN_ID
./shanks runs resume RUN_ID implement
./shanks runs cancel RUN_ID --reason "Operator stopped."
```

`list` and `status` report persisted lifecycle and latest-checkpoint details.
`status` also prints the prompt a paused run is waiting on (question, options,
and any extra payload), the current `repo_drift` note, and the newest
run-manifest events, so a paused run can be diagnosed without reading raw
checkpoint state. `resume` passes an interrupt response (`implement`, `learn`,
`approve`, `reject`) to a paused or stale run and prints the next prompt when
the run pauses again; add `--tool codex` or `--tool claude` to
pick the agent backend. `cancel` writes a safe-boundary stop request that a
live owner finishes at its next safe boundary.

```bash
./shanks runs recover
./shanks runs cleanup --keep-latest 20
./shanks runs cleanup --max-age 604800 --delete-records
```

`recover` marks expired leases as abandoned so a later owner can take over.
`cleanup` prunes terminal checkpoint history and is terminal-only unless
`--include-active` is passed; `--delete-records` also prunes lifecycle
records older than `--max-age` seconds.

```bash
SHANKS_MODE=development ./shanks runs remove RUN_ID --delete-branch
./shanks runs remove RUN_ID --force
```

Removes a completed run's worktree. It requires a finished terminal run and
rejects active leases. Deleting the local branch also requires
`SHANKS_MODE=development` plus `--delete-branch`; `--force` allows removing
an unmerged branch or a failed/cancelled run's worktree.

```bash
./shanks runs prune
./shanks runs prune --apply
SHANKS_MODE=development ./shanks runs prune --apply --delete-branches --include-remote
```

`prune` reports every run worktree and branch under Shanks' management that
does not belong to a live run (no lifecycle record, or a terminal record with
no active lease) — a dry-run report by default. `--apply` removes the
reported orphans; `--delete-branches` and `--include-remote` extend removal
to orphaned local and remote branches and require `SHANKS_MODE=development`.
Only worktrees under the configured worktree root and branches under the
run-branch prefix are ever considered, and protected branches (`main`,
`master`, the base branch) are never touched.

```bash
./shanks runs list --json
./shanks runs --checkpoint-db /tmp/shanks-checkpoints.sqlite list
```

`--json` on any `runs` subcommand prints machine-readable output instead of
the human-readable summary. Runtime flags (`--checkpoint-db`, `--project-dir`,
`--base-branch`, `--worktree-root`) go on the `runs` parser itself and apply
to every subcommand.

## Setup

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -r requirements-dev.txt
gh auth status
```

The first command installs runtime dependencies; the second installs the
development and quality tools. `gh auth status` checks the GitHub CLI login
required by the default preflight.

## Parallel agents

```bash
./shanks dev worktree feat/my-item
./shanks dev worktree feat/my-item --directory ../elsewhere
```

Creates a sibling worktree (`../shanks-feat-my-item` by default) on its own
branch, so a second coding agent can work at the same time without sharing this
checkout — one working tree only ever has one HEAD, so two agents in one
directory cannot be on different branches.

It copies the gitignored `.claude/settings.json` and symlinks `.venv` into the
new tree. Both matter: without the first, *no* hooks fire there (no
dangerous-command guard, no secret scanning); without the second,
`.venv/bin/python` does not exist, so tests and quality gates cannot run. A
bare `git worktree add` carries neither, which is why this command exists
rather than a documented recipe. It warns on stderr if the project itself has
no `.claude/settings.json` to copy.

Merge each branch to `main` through its own PR, then `git pull` in the other
worktree. `dev/new features.txt` is the file both agents tend to edit, so
expect to resolve it on whichever merges second.

## Tests and quality

```bash
.venv/bin/python -m unittest discover -s tests
bash hooks/test-guard.sh
```

The first command runs the complete unittest suite. The second runs the shell
regression checks for dangerous-command blocking and safe-command allowlisting.

```bash
.venv/bin/python scripts/quality_gates.py --diff-base origin/main
.venv/bin/python scripts/quality_gates.py --diff-base origin/main --staged
```

Runs Black, Ruff, Mypy, pip-audit, and the diff-size gate. The first form checks
the working tree against `origin/main`; `--staged` checks only staged changes
and requires `--diff-base`.

```bash
.venv/bin/python scripts/quality_gates.py \
  --diff-base origin/main --max-files 50 --max-lines 2000
```

Runs the same gates with explicit diff-size limits. This does not skip the
formatting, linting, typing, or security checks.

## Workflow and viewer

```bash
.venv/bin/python graph.py
```

Runs the small demo entry point in `graph.py` with the default dependencies.
Normal application code should build the graph and resume its intake interrupt
through LangGraph's `Command` API.

```bash
.venv/bin/python serve_graph.py
.venv/bin/python serve_graph.py --port 9000
```

Starts the Mermaid viewer at `http://127.0.0.1:8765/graph.html`, or at the
specified port. The viewer can inspect checkpointed runs and refreshes when
graph source files change.

```bash
export SHANKS_CHECKPOINT_DB=/tmp/shanks-checkpoints.sqlite
export SHANKS_RUN_LEASE_SECONDS=3600
export SHANKS_CHECKPOINT_RETENTION=100
```

Configures the shared checkpoint database, run-lease duration, and automatic
terminal-checkpoint retention. Use the same database path in the workflow and
viewer processes when they need to share runs.

## Ralph loop

```bash
cp scripts/ralph/prd.json.example scripts/ralph/prd.json
./scripts/ralph/ralph.sh
./scripts/ralph/ralph.sh 5
```

Creates a local PRD from the example and runs Ralph with Codex, the default
`ponytail` skill, and 10 iterations. A trailing number changes the maximum
iteration count. Ralph stops after an item is built so the graph owns
validation, commits, routing, and the GitHub handoff.

```bash
./scripts/ralph/ralph.sh --tool codex
./scripts/ralph/ralph.sh --tool claude
./scripts/ralph/ralph.sh --skill decisions
./scripts/ralph/ralph.sh --no-skill
./scripts/ralph/ralph.sh --project-dir path/to/project
./scripts/ralph/ralph.sh --run-dir path/to/run
./scripts/ralph/ralph.sh --graph-item-id item-1
./scripts/ralph/ralph.sh --graph-instructions "Use repository graph context."
```

These options select the agent tool or skill, disable skill injection, change
the target or run directory, target one PRD item, or add graph context. The
selected CLI must be installed and available on `PATH`.

## Graphify

```bash
graphify query "Where is the execution mode checked?"
graphify path "execution_mode()" "github_node()"
graphify explain "side-effect approvals"
graphify update .
```

`query` finds related code and concepts, `path` shows relationships between
two concepts, and `explain` focuses on one concept. `update .` refreshes the
local AST/code graph after source changes without an external model call.

## Git and GitHub handoff

```bash
git status -sb
git branch --show-current
git diff --check
git diff --stat
git diff --cached --check
```

Shows branch/worktree state, verifies whitespace, summarizes changes, and
checks the staged diff before committing.

```bash
git switch -c feature/my-change
git add path/to/file
git commit -m "feat: describe the change"
git push -u origin feature/my-change
```

Creates a feature branch, stages selected files, commits with the project’s
Conventional Commit style, and publishes the branch. Review the staged diff
and obtain approval immediately before each side effect.

```bash
gh pr create --base main --head feature/my-change \
  --title "feat: describe the change" \
  --body $'## Why\n- Explain the outcome.\n\n## Tested\n- `command used`'
gh pr view --web
```

Opens a pull request for human review and displays it in a browser. Push
approval and PR-opening approval are separate. Never push `main`, merge a PR,
or enable auto-merge through the agent.
