# Hooks

Hooks are wired via the local, gitignored `.claude/settings.json`
(`RunWorkspaceManager._sync_local_guardrails()` copies it into every run
worktree). They only fire for Claude-CLI-driven agents — Codex-based agents
(`CodexAdapter`, `GPT56LunaCriticAdapter`, `DebuggerAdapter(tool="codex")`)
use Codex's own `--sandbox` flag instead and never see them.

## Fail-open vs fail-closed on a missing `jq` (or other required tool)

The "On missing tool" column below isn't accidental — it's a per-hook call
that needs to stay a decision, not whatever the next hook's author happens to
pick. Default to fail closed (block the action): use it whenever skipping the
check would let something irreversible or safety-critical through, which is
the case for every hook whose entire job is to `deny()` something —
`deny-dangerous.sh` (catastrophic shell commands) and `secret-scan.sh`
(secrets). Fail open only when the hook is advisory/convenience rather than a
safety backstop, and a missed check costs less than blocking every write on a
dev machine that's missing `jq` — `guard-dependency-files.sh` is the one
example today: it's a nudge around lockfiles/`.env` files that's already
bypassable via `SHANKS_ALLOW_DEPENDENCY_EDIT=1`, so failing open on a missing
`jq` doesn't remove a real guarantee. When adding a new hook, pick fail-closed
unless you can name why this hook is more like `guard-dependency-files.sh`
than `deny-dangerous.sh`.

`guard-worktree.sh` is the second fail-open example, for the same reason: it
is a collision nudge between concurrent agents, not a safety backstop, and it
is already bypassable via `SHANKS_ALLOW_BRANCH_SWITCH=1`. What it prevents is
also recoverable — a wrongly carried change is still in the working tree, not
destroyed — so failing open on a missing `jq`/`git` costs less than blocking
every branch switch on a machine that lacks them.

## Reference

| Hook | Trigger | Matcher | Does | On missing tool |
| --- | --- | --- | --- | --- |
| `deny-dangerous.sh` | PreToolUse | `Bash` | Blocks catastrophic shell commands (`rm -rf /`, `curl\|sh`, force-push, `gh auth token`, ...) via `dangerous-patterns.txt` | Fails closed (blocks) if `jq` missing |
| `guard-dependency-files.sh` | PreToolUse | `Write\|Edit` | Blocks writes to lockfiles, pinned `requirements*.txt`, `.env` files via `guarded-paths.txt`; override with `SHANKS_ALLOW_DEPENDENCY_EDIT=1` | Fails open (allows) if `jq` missing |
| `secret-scan.sh` | PreToolUse | `Write\|Edit`, `Bash` | Scans written/edited content or the Bash command text with `gitleaks`, blocks on a match | Fails closed (blocks) if `jq`/`gitleaks` missing |
| `guard-worktree.sh` | PreToolUse | `Bash` | Blocks `git checkout`/`git switch` to another ref while tracked files are dirty, so a second agent in this checkout never carries the first one's uncommitted work onto its branch; branch creation (`-b`/`-B`/`-c`/`-C`) and `--` path restores stay allowed. Override with `SHANKS_ALLOW_BRANCH_SWITCH=1` | Fails open (allows) if `jq`/`git` missing |
| `graphify hook-guard search` | PreToolUse | `Bash\|Grep` | Injects a reminder to run `graphify query` before raw grep/Bash search | Advisory only, never blocks |
| `graphify hook-guard read` | PreToolUse | `Read\|Glob` | Injects a reminder to run `graphify query`/`explain` before reading raw source | Advisory only, never blocks |
| `graphify-update.sh` | PostToolUse | `Write\|Edit` | Refreshes the graphify graph in the background (AST-only, no LLM cost) | No-op if graphify isn't installed |
| `format-touched.sh` | PostToolUse | `Write\|Edit` | Applies `black` to the touched `.py` file and reports `ruff check` (plus `mypy`, only for files listed in `[tool.mypy] files`) failures, so a quality-gate failure surfaces at the edit rather than at the next `--diff-base origin/main` run. Blocking feedback on failure — including on a reformat, since the file on disk no longer matches what was written | Skips silently if `jq` or `.venv/bin/python` are missing |
| `run-impacted-tests.sh` | PostToolUse | `Write\|Edit` | Runs the check matching the touched file: `<name>.py` -> `tests/test_<name>.py` (a touched `tests/test_*.py` runs itself); `hooks/<name>.sh` -> `hooks/test.hooks/test-<name>.sh` (a touched `hooks/test.hooks/test-*.sh` runs itself). Blocking feedback on failure | Skips silently if `jq`, the matching test/harness, or `.venv/bin/python` (Python case only) are missing |

