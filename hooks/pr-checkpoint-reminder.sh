#!/bin/bash
# Advisory-only nudge toward the github-commit-pr skill's two AskUserQuestion
# checkpoints, right at the `gh pr create` call they gate. Never blocks: a
# skill is a prompt, not enforced code, so this can't guarantee the tool gets
# called - it just narrows how easy it is to forget, the same way the
# graphify hook-guard hooks nudge toward `graphify query` at the point of use.

set -euo pipefail

STAGE="${1:-pre}"

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)" || exit 0
CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)" || exit 0
[ -z "$CMD" ] && exit 0

printf '%s\n' "$CMD" | grep -qE '(^|[;&|[:space:]])gh[[:space:]]+pr[[:space:]]+create([[:space:]]|$)' || exit 0

if [ "$STAGE" = "pre" ]; then
  printf 'github-commit-pr skill checkpoint 1: call the AskUserQuestion tool (not prose) to ask whether to open the PR now or wait, before running this.\n'
else
  printf 'github-commit-pr skill checkpoint 2: once this PR is open, call the AskUserQuestion tool (not prose) to ask whether to merge now or wait - a separate question from checkpoint 1.\n'
fi
