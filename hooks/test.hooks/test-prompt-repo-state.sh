#!/bin/bash
# Small regression harness for prompt-repo-state.sh.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK="$SCRIPT_DIR/../prompt-repo-state.sh"
# Absolute, so the empty-PATH check below can still start a shell.
BASH_BIN="$(command -v bash)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CACHE_DIR="$TMP/cache"
FAKE_BIN="$TMP/bin"
mkdir -p "$CACHE_DIR" "$FAKE_BIN"

# A `gh` that reports one open PR, and one that fails the way an unauthenticated
# or offline `gh` does. The hook must survive both.
cat > "$FAKE_BIN/gh" <<'EOF'
#!/bin/bash
echo "- Open PR #123: Sample title (https://example.test/pr/123)"
EOF
chmod +x "$FAKE_BIN/gh"

cat > "$TMP/gh-broken" <<'EOF'
#!/bin/bash
echo "gh: could not authenticate" >&2
exit 1
EOF
chmod +x "$TMP/gh-broken"

REPO="$TMP/repo"
mkdir -p "$REPO"
git -C "$REPO" init -q -b main 2>/dev/null
git -C "$REPO" config user.email "tests@example.com"
git -C "$REPO" config user.name "Tests"
echo "one" > "$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -qm "add readme"
echo "two" >> "$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -qm "extend readme"

PLAIN="$TMP/not-a-repo"
mkdir -p "$PLAIN"

passed=0
failed=0
OUTPUT=""
STATUS=0

run() {
  # Runs the hook from an unrelated directory, so anything it reports had to
  # come from the payload's `.cwd` rather than from where it happened to run.
  local payload_cwd="$1"
  shift
  OUTPUT="$(cd "$TMP" && printf '{"cwd":"%s"}' "$payload_cwd" |
    env PATH="$FAKE_BIN:$PATH" TMPDIR="$CACHE_DIR" "$@" bash "$HOOK" 2>/dev/null)"
  STATUS=$?
}

record() {
  local ok="$1"
  local label="$2"
  if [ "$ok" = "yes" ]; then
    passed=$((passed + 1))
  else
    failed=$((failed + 1))
    printf 'FAIL %s\n' "$label"
  fi
}

expect_contains() {
  local label="$1"
  local needle="$2"
  case "$OUTPUT" in
    *"$needle"*) record yes "$label" ;;
    *) record no "$label (missing: $needle)" ;;
  esac
}

expect_missing() {
  local label="$1"
  local needle="$2"
  case "$OUTPUT" in
    *"$needle"*) record no "$label (unexpected: $needle)" ;;
    *) record yes "$label" ;;
  esac
}

expect_exit_zero() {
  # A non-zero UserPromptSubmit hook blocks the prompt, so every path must
  # exit 0 - this is the check that keeps an advisory hook advisory.
  if [ "$STATUS" -eq 0 ]; then
    record yes "$1"
  else
    record no "$1 (exit $STATUS)"
  fi
}

run "$REPO"
expect_exit_zero "clean repository exits zero"
expect_contains "reports the current branch" "- Branch: main"
expect_contains "reports a clean tree" "- Working tree clean"
expect_contains "reports recent commits" "extend readme"
expect_contains "reports the older commit too" "add readme"
expect_contains "reports the open PR" "Open PR #123"

echo "dirty" >> "$REPO/README.md"
: > "$REPO/untracked.txt"
run "$REPO"
expect_contains "reports uncommitted changes" "Uncommitted changes (2)"
expect_contains "lists the modified file" "README.md"
expect_contains "lists the untracked file" "untracked.txt"
expect_missing "clean line is gone once dirty" "Working tree clean"

for extra in a b c d e f; do : > "$REPO/extra-$extra.txt"; done
run "$REPO"
expect_contains "truncates a long dirty list" "... and 3 more"
git -C "$REPO" checkout -q -- README.md
rm -f "$REPO"/untracked.txt "$REPO"/extra-*.txt

# The PR line is cached per branch: a broken `gh` after a good one still
# reports the cached PR rather than paying the failure.
run "$REPO"
expect_contains "cached PR line survives" "Open PR #123"
cp "$TMP/gh-broken" "$FAKE_BIN/gh"
run "$REPO"
expect_contains "broken gh reuses the cache" "Open PR #123"
expect_exit_zero "broken gh still exits zero"

rm -rf "${CACHE_DIR:?}"/*
run "$REPO"
expect_exit_zero "broken gh with a cold cache exits zero"
expect_contains "broken gh reports no open PR" "No open PR for this branch"
expect_contains "broken gh still reports the branch" "- Branch: main"

run "$PLAIN"
expect_exit_zero "non-repository directory exits zero"
expect_missing "non-repository directory says nothing" "Repository state"

OUTPUT="$(cd "$TMP" && printf '{"cwd":"%s"}' "$REPO" |
  env PATH="/nonexistent" "$BASH_BIN" "$HOOK" 2>/dev/null)"
STATUS=$?
expect_exit_zero "missing git exits zero"
expect_missing "missing git says nothing" "Repository state"

git -C "$REPO" checkout -q --detach
run "$REPO"
expect_exit_zero "detached HEAD exits zero"
expect_contains "detached HEAD is reported" "(detached HEAD)"

printf 'passed: %s, failed: %s\n' "$passed" "$failed"
[ "$failed" -eq 0 ]
