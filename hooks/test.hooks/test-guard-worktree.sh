#!/bin/bash
# Small regression harness for guard-worktree.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/../guard-worktree.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CLEAN="$TMP/clean"
DIRTY="$TMP/dirty"
for repo in "$CLEAN" "$DIRTY"; do
  mkdir -p "$repo"
  git -C "$repo" init --quiet
  git -C "$repo" config user.email agent@example.com
  git -C "$repo" config user.name agent
  printf 'one\n' > "$repo/tracked.txt"
  git -C "$repo" add tracked.txt
  git -C "$repo" commit --quiet -m "initial"
done
# Only the dirty repo has an uncommitted change to a tracked file.
printf 'two\n' > "$DIRTY/tracked.txt"
# Untracked files survive a checkout, so they must not count as dirty.
printf 'scratch\n' > "$CLEAN/untracked.txt"

passed=0
failed=0

check() {
  local expected="$1"
  local label="$2"
  local repo="$3"
  local command="$4"
  local json verdict

  json="$(jq -cn --arg cmd "$command" --arg cwd "$repo" \
    '{tool_input:{command:$cmd},cwd:$cwd}')"
  if printf '%s' "$json" | "$HOOK" >/dev/null 2>&1; then
    verdict="allow"
  else
    verdict="block"
  fi
  if [ "$verdict" = "$expected" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL expected=%s got=%s: %s\n' "$expected" "$verdict" "$label"
  fi
}

# The incident this guard exists for.
check block "switch branches with a dirty tree" "$DIRTY" "git checkout main"
check block "git switch with a dirty tree" "$DIRTY" "git switch main"
check block "switch buried in a compound command" "$DIRTY" "cd /tmp && git checkout main"

# Creating a branch carries the work deliberately; that is the normal flow.
check allow "git checkout -b with a dirty tree" "$DIRTY" "git checkout -b feat/x"
check allow "git switch -c with a dirty tree" "$DIRTY" "git switch -c feat/x"
check allow "git checkout -B with a dirty tree" "$DIRTY" "git checkout -B feat/x"

# Path restores never move HEAD.
check allow "path restore with --" "$DIRTY" "git checkout -- tracked.txt"

# A clean tree has nothing to carry.
check allow "switch branches with a clean tree" "$CLEAN" "git checkout main"
check allow "untracked files do not count as dirty" "$CLEAN" "git switch main"

# Unrelated commands must pass straight through.
check allow "not a git command" "$DIRTY" "echo git checkout main"
check allow "different git subcommand" "$DIRTY" "git status --short"
check allow "checkout as a substring" "$DIRTY" "grep -r checkout ."

# The documented escape hatch.
SHANKS_ALLOW_BRANCH_SWITCH=1 check allow "override env var" "$DIRTY" "git checkout main"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
