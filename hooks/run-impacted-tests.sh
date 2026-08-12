#!/bin/bash
# Run just the unittest module matching a touched Python file (naming
# convention: <name>.py -> tests/test_<name>.py; a touched tests/test_*.py
# runs itself), so a regression surfaces on the edit that caused it instead
# of only at the next full suite run. Skips silently when no test module
# matches rather than guessing broadly at what to test.

set -u

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)" || exit 0
FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$PWD"
[ -n "$FILE_PATH" ] || exit 0

case "$FILE_PATH" in
  *.py) ;;
  *) exit 0 ;;
esac

DIRNAME="$(dirname -- "$FILE_PATH")"
STEM="$(basename -- "$FILE_PATH" .py)"

case "$STEM" in
  test_*)
    if [ "$DIRNAME" = "$CWD/tests" ]; then
      MODULE="tests.$STEM"
    else
      MODULE="tests.test_$STEM"
    fi
    ;;
  *)
    MODULE="tests.test_$STEM"
    ;;
esac

TEST_FILE="$CWD/tests/${MODULE#tests.}.py"
[ -f "$TEST_FILE" ] || exit 0

PYTHON="${SHANKS_TEST_IMPACT_PYTHON:-$CWD/.venv/bin/python}"
command -v "$PYTHON" >/dev/null 2>&1 || exit 0

OUTPUT="$(cd "$CWD" && "$PYTHON" -m unittest "$MODULE" 2>&1)"
STATUS=$?

if [ "$STATUS" -ne 0 ]; then
  printf '%s\n\nScoped test-impact hook: `%s` failed after editing %s.\n' \
    "$OUTPUT" "$MODULE" "$FILE_PATH" >&2
  exit 2
fi

exit 0
