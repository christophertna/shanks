#!/bin/bash
# Block switching branches while tracked files are dirty, so one agent's
# uncommitted work is never carried onto another agent's branch. Two agents
# sharing this checkout is the failure this guards: a `git checkout` moves
# HEAD under whoever else is mid-edit, and git does it silently.
# Override for one call with SHANKS_ALLOW_BRANCH_SWITCH=1.

set -euo pipefail

[ "${SHANKS_ALLOW_BRANCH_SWITCH:-}" = "1" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
command -v git >/dev/null 2>&1 || exit 0

INPUT="$(cat)" || exit 0
COMMAND="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)"
[ -z "$COMMAND" ] && exit 0
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$CWD" ] && cd "$CWD" 2>/dev/null

# Only a move to another ref is risky, and only as a real git subcommand -
# not the word "checkout" inside an unrelated string.
if ! printf '%s' "$COMMAND" |
  grep -qE '(^|[;&|(]|&&)[[:space:]]*git[[:space:]]+(checkout|switch)([[:space:]]|$)'; then
  exit 0
fi

# Creating a branch (-b/-B/-c/-C) leaves the working tree exactly where it is
# and carries the changes deliberately. That is how an agent legitimately
# starts work, so it stays allowed even with a dirty tree.
if printf '%s' "$COMMAND" | grep -qE '[[:space:]]-(b|B|c|C)([[:space:]]|$)'; then
  exit 0
fi

# `git checkout -- <path>` restores files and never moves HEAD.
# ponytail: a bare `git checkout <path>` (no --) is indistinguishable from a
# ref here without resolving it, so it is treated as a switch and blocked when
# dirty. Over-blocking a destructive path restore is the safe direction.
if printf '%s' "$COMMAND" | grep -qE '[[:space:]]--([[:space:]]|$)'; then
  exit 0
fi

DIRTY="$(git status --porcelain --untracked-files=no 2>/dev/null)" || exit 0
[ -z "$DIRTY" ] && exit 0

BRANCH="$(git branch --show-current 2>/dev/null || true)"
printf 'Blocked by Shanks worktree guard: refusing to switch branches with uncommitted changes to tracked files.\n' >&2
printf 'Another agent may be working in this checkout. Currently on %s with:\n%s\n' \
  "${BRANCH:-a detached HEAD}" "$DIRTY" >&2
printf 'Commit or stash first, work in your own tree (git worktree add ../shanks-<branch> -b <branch>),\n' >&2
printf 'or set SHANKS_ALLOW_BRANCH_SWITCH=1 to override for this call.\n' >&2
exit 2
