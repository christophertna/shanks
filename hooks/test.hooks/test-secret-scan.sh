#!/bin/bash
# Small regression harness for secret-scan.sh.
#
# The fake token below is assembled at runtime (not a literal in this file)
# so that saving this test doesn't itself trip the guard it's testing.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD="$SCRIPT_DIR/../secret-scan.sh"
FAKE_TOKEN="ghp_$(printf 'wF9k2Lm8Qx3Vn7Rt4Yc6Zb1Ad5Ef0Gh2Ij9K')"
passed=0
failed=0

check() {
  local expected="$1"
  local field="$2"
  local value="$3"
  local result verdict

  if printf '%s' "$(jq -cn --arg path "notes.txt" --arg field "$field" --arg value "$value" \
    '{tool_input: ({file_path: $path} + {($field): $value})}')" \
    | "$GUARD" >/dev/null 2>&1; then
    verdict="allow"
  else
    verdict="block"
  fi
  if [ "$verdict" = "$expected" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL expected=%s got=%s: %s=%s\n' "$expected" "$verdict" "$field" "$value"
  fi
}

check allow content 'just a normal line of code'
check allow new_string 'const greeting = "hello"'
check block content "token = \"$FAKE_TOKEN\""
check block new_string "token = \"$FAKE_TOKEN\""

if printf '%s' "$(jq -cn '{tool_input: {file_path: "notes.txt"}}')" | "$GUARD" >/dev/null 2>&1; then
  passed=$((passed + 1))
else
  failed=$((failed + 1))
  printf 'FAIL expected=allow got=block: no content field at all\n'
fi

# Bash tool calls have no file_path at all - only a command field.
check_bash() {
  local expected="$1"
  local command="$2"
  local verdict

  if printf '%s' "$(jq -cn --arg cmd "$command" '{tool_input: {command: $cmd}}')" \
    | "$GUARD" >/dev/null 2>&1; then
    verdict="allow"
  else
    verdict="block"
  fi
  if [ "$verdict" = "$expected" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL expected=%s got=%s: command=%s\n' "$expected" "$verdict" "$command"
  fi
}

check_bash allow 'git status'
check_bash block "echo \"$FAKE_TOKEN\" >> config.py"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
