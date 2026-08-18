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

# Physical paths throughout, so the comparisons below hold: `git rev-parse`
# returns them, and a payload path may reach the tree through a symlink
# (/tmp -> /private/tmp on macOS).
physical() { (cd -- "$1" 2>/dev/null && pwd -P) || printf '%s' "$1"; }

# The root is the touched file's tree, not the session's: an agent rooted in
# the parent checkout that edits a file in a sibling worktree must run that
# worktree's tests, not the parent's. Falls back to the payload's `.cwd`.
CWD="$(physical "$CWD")"
DIRNAME="$(physical "$(dirname -- "$FILE_PATH")")"
FILE_PATH="$DIRNAME/$(basename -- "$FILE_PATH")"
ROOT="$(git -C "$DIRNAME" rev-parse --show-toplevel 2>/dev/null)"
[ -n "$ROOT" ] || ROOT="$CWD"

case "$FILE_PATH" in
  *.py)
    STEM="$(basename -- "$FILE_PATH" .py)"
    case "$STEM" in
      test_*)
        if [ "$DIRNAME" = "$ROOT/tests" ]; then
          MODULE="tests.$STEM"
        else
          MODULE="tests.test_$STEM"
        fi
        ;;
      *)
        MODULE="tests.test_$STEM"
        ;;
    esac

    TARGET="$ROOT/tests/${MODULE#tests.}.py"
    [ -f "$TARGET" ] || exit 0

    PYTHON="${SHANKS_TEST_IMPACT_PYTHON:-$ROOT/.venv/bin/python}"
    command -v "$PYTHON" >/dev/null 2>&1 || exit 0

    LABEL="$MODULE"
    OUTPUT="$(cd "$ROOT" && "$PYTHON" -m unittest "$MODULE" 2>&1)"
    STATUS=$?
    ;;
  *.sh)
    case "$DIRNAME" in
      "$ROOT/hooks"|"$ROOT/hooks/test.hooks") ;;
      *) exit 0 ;;
    esac

    STEM="$(basename -- "$FILE_PATH" .sh)"
    case "$STEM" in
      test-*) HARNESS_NAME="$STEM" ;;
      *) HARNESS_NAME="test-$STEM" ;;
    esac
    HARNESS="$ROOT/hooks/test.hooks/$HARNESS_NAME.sh"
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