Pattern files: `dangerous-patterns.txt` (for `deny-dangerous.sh`),
`guarded-paths.txt` (for `guard-dependency-files.sh`). Regression harnesses
live in `hooks/test.hooks/`: `test-deny-dangerous.sh`, `test-secret-scan.sh`,
`test-guard-worktree.sh`, `test-pre-push.sh`, `test-run-impacted-tests.sh`,
`test-format-touched.sh`, `test-post-merge-checkout.sh`. Every one of them has
a row in `tests/tests.md` and a line in `.github/workflows/tests.yml`;
`test_every_shell_harness_is_documented_and_run_in_ci` (`tests/test_cli.py`)
fails if a new harness is missing from either.

`secret-scan.sh`'s Bash coverage only catches secrets typed literally into
the command text (e.g. `echo "sk-..." >> config.py`, a heredoc, `sed -i`) —
not ones assembled from existing files or variables at runtime. That residual
gap is real but strictly smaller than having no Bash coverage at all.

## Ralph / build agents

`RalphAdapter` (`scripts/ralph/ralph.sh`, Claude branch) and
`ClaudeAdapter(read_only=False)` run with
`--tools Read,Write,Edit,Bash,Grep,Glob` inside `scripts/sandbox_claude.sh`'s
filesystem sandbox, so every hook above can fire: `deny-dangerous.sh`,
`secret-scan.sh`, and `hook-guard search` on `Bash`; `guard-dependency-files.sh`,
`secret-scan.sh`, `graphify-update.sh`, `run-impacted-tests.sh`, and
`format-touched.sh` on `Write`/`Edit`; `hook-guard read` on `Read`.

## Other agents (critic, debugger)

`ClaudeAdapter(read_only=True)`, `DebuggerAdapter(tool="claude")`, and
`ClaudeOpus48CriticAdapter` run with `--tools Read,Grep,Glob` — no `Bash`,
`Write`, or `Edit` — so `graphify hook-guard read` fires for them (`Read`/`Glob`)
and `graphify hook-guard search` fires on their `Grep` calls; still fully
read-only, same guarantee as before.
`GPT56LunaCriticAdapter` and `DebuggerAdapter(tool="codex")` are Codex-based
and see no Claude Code hooks at all.

## Developer

An interactive Claude Code session isn't tool-scoped by `--tools`, so every
hook in the table is live: `deny-dangerous.sh`, `hook-guard search`,
`hook-guard read`, `guard-dependency-files.sh`, `secret-scan.sh`,
`graphify-update.sh`, `run-impacted-tests.sh`, and `format-touched.sh`. Test
them with `bash hooks/test.hooks/test-deny-dangerous.sh`,
`bash hooks/test.hooks/test-secret-scan.sh`,
`bash hooks/test.hooks/test-run-impacted-tests.sh`, and
`bash hooks/test.hooks/test-format-touched.sh`.

A `PreToolUse`/`PostToolUse` hook on `gh pr create` (nudging toward the
`github-commit-pr` skill's `AskUserQuestion` checkpoints) was tried and
removed: it can only see tool-call boundaries, and the actual failure mode
observed was asking in prose and never reaching a `gh pr create` call at
all, so the hook never had anything to intercept. Revisit only if Claude
Code hooks gain visibility into prior transcript/tool-call history.

## Real Git hooks

`post-merge`, `post-checkout`, and `pre-push` are ordinary Git hooks, not
Claude Code hooks. They only fire once a clone points Git at this directory:

```bash
git config core.hooksPath hooks
```

`post-merge`/`post-checkout` run `graphify update .` after a pull/checkout so
the untracked, generated `graphify-out/graph.json` (and friends) stay
current — `post-checkout` skips the no-op case where the tree didn't
actually change (e.g. `checkout -b` off the current commit), and both fail
open (no-op) if `graphify` isn't on PATH. Regression harness:
`test.hooks/test-post-merge-checkout.sh`. `pre-push` runs
`scripts/quality_gates.py --diff-base origin/main` (formatting, linting,
typing, dependency audit, diff size) and blocks the push on failure, so a
gate failure surfaces locally instead of only after opening a PR — fails
open with a stderr warning if `.venv/bin/python` isn't present, rather than
blocking every push on a missing dev environment. Regression harness:
`test.hooks/test-pre-push.sh`.
