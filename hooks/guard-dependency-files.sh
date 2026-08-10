#!/bin/bash
# Block Write/Edit from touching lockfiles, pinned dependency manifests, and
# .env secrets. Override for one call with SHANKS_ALLOW_DEPENDENCY_EDIT=1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS_FILE="${SHANKS_GUARDED_PATTERNS:-$SCRIPT_DIR/guarded-paths.txt}"

[ "${SHANKS_ALLOW_DEPENDENCY_EDIT:-}" = "1" ] && exit 0
command -v jq >/dev/null 2>&1 || exit 0
[ -f "$PATTERNS_FILE" ] || exit 0

INPUT="$(cat)" || exit 0
FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -z "$FILE_PATH" ] && exit 0

BASENAME="$(basename -- "$FILE_PATH")"

# Templates are meant to be edited; only the real secret file is guarded.
case "$BASENAME" in
  .env.example|.env.sample|.env.template|.env.dist) exit 0 ;;
esac

while IFS= read -r pattern; do
  case "$pattern" in
    ""|\#*) continue ;;
  esac
  if printf '%s\n' "$BASENAME" | grep -qE -- "$pattern" 2>/dev/null; then
    printf 'Blocked by Shanks dependency guard: %s matches guarded pattern %s\nSet SHANKS_ALLOW_DEPENDENCY_EDIT=1 to override for this session.\n' \
      "$BASENAME" "$pattern" >&2
    exit 2
  fi
done < "$PATTERNS_FILE"

exit 0
