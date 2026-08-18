#!/bin/bash
# Small regression harness for run-impacted-tests.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/../run-impacted-tests.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/tests" "$TMP/hooks/test.hooks" "$TMP/scripts"
: > "$TMP/tests/test_workspaces.py"

cat > "$TMP/hooks/test.hooks/test-widget.sh" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "$TMP/hooks/test.hooks/test-widget.sh"

cat > "$TMP/hooks/test.hooks/test-failing.sh" <<'EOF'
#!/bin/bash
echo "FAIL: sample harness failure" >&2
exit 1
EOF
chmod +x "$TMP/hooks/test.hooks/test-failing.sh"

cat > "$TMP/hooks/test.hooks/test-outside.sh" <<'EOF'
#!/bin/bash
echo "FAIL: should never run for a file outside hooks/" >&2
exit 1
EOF
chmod +x "$TMP/hooks/test.hooks/test-outside.sh"

# A sibling checkout: its own Git tree, holding a test module and a harness
# that exist nowhere in $TMP. Resolving from the session's `.cwd` finds
# neither and skips silently — the bug this guards.
SIBLING="$TMP/sibling"
mkdir -p "$SIBLING/tests" "$SIBLING/workflow" "$SIBLING/hooks/test.hooks"
git -C "$SIBLING" init -q 2>/dev/null
: > "$SIBLING/tests/test_sibling.py"
: > "$SIBLING/workflow/sibling.py"

cat > "$SIBLING/hooks/test.hooks/test-sibling.sh" <<'EOF'
#!/bin/bash
echo "FAIL: sibling harness failure" >&2
exit 1
EOF
chmod +x "$SIBLING/hooks/test.hooks/test-sibling.sh"

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

check allow "matching shell harness passes" "$TMP/hooks/widget.sh" "$TMP/python-pass"
check block "matching shell harness fails" "$TMP/hooks/failing.sh" "$TMP/python-pass"
check allow "no matching shell harness" "$TMP/hooks/no-such-hook.sh" "$TMP/python-pass"
check allow "editing the shell harness itself" "$TMP/hooks/test.hooks/test-widget.sh" "$TMP/python-pass"
check block "editing the shell harness itself, failing" "$TMP/hooks/test.hooks/test-failing.sh" "$TMP/python-pass"
check allow "extensionless git hook (no .sh match)" "$TMP/hooks/post-merge" "$TMP/python-pass"
check allow "shell file outside hooks/ is ignored" "$TMP/scripts/outside.sh" "$TMP/python-pass"

check block "python file in a sibling worktree, not the session cwd" \
  "$SIBLING/workflow/sibling.py" "$TMP/python-fail"
check block "shell file in a sibling worktree, not the session cwd" \
  "$SIBLING/hooks/sibling.sh" "$TMP/python-pass"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
