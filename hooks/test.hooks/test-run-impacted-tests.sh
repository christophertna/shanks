#!/bin/bash
# Small regression harness for run-impacted-tests.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/../run-impacted-tests.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/tests"
: > "$TMP/tests/test_workspaces.py"

cat > "$TMP/python-pass" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$TMP/python-pass"

cat > "$TMP/python-fail" <<'EOF'
#!/bin/bash
echo "AssertionError: sample failure" >&2
exit 1
EOF
chmod +x "$TMP/python-fail"

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
  if printf '%s' "$json" | SHANKS_TEST_IMPACT_PYTHON="$python_bin" "$HOOK" >/dev/null 2>&1; then
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

check allow "matching module passes" "$TMP/workflow/workspaces.py" "$TMP/python-pass"
check block "matching module fails" "$TMP/workflow/workspaces.py" "$TMP/python-fail"
check allow "no matching test module" "$TMP/workflow/adapters.py" "$TMP/python-fail"
check allow "editing the test module itself" "$TMP/tests/test_workspaces.py" "$TMP/python-pass"
check block "editing the test module itself, failing" "$TMP/tests/test_workspaces.py" "$TMP/python-fail"
check allow "non-python file" "$TMP/README.md" "$TMP/python-fail"
check allow "python interpreter missing (fail open)" "$TMP/workflow/workspaces.py" "$TMP/no-such-python"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
