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

case "$FILE_PATH" in
  "$CWD"/*.py) ;;
  *) exit 0 ;;
esac
[ -f "$FILE_PATH" ] || exit 0

PYTHON="${SHANKS_FORMAT_PYTHON:-$CWD/.venv/bin/python}"
command -v "$PYTHON" >/dev/null 2>&1 || exit 0

REL="${FILE_PATH#"$CWD"/}"
REPORT=""

note() {
  REPORT="${REPORT}$1"$'\n'
}

if ! (cd "$CWD" && "$PYTHON" -m black --check --quiet "$REL") >/dev/null 2>&1; then
  if OUTPUT="$(cd "$CWD" && "$PYTHON" -m black --quiet "$REL" 2>&1)"; then
    note "black reformatted $REL — re-read it before editing again."
  else
    note "black failed on $REL:"$'\n'"$OUTPUT"
  fi
fi

if ! OUTPUT="$(cd "$CWD" && "$PYTHON" -m ruff check "$REL" 2>&1)"; then
  note "ruff check failed on $REL:"$'\n'"$OUTPUT"
fi

# ponytail: textual grep of pyproject.toml's `[tool.mypy] files` list rather
# than a TOML parse — a listed path is one quoted line there today. Parse it
# properly if that list ever gets globs or a second quoted-path list appears.
if grep -q "\"$REL\"," "$CWD/pyproject.toml" 2>/dev/null; then
  if ! OUTPUT="$(cd "$CWD" && "$PYTHON" -m mypy "$REL" 2>&1)"; then
    note "mypy failed on $REL:"$'\n'"$OUTPUT"
  fi
fi

[ -n "$REPORT" ] || exit 0

printf 'Scoped quality hook:\n%s' "$REPORT" >&2
exit 2
