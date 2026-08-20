#!/bin/bash
# Format/lint/type-check the single Python file Claude just touched, so a
# quality-gate failure surfaces at the edit that caused it instead of at the
# next `scripts/quality_gates.py --diff-base origin/main` run.
#
# Black is applied (not just checked) — the reformat is mechanical, so fixing
# it beats reporting it — and the reformat is still reported, because the file
# on disk no longer matches what the agent just wrote. Ruff and mypy need
# judgment, so they are reported only. mypy runs only for files listed in
# `[tool.mypy] files` (pyproject.toml), which stays the single source of truth
# for what is type-checked.

set -u

command -v jq >/dev/null 2>&1 || exit 0

INPUT="$(cat)" || exit 0
FILE_PATH="$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$PWD"
[ -n "$FILE_PATH" ] || exit 0

# Physical paths throughout, so the prefix match below holds: `git rev-parse`
# returns them, and a payload path may reach the tree through a symlink
# (/tmp -> /private/tmp on macOS).
physical() { (cd -- "$1" 2>/dev/null && pwd -P) || printf '%s' "$1"; }

# The root is the touched file's tree, not the session's: an agent rooted in
# the parent checkout that edits a file in a sibling worktree used to fall
# straight through the prefix match below and format nothing at all. Falls
# back to the payload's `.cwd`.
CWD="$(physical "$CWD")"
DIRNAME="$(physical "$(dirname -- "$FILE_PATH")")"
FILE_PATH="$DIRNAME/$(basename -- "$FILE_PATH")"
ROOT="$(git -C "$DIRNAME" rev-parse --show-toplevel 2>/dev/null)"
[ -n "$ROOT" ] || ROOT="$CWD"

case "$FILE_PATH" in
  "$ROOT"/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE_PATH" ] || exit 0

PYTHON="${SHANKS_FORMAT_PYTHON:-$ROOT/.venv/bin/python}"
command -v "$PYTHON" >/dev/null 2>&1 || exit 0

REL="${FILE_PATH#"$ROOT"/}"
REPORT=""

note() {
  REPORT="${REPORT}$1"$'\n'
}

if ! (cd "$ROOT" && "$PYTHON" -m black --check --quiet "$REL") >/dev/null 2>&1; then
  if OUTPUT="$(cd "$ROOT" && "$PYTHON" -m black --quiet "$REL" 2>&1)"; then
    note "black reformatted $REL — re-read it before editing again."
  else
    note "black failed on $REL:"$'\n'"$OUTPUT"
  fi
fi

if ! OUTPUT="$(cd "$ROOT" && "$PYTHON" -m ruff check "$REL" 2>&1)"; then
  note "ruff check failed on $REL:"$'\n'"$OUTPUT"
fi

# Read the TOML value rather than depending on how the list is laid out on
# lines. Parser errors stay fail-open like the old grep, while the full quality
# gate still checks the configured mypy files.
if (
  cd "$ROOT" &&
  "$PYTHON" -c '
import fnmatch
import sys
import tomllib

with open(sys.argv[1], "rb") as stream:
    files = tomllib.load(stream).get("tool", {}).get("mypy", {}).get("files", ())
if isinstance(files, str):
    files = (files,)
raise SystemExit(
    0 if any(fnmatch.fnmatchcase(sys.argv[2], pattern) for pattern in files) else 1
)
' "$ROOT/pyproject.toml" "$REL"
) >/dev/null 2>&1; then
  if ! OUTPUT="$(cd "$ROOT" && "$PYTHON" -m mypy "$REL" 2>&1)"; then
    note "mypy failed on $REL:"$'\n'"$OUTPUT"
  fi
fi

[ -n "$REPORT" ] || exit 0

printf 'Scoped quality hook:\n%s' "$REPORT" >&2
exit 2
