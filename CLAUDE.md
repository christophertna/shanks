## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- `explained.md` is human-only orientation documentation. Do not load it into an agent context; it is excluded from Graphify through `.graphifyignore`.

## Project overview

Shanks is a LangGraph workflow that runs "Ralph-style" agent tasks: an intake step
chooses `learn` (documentation) or `implement` (feature) mode, then drives a
plan → build/revise → critic feedback → validate → next-item loop. `graph.py`
assembles the graph; `serve_graph.py` serves a live Mermaid viewer at
`http://127.0.0.1:8765/graph.html`. Core logic lives in `workflow/` (`state.py`,
`contracts.py`, `adapters.py`, `nodes.py`).

## Commands

- Tests: `.venv/bin/python -m unittest discover -s tests` (use the checked-in
  venv's interpreter, not system `python`)
- Viewer: `.venv/bin/python serve_graph.py`
- Diagnose the local setup: `./shanks doctor` — checks mode, required tools
  (including Git/gh/gitleaks version floors), pinned dependencies, GitHub CLI
  auth, `SHANKS_*` settings, SQLite checkpoint setup, and whether every
  `hooks/*.sh` is wired into the gitignored `.claude/settings.json`; exits
  non-zero on failure.
- Isolate a second agent: `./shanks dev worktree <branch>` — creates a sibling
  worktree with `.claude/settings.json` copied and `.venv` symlinked, so two
  agents can work on different branches at once without sharing a tree.
- Manage runs: `./shanks runs list|status RUN_ID|resume RUN_ID|cancel RUN_ID|
  recover|cleanup|remove RUN_ID|prune` — see `dev/commands.md` for the full
  option reference.
- No linter/formatter is configured in this repo.

## Gotchas

- The graph pauses at the `intake` node on first invocation and must be resumed
  with `Command(resume="implement"|"learn")` — a plain `graph.invoke()` will not
  run to completion.
- Each validated PRD item is committed locally automatically as part of the
  graph run — the workflow itself makes commits, not just the human/agent
  driving it.
- The final step of an `implement` run pushes the current non-`main` branch and
  reconciles or opens its PR via `gh` — `gh` must be pre-authenticated.
- Skills are split across three locations with overlapping content:
  `.claude/skills/`, `.agents/skills/`, and top-level `skills/`. Check which
  copy is canonical before editing one.
- The build agent (`RalphAdapter` / `scripts/ralph/ralph.sh`,
  `ClaudeAdapter(read_only=False)`) runs Claude with `--permission-mode
  acceptEdits --tools Read,Write,Edit,Bash,Grep,Glob` rather than
  `--dangerously-skip-permissions`. `_validate_execution` only restricts
  which executable and paths *launch* the agent, not what it does once
  running.
- On top of that, `scripts/sandbox_claude.sh` wraps the same Claude build
  invocation in a real OS-level sandbox (`sandbox-exec`/Seatbelt on macOS)
  confined to the target worktree, a fresh private per-run temp dir, and
  `~/.claude`/`~/.codex`/`~/.npm`/`~/.cache` — so `Bash` can no longer write
  outside the worktree even though it's an allowed tool. Falls back to
  unsandboxed (with a stderr warning) on non-macOS or without `sandbox-exec`.
  Network is intentionally left open for now. See `tests/test_sandbox_claude.py`
  for the actual containment checks.
- `.claude/` is gitignored, so a fresh run worktree from
  `RunWorkspaceManager.ensure()` (`workflow/workspaces.py`) wouldn't
  otherwise carry `.claude/settings.json` — and without it, Claude Code
  loads no project hooks (e.g. `hooks/deny-dangerous.sh`, the dangerous-shell-
  command guard) in that worktree. `_sync_local_guardrails()` copies it in
  right after `git worktree add`. `hooks/` itself is tracked, so it's
  already checked out normally.

## Shared checkout

Another coding agent (Codex, or a second Claude session) may be editing this
repo at the same time, in the same checkout — this has already caused two
sessions' uncommitted work to be mixed into one dirty tree. The full rules are
in `AGENTS.md`; the short version:

- Run `git status -sb` before your first write. A dirty tree you did not make,
  or a branch you did not create, means someone else is working here — stop and
  say so.
- Start work with `./shanks dev worktree <branch>` rather than sharing this
  tree — it copies the gitignored `.claude/settings.json` and symlinks `.venv`,
  which a bare `git worktree add` does not, leaving that tree with no hooks and
  no test runner. `git checkout -b` in place is fine.
- Stage explicit paths; never `git add -A` or `git add .`.
- `hooks/guard-worktree.sh` blocks a branch switch while tracked files are
  dirty. Override with `SHANKS_ALLOW_BRANCH_SWITCH=1` only when the dirty files
  are certainly yours.

## Repo etiquette

- Commit style: Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`), short
  imperative subject, no scopes, PR number in parens when applicable.
