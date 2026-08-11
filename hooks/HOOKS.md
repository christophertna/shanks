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
| `secret-scan.sh` | PreToolUse | `Write\|Edit` | Scans written/edited content with `gitleaks`, blocks the write on a match | Fails closed (blocks) if `jq`/`gitleaks` missing |
| `graphify hook-guard search` | PreToolUse | `Bash\|Grep` | Injects a reminder to run `graphify query` before raw grep/Bash search | Advisory only, never blocks |
| `graphify hook-guard read` | PreToolUse | `Read\|Glob` | Injects a reminder to run `graphify query`/`explain` before reading raw source | Advisory only, never blocks |
| `graphify-update.sh` | PostToolUse | `Write\|Edit` | Refreshes the graphify graph in the background (AST-only, no LLM cost) | No-op if graphify isn't installed |

Pattern files: `dangerous-patterns.txt` (for `deny-dangerous.sh`),
`guarded-paths.txt` (for `guard-dependency-files.sh`). Regression harnesses:
`test-guard.sh`, `test-secret-scan.sh`.

## Ralph / build agents

`RalphAdapter` (`scripts/ralph/ralph.sh`, Claude branch) and
`ClaudeAdapter(read_only=False)` run with
`--tools Read,Write,Edit,Bash,Grep,Glob` inside `scripts/sandbox_claude.sh`'s
filesystem sandbox, so every hook above can fire: `deny-dangerous.sh` and
`hook-guard search` on `Bash`; `guard-dependency-files.sh`, `secret-scan.sh`,
and `graphify-update.sh` on `Write`/`Edit`; `hook-guard read` on `Read`.

## Other agents (critic, debugger)

`ClaudeAdapter(read_only=True)`, `DebuggerAdapter(tool="claude")`, and
`ClaudeOpus48CriticAdapter` run with `--tools Read` only — no `Bash`, `Grep`,
`Write`, or `Edit` — so only `graphify hook-guard read` ever fires for them.
`GPT56LunaCriticAdapter` and `DebuggerAdapter(tool="codex")` are Codex-based
and see no Claude Code hooks at all.

## Developer

An interactive Claude Code session isn't tool-scoped by `--tools`, so every
hook in the table is live: `deny-dangerous.sh`, `hook-guard search`,
`hook-guard read`, `guard-dependency-files.sh`, `secret-scan.sh`, and
`graphify-update.sh`. Test them with `bash hooks/test-guard.sh` and
`bash hooks/test-secret-scan.sh`.
