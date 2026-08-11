# Hooks

Hooks are wired via the local, gitignored `.claude/settings.json`
(`RunWorkspaceManager._sync_local_guardrails()` copies it into every run
worktree). They only fire for Claude-CLI-driven agents — Codex-based agents
(`CodexAdapter`, `GPT56LunaCriticAdapter`, `DebuggerAdapter(tool="codex")`)
use Codex's own `--sandbox` flag instead and never see them.

## Reference

| Hook | Trigger | Matcher | Does | On missing tool |
| --- | --- | --- | --- | --- |
| `deny-dangerous.sh` | PreToolUse | `Bash` | Blocks catastrophic shell commands (`rm -rf /`, `curl\|sh`, force-push, `gh auth token`, ...) via `dangerous-patterns.txt` | Fails closed (blocks) if `jq` missing |
| `guard-dependency-files.sh` | PreToolUse | `Write\|Edit` | Blocks writes to lockfiles, pinned `requirements*.txt`, `.env` files via `guarded-paths.txt`; override with `SHANKS_ALLOW_DEPENDENCY_EDIT=1` | Fails open (allows) if `jq` missing |
| `secret-scan.sh` | PreToolUse | `Write\|Edit`, `Bash` | Scans written/edited content or the Bash command text with `gitleaks`, blocks on a match | Fails closed (blocks) if `jq`/`gitleaks` missing |
| `graphify hook-guard search` | PreToolUse | `Bash\|Grep` | Injects a reminder to run `graphify query` before raw grep/Bash search | Advisory only, never blocks |
| `graphify hook-guard read` | PreToolUse | `Read\|Glob` | Injects a reminder to run `graphify query`/`explain` before reading raw source | Advisory only, never blocks |
| `graphify-update.sh` | PostToolUse | `Write\|Edit` | Refreshes the graphify graph in the background (AST-only, no LLM cost) | No-op if graphify isn't installed |
| `pr-checkpoint-reminder.sh pre` | PreToolUse | `Bash` (`gh pr create` only) | Reminds to use the `AskUserQuestion` tool for the `github-commit-pr` skill's checkpoint 1 (open now vs. wait) | Advisory only, never blocks |
| `pr-checkpoint-reminder.sh post` | PostToolUse | `Bash` (`gh pr create` only) | Reminds to use `AskUserQuestion` for checkpoint 2 (merge now vs. wait) once the PR is open | Advisory only, never blocks |

Pattern files: `dangerous-patterns.txt` (for `deny-dangerous.sh`),
`guarded-paths.txt` (for `guard-dependency-files.sh`). Regression harnesses:
`test-guard.sh`, `test-secret-scan.sh`.

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
`secret-scan.sh`, and `graphify-update.sh` on `Write`/`Edit`; `hook-guard read`
on `Read`.

## Other agents (critic, debugger)

`ClaudeAdapter(read_only=True)`, `DebuggerAdapter(tool="claude")`, and
`ClaudeOpus48CriticAdapter` run with `--tools Read` only — no `Bash`, `Grep`,
`Write`, or `Edit` — so only `graphify hook-guard read` ever fires for them.
`GPT56LunaCriticAdapter` and `DebuggerAdapter(tool="codex")` are Codex-based
and see no Claude Code hooks at all.

`pr-checkpoint-reminder.sh` never fires for either group above: PR creation
goes through `GitHubAdapter`'s own direct `gh` subprocess call, not a Claude
Bash tool call, so there's nothing for a Claude Code hook to see.

## Developer

An interactive Claude Code session isn't tool-scoped by `--tools`, so every
hook in the table is live: `deny-dangerous.sh`, `hook-guard search`,
`hook-guard read`, `guard-dependency-files.sh`, `secret-scan.sh`, and
`graphify-update.sh`. `pr-checkpoint-reminder.sh` is developer-only in
practice — it only fires when `gh pr create` is run as a Bash tool call,
which is how the `github-commit-pr` skill does it. Test the scriptable hooks
with `bash hooks/test-guard.sh` and `bash hooks/test-secret-scan.sh`.
