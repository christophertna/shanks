#!/bin/bash
# Run just the regression check matching a touched file, so a regression
# surfaces on the edit that caused it instead of only at the next full
# suite/harness run. Skips silently when nothing matches rather than
# guessing broadly at what to test.
#
# Python: <name>.py -> tests/test_<name>.py (a touched tests/test_*.py
# runs itself). Shell: hooks/<name>.sh -> hooks/test.hooks/test-<name>.sh
# (a touched hooks/test.hooks/test-*.sh runs itself).

set -u

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)" || exit 0
FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$PWD"
[ -n "$FILE_PATH" ] || exit 0

DIRNAME="$(dirname -- "$FILE_PATH")"

case "$FILE_PATH" in
  *.py)
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

    TARGET="$CWD/tests/${MODULE#tests.}.py"
    [ -f "$TARGET" ] || exit 0

    PYTHON="${SHANKS_TEST_IMPACT_PYTHON:-$CWD/.venv/bin/python}"
    command -v "$PYTHON" >/dev/null 2>&1 || exit 0

    LABEL="$MODULE"
    OUTPUT="$(cd "$CWD" && "$PYTHON" -m unittest "$MODULE" 2>&1)"
    STATUS=$?
    ;;
  *.sh)
    case "$DIRNAME" in
      "$CWD/hooks"|"$CWD/hooks/test.hooks") ;;
      *) exit 0 ;;
    esac

    STEM="$(basename -- "$FILE_PATH" .sh)"
    case "$STEM" in
      test-*) HARNESS_NAME="$STEM" ;;
      *) HARNESS_NAME="test-$STEM" ;;
    esac
    HARNESS="$CWD/hooks/test.hooks/$HARNESS_NAME.sh"
    [ -f "$HARNESS" ] || exit 0

    LABEL="hooks/test.hooks/$HARNESS_NAME.sh"
    OUTPUT="$(bash "$HARNESS" 2>&1)"
    STATUS=$?
    ;;
  *)
    exit 0
    ;;
esac

if [ "$STATUS" -ne 0 ]; then
  printf '%s\n\nScoped test-impact hook: `%s` failed after editing %s.\n' \
    "$OUTPUT" "$LABEL" "$FILE_PATH" >&2
  exit 2
fi

exit 0
