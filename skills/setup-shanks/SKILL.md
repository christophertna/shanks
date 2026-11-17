---
name: setup-shanks
description: Load the context a new agent needs before working on Shanks. Use at the start of any session that will read, debug, or change this repo, or when the user runs /setup-shanks.
---

# Setup

Orient before touching anything. Do these in order.

1. Run `git status -sb`. A dirty tree or a branch you did not create means
   another agent is working here: stop and say so. Start your own work with
   `./shanks dev worktree <branch>` (or `git checkout -b`).
2. Read `CLAUDE.md` (Claude Code) or `AGENTS.md` (Codex) at the repo root. They
   hold the commands, gotchas, shared-checkout rules, and commit style.
3. Read `dev/context.md` if it exists: architecture, modes and safety, and
   agent tool scoping. `dev/` is gitignored, so it may be absent or stale; check
   it against the code and `git log` before trusting it.
4. Read `dev/commands.md` only when you need the `./shanks runs` option
   reference.
5. For codebase questions, run `graphify query "<question>"` first when
   `graphify-out/graph.json` exists. Read `graphify-out/GRAPH_REPORT.md` only
   for broad architecture review.
6. Run `./shanks doctor` and `./shanks --mode` to confirm tools, hooks, and the
   real mode. Do not infer the mode from docs.

Never load `dev/explained.md` (human-only) into agent context. Roadmap lives in
`dev/new features.txt`; use the `roadmap-review` skill for it.

Report back in a few lines: branch, mode, doctor result, and anything surprising.
