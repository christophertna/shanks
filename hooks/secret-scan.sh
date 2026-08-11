#!/bin/bash
# Block Write/Edit/Bash from introducing secrets before they land on disk or
# run. PostToolUse would be too late: Ralph auto-commits each validated PRD
# item, so a PreToolUse hook is what actually stops a leaked credential from
# reaching the tree, not just flags it after the fact. The Bash path only
# catches secrets typed literally into the command text, not ones assembled
# from existing files/variables at runtime.

set -euo pipefail

MODE="${1:-exitcode}"

deny() {
  local reason="$1"
  if [ "$MODE" = "cursor" ]; then
    jq -cn --arg reason "$reason" '{permission:"deny",user_message:"Command blocked by Shanks security guard.",agent_message:$reason}'
    exit 0
  fi
  printf 'Blocked by Shanks security guard: %s\n' "$reason" >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || deny "jq is required to inspect hook input."
command -v gitleaks >/dev/null 2>&1 || deny "gitleaks is required to scan writes for secrets (brew install gitleaks; see ./shanks doctor)."

INPUT="$(cat)" || deny "could not read hook input."
if ! CONTENT="$(printf '%s' "$INPUT" | jq -r '[.tool_input.content, .tool_input.new_string, .tool_input.command] | map(select(. != null)) | join("\n")' 2>/dev/null)"; then
  deny "hook input was not valid JSON."
fi
[ -z "$CONTENT" ] && exit 0

FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)" || FILE_PATH=""
SCAN_NAME="$(basename -- "${FILE_PATH:-bash-command}")"

SCAN_DIR="$(mktemp -d "${TMPDIR:-/tmp}/shanks-secret-scan.XXXXXX")"
trap 'rm -rf "$SCAN_DIR"' EXIT
printf '%s' "$CONTENT" >"$SCAN_DIR/$SCAN_NAME"

REPORT="$(gitleaks detect --source "$SCAN_DIR" --no-git --no-banner -f json -r - 2>/dev/null)" && exit 0

SUMMARY="$(printf '%s' "$REPORT" | jq -r '[.[] | "\(.RuleID) at line \(.StartLine)"] | join(", ")' 2>/dev/null)"
deny "potential secret in ${FILE_PATH:-a Bash command} (${SUMMARY:-gitleaks flagged this}). Remove it, or add a gitleaks:allow comment if this is a false positive."
