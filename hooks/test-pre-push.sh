#!/bin/bash
# Small regression harness for pre-push.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/pre-push"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/pass.py" <<'EOF'
import sys
sys.exit(0)
EOF
cat > "$TMP/fail.py" <<'EOF'
import sys
sys.exit(1)
EOF

passed=0
failed=0

check() {
  local expected="$1"
  local label="$2"
  local python_bin="$3"
  local gates_script="$4"
  local verdict

  if SHANKS_QUALITY_GATES_PYTHON="$python_bin" SHANKS_QUALITY_GATES_SCRIPT="$gates_script" \
    "$HOOK" >/dev/null 2>&1; then
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

check allow "gates pass" python3 "$TMP/pass.py"
check block "gates fail" python3 "$TMP/fail.py"
check allow "python missing (fail open)" "$TMP/no-such-python" "$TMP/fail.py"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
