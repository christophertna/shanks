#!/bin/bash
# Small regression harness for format-touched.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/../format-touched.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/workflow" "$TMP/tests"
: > "$TMP/workflow/nodes.py"
: > "$TMP/tests/test_nodes.py"
: > "$TMP/README.md"
: > "$TMP/outside.py"

cat > "$TMP/pyproject.toml" <<'EOF'
[tool.mypy]
files = ["workflow/nodes.py"]
EOF

# A sibling checkout: its own Git tree, with its own `[tool.mypy] files` list.
# Resolving from the session's `.cwd` never matches this path at all — the bug
# this guards.
SIBLING="$TMP/sibling"
mkdir -p "$SIBLING/workflow"
git -C "$SIBLING" init -q 2>/dev/null
: > "$SIBLING/workflow/sibling.py"
cat > "$SIBLING/pyproject.toml" <<'EOF'
[tool.mypy]
files = ["workflow/sibling.py"]
EOF

# Stub interpreters: $1=-m, $2=tool, rest are that tool's arguments. The hook's
# TOML probe uses $1=-c, $3=pyproject.toml, and $4=the touched relative path.
# $TMP/fail-<tool> makes the matching tool exit non-zero; "black --check"
# fails via $TMP/fail-black-check so the reformat pass can still succeed.
cat > "$TMP/python" <<EOF
#!/bin/bash
if [ "\$1" = "-c" ]; then
  case "\$4" in
    workflow/nodes.py|workflow/sibling.py) exit 0 ;;
    *) exit 1 ;;
  esac
fi
TOOL="\$2"
if [ "\$TOOL" = "black" ] && [ "\$3" = "--check" ]; then
  [ -f "$TMP/fail-black-check" ] && exit 1
  exit 0
fi
if [ -f "$TMP/fail-\$TOOL" ]; then
  echo "\$TOOL: sample failure" >&2
  exit 1
fi
exit 0
EOF
chmod +x "$TMP/python"

passed=0
failed=0

check() {
  local expected="$1"
  local label="$2"
  local file_path="$3"
  local python_bin="$4"
  local json verdict

  json="$(jq -cn --arg file "$file_path" --arg cwd "$TMP" \
    '{tool_input:{file_path:$file},cwd:$cwd}')"
  if printf '%s' "$json" | SHANKS_FORMAT_PYTHON="$python_bin" "$HOOK" >/dev/null 2>&1; then
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

check allow "clean python file" "$TMP/workflow/nodes.py" "$TMP/python"

: > "$TMP/fail-black-check"
check block "black reformatted the file" "$TMP/workflow/nodes.py" "$TMP/python"
rm -f "$TMP/fail-black-check"

: > "$TMP/fail-ruff"
check block "ruff reports a lint error" "$TMP/workflow/nodes.py" "$TMP/python"
rm -f "$TMP/fail-ruff"

: > "$TMP/fail-mypy"
check block "mypy fails on a type-checked file" "$TMP/workflow/nodes.py" "$TMP/python"
check allow "mypy skipped for a file outside [tool.mypy] files" \
  "$TMP/tests/test_nodes.py" "$TMP/python"
rm -f "$TMP/fail-mypy"

: > "$TMP/fail-ruff"
check allow "non-python file" "$TMP/README.md" "$TMP/python"
check allow "python file outside the project directory" "/tmp/not-in-cwd.py" "$TMP/python"
check allow "deleted or missing file" "$TMP/workflow/gone.py" "$TMP/python"
check allow "python interpreter missing (fail open)" \
  "$TMP/workflow/nodes.py" "$TMP/no-such-python"
rm -f "$TMP/fail-ruff"

: > "$TMP/fail-mypy"
check block "python file in a sibling worktree, not the session cwd" \
  "$SIBLING/workflow/sibling.py" "$TMP/python"
rm -f "$TMP/fail-mypy"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
