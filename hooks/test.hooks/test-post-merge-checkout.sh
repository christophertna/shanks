#!/bin/bash
# Small regression harness for post-merge/post-checkout.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POST_MERGE="$SCRIPT_DIR/../post-merge"
POST_CHECKOUT="$SCRIPT_DIR/../post-checkout"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# A fake `graphify` that records each invocation instead of doing real work.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/graphify" <<'EOF'
#!/bin/sh
echo "$*" >> "$GRAPHIFY_LOG"
EOF
chmod +x "$TMP/bin/graphify"
GRAPHIFY_LOG="$TMP/graphify.log"
export GRAPHIFY_LOG

GIT_ONLY_PATH="$(dirname "$(command -v git)")"
WITH_GRAPHIFY_PATH="$TMP/bin:$GIT_ONLY_PATH"

passed=0
failed=0

check() {
  local label="$1"
  local expected_calls="$2"
  shift 2

  : > "$GRAPHIFY_LOG"
  "$@" >/dev/null 2>&1
  local status=$?
  local calls
  calls="$(wc -l < "$GRAPHIFY_LOG" | tr -d ' ')"

  if [ "$status" -ne 0 ]; then
    failed=$((failed + 1))
    printf 'FAIL exit=%s: %s\n' "$status" "$label"
  elif [ "$calls" != "$expected_calls" ]; then
    failed=$((failed + 1))
    printf 'FAIL expected %s graphify call(s), got %s: %s\n' \
      "$expected_calls" "$calls" "$label"
  else
    passed=$((passed + 1))
  fi
}

check "post-checkout same SHA is a no-op skip" 0 \
  env PATH="$WITH_GRAPHIFY_PATH" "$POST_CHECKOUT" abc123 abc123 1

check "post-checkout different SHA runs graphify update" 1 \
  env PATH="$WITH_GRAPHIFY_PATH" "$POST_CHECKOUT" abc123 def456 1

check "post-merge without graphify on PATH is a no-op" 0 \
  env PATH="$GIT_ONLY_PATH" "$POST_MERGE"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
