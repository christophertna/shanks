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

# A `gh` that reports one open PR and a red `main`, and one that fails the way
# an unauthenticated or offline `gh` does. The hook must survive both. Each
# subcommand emits the line the real `--jq` template would have produced.
cat > "$FAKE_BIN/gh" <<'EOF'
#!/bin/bash
case "$1 $2" in
  "pr list") echo "- Open PR #123: Sample title (https://example.test/pr/123)" ;;
  "run list") echo "- main CI: failure (Tests)" ;;
esac
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
expect_contains "reports main's CI status" "- main CI: failure (Tests)"

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
expect_contains "cached CI line survives too" "main CI: failure"
expect_exit_zero "broken gh still exits zero"

rm -rf "${CACHE_DIR:?}"/*
run "$REPO"
expect_exit_zero "broken gh with a cold cache exits zero"
expect_contains "broken gh reports no open PR" "No open PR for this branch"
expect_missing "broken gh reports no CI line" "main CI"
expect_contains "broken gh still reports the branch" "- Branch: main"

# Upstream drift and fetch freshness get their own repository: the runs above
# launched background fetches against a remoteless `$REPO`, and one of those
# can still be in flight (or land a stamp) once a remote appears, which is
# exactly the kind of straggler these checks must not see. `push -u` sets the
# upstream without writing FETCH_HEAD, so the first look is a genuine
# "never fetched".
UP="$TMP/upstream"
REMOTE="$TMP/remote.git"
mkdir -p "$UP"
git init -q --bare -b main "$REMOTE" 2>/dev/null
git -C "$UP" init -q -b main 2>/dev/null
git -C "$UP" config user.email "tests@example.com"
git -C "$UP" config user.name "Tests"
echo "one" > "$UP/README.md"
git -C "$UP" add README.md
git -C "$UP" commit -qm "add readme"
git -C "$UP" remote add origin "$REMOTE"
git -C "$UP" push -q -u origin main

# FETCH_MINUTES=0 disables the background fetch, so these read a fixed state.
run "$UP" SHANKS_PROMPT_STATE_FETCH_MINUTES=0
expect_contains "reports zero drift instead of staying silent" \
  "- 0 ahead, 0 behind origin/main"
expect_contains "reports a never-fetched checkout" \
  "(no successful fetch on record)"

git -C "$UP" fetch -q origin
run "$UP" SHANKS_PROMPT_STATE_FETCH_MINUTES=0
expect_contains "reports a fresh fetch age" "(last fetch: just now)"

# A failed fetch truncates FETCH_HEAD, which must not read as a fresh fetch -
# and no stamp from a successful fetch of our own exists yet to fall back to.
: > "$UP/.git/FETCH_HEAD"
run "$UP" SHANKS_PROMPT_STATE_FETCH_MINUTES=0
expect_contains "a failed fetch is not reported as fresh" \
  "(no successful fetch on record)"
git -C "$UP" fetch -q origin

# Both `stat` spellings, pinned on whichever platform this runs on: only one of
# them is exercised for real here, and the GNU one is a trap - `stat -f` there
# means "filesystem status" and succeeds, printing a mount point instead of
# failing the way BSD-first fallback ordering assumes.
NOW="$(date +%s)"
for flavor in gnu bsd; do
  mkdir -p "$TMP/stat-$flavor"
  if [ "$flavor" = gnu ]; then
    printf '#!/bin/bash\ncase "$1" in\n  -c) echo %s ;;\n  -f) echo / ;;\nesac\n' \
      "$NOW" > "$TMP/stat-$flavor/stat"
  else
    printf '#!/bin/bash\ncase "$1" in\n  -c) exit 1 ;;\n  -f) echo %s ;;\nesac\n' \
      "$NOW" > "$TMP/stat-$flavor/stat"
  fi
  chmod +x "$TMP/stat-$flavor/stat"
  run "$UP" SHANKS_PROMPT_STATE_FETCH_MINUTES=0 \
    PATH="$TMP/stat-$flavor:$FAKE_BIN:$PATH"
  expect_contains "reads the fetch age with $flavor stat" "(last fetch: just now)"
done

echo "two" >> "$UP/README.md"
git -C "$UP" add README.md
git -C "$UP" commit -qm "second commit"
run "$UP" SHANKS_PROMPT_STATE_FETCH_MINUTES=0
expect_contains "reports the ahead count" "- 1 ahead, 0 behind origin/main"

# The background fetch itself: it must refresh FETCH_HEAD without the hook
# waiting on it, and must not run again inside the debounce window.
rm -f "$UP/.git/FETCH_HEAD"
run "$UP"
expect_exit_zero "background fetch still exits zero"
i=0
while [ ! -f "$UP/.git/FETCH_HEAD" ] && [ "$i" -lt 100 ]; do
  sleep 0.1
  i=$((i + 1))
done
if [ -f "$UP/.git/FETCH_HEAD" ]; then
  record yes "background fetch refreshes FETCH_HEAD"
else
  record no "background fetch refreshes FETCH_HEAD"
fi

rm -f "$UP/.git/FETCH_HEAD"
run "$UP"
sleep 0.5
if [ -f "$UP/.git/FETCH_HEAD" ]; then
  record no "debounce skips the second fetch"
else
  record yes "debounce skips the second fetch"
fi

# FETCH_HEAD is gone, as it effectively is mid-fetch while git has truncated it
# but not yet rewritten it, so the age has to come from the stamp the earlier
# successful background fetch left behind.
run "$UP" SHANKS_PROMPT_STATE_FETCH_MINUTES=0
expect_contains "falls back to the fetch stamp" "(last fetch: just now)"

# The prompt that launches a fetch must report the age from before it started,
# not the FETCH_HEAD its own fetch truncates on the way out. A real fetch of
# this local remote finishes too fast to leave that window open, so `git fetch`
# is stubbed to truncate and then hang the way a network fetch does; it also
# fails, so no stamp is written and only the pre-launch read can save the line.
REAL_GIT="$(command -v git)"
mkdir -p "$TMP/slow-git"
cat > "$TMP/slow-git/git" <<EOF
#!/bin/bash
for a in "\$@"; do
  if [ "\$a" = fetch ]; then
    : > "$UP/.git/FETCH_HEAD"
    sleep 2
    exit 1
  fi
done
exec "$REAL_GIT" "\$@"
EOF
chmod +x "$TMP/slow-git/git"
git -C "$UP" fetch -q origin
rm -f "$CACHE_DIR"/*-fetch-* "$CACHE_DIR"/*-fetched-*
run "$UP" PATH="$TMP/slow-git:$FAKE_BIN:$PATH"
expect_missing "launching a fetch does not erase the age it reports" \
  "no successful fetch on record"

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
