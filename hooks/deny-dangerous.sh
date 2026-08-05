#!/bin/bash
# Block catastrophic shell commands before an agent executes them.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS_FILE="${SHANKS_DANGEROUS_PATTERNS:-$SCRIPT_DIR/dangerous-patterns.txt}"
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
[ -f "$PATTERNS_FILE" ] || deny "missing pattern file: $PATTERNS_FILE"

INPUT="$(cat)" || deny "could not read hook input."
if ! CMD="$(printf '%s' "$INPUT" | jq -r '.tool_input.command // .toolInput.command // .command // empty' 2>/dev/null)"; then
  deny "hook input was not valid JSON."
fi
[ -z "$CMD" ] && exit 0

while IFS= read -r pattern; do
  case "$pattern" in
    ""|\#*) continue ;;
  esac
  if printf '%s\n' "$CMD" | grep -qE -- "$pattern" 2>/dev/null; then
    deny "a dangerous command pattern matched."
  fi
done < "$PATTERNS_FILE"
