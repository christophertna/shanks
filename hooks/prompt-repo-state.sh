#!/bin/bash
# Put the repository's current state in front of every prompt, so a session
# never starts blind about the branch it is on, what just landed, whether
# someone else's work is sitting in the tree, or whether this branch already
# has an open PR. `UserPromptSubmit` stdout becomes context for that turn.
#
# Deliberately cheap: everything but the two `gh` lookups is local Git, and
# those are cached per branch so a fast follow-up prompt reuses them. The fetch
# that keeps the ahead/behind counts honest is debounced and backgrounded, so
# no prompt ever waits on it. The test suite stays out of it entirely (~15s,
# and it would be paid on every prompt).
#
# Advisory only, so it fails open everywhere: a missing tool, a non-repository
# directory, or a failed command prints nothing and exits 0. It must never
# exit non-zero — a non-zero `UserPromptSubmit` hook blocks the prompt itself.

set -u

PR_CACHE_MINUTES="${SHANKS_PROMPT_STATE_CACHE_MINUTES:-5}"
FETCH_MINUTES="${SHANKS_PROMPT_STATE_FETCH_MINUTES:-5}"
LOG_COUNT="${SHANKS_PROMPT_STATE_COMMITS:-5}"
DIRTY_COUNT=5

command -v git >/dev/null 2>&1 || exit 0

CWD=""
if command -v jq >/dev/null 2>&1; then
  INPUT="$(cat)" || exit 0
  CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
fi
[ -n "$CWD" ] || CWD="$PWD"

ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -n "$ROOT" ] || exit 0

BRANCH="$(git -C "$ROOT" branch --show-current 2>/dev/null)"
[ -n "$BRANCH" ] || BRANCH="(detached HEAD)"

CACHE_BASE="${TMPDIR:-/tmp}/shanks-prompt-state-$(id -u)"
REPO_KEY="$(printf '%s' "$ROOT" | tr -c 'A-Za-z0-9' '-')"

# One debounced background fetch, so the counts below reflect a fetch from a
# few minutes ago rather than whenever someone last fetched by hand. Detached
# and discarded: the prompt must never wait on the network, and this run's
# counts are still the previous fetch's. `SHANKS_PROMPT_STATE_FETCH_MINUTES=0`
# turns it off.
if [ "$FETCH_MINUTES" -gt 0 ] 2>/dev/null; then
  MARKER="$CACHE_BASE-fetch-$REPO_KEY"
  if [ ! -f "$MARKER" ] ||
     [ -z "$(find "$MARKER" -mmin "-$FETCH_MINUTES" 2>/dev/null)" ]; then
    : > "$MARKER" 2>/dev/null
    ( git -C "$ROOT" fetch --quiet --no-tags >/dev/null 2>&1 </dev/null & )
  fi
fi

# Age of the last fetch, so a "0 behind" line is never mistaken for "up to
# date". A *failed* fetch truncates FETCH_HEAD to zero bytes rather than
# leaving it alone, so `-s` is what separates "fetched" from "tried and
# couldn't" - and reporting the latter as no fetch at all errs toward "you may
# be stale", which is the safe direction here. `stat` spells mtime differently
# on BSD (`-f %m`) and GNU (`-c %Y`), and the two are not safely ordered by
# exit status: GNU's `-f` means "filesystem status", so `stat -f %m` *succeeds*
# on Linux and prints the mount point. Hence trying one and re-trying on
# anything that is not an epoch, rather than on failure.
fetch_age() {
  local head mtime secs
  head="$(git -C "$ROOT" rev-parse --absolute-git-dir 2>/dev/null)/FETCH_HEAD"
  mtime=""
  if [ -s "$head" ]; then
    mtime="$(stat -c %Y "$head" 2>/dev/null)"
    case "$mtime" in
      ''|*[!0-9]*) mtime="$(stat -f %m "$head" 2>/dev/null)" ;;
    esac
  fi
  case "$mtime" in
    ''|*[!0-9]*) printf 'no successful fetch on record'; return ;;
  esac
  secs=$(( $(date +%s) - mtime ))
  printf 'last fetch: '
  if [ "$secs" -lt 120 ]; then printf 'just now'
  elif [ "$secs" -lt 7200 ]; then printf '%sm ago' "$(( secs / 60 ))"
  elif [ "$secs" -lt 172800 ]; then printf '%sh ago' "$(( secs / 3600 ))"
  else printf '%sd ago' "$(( secs / 86400 ))"
  fi
}

printf 'Repository state (%s):\n' "$(basename "$ROOT")"
printf -- '- Branch: %s\n' "$BRANCH"

# Local ref comparison only - the fetch above is asynchronous, so this reflects
# the last completed fetch rather than the remote right now. Printed even when
# both counts are zero: "0 behind" with a stale fetch age is exactly the state
# worth seeing.
UPSTREAM="$(git -C "$ROOT" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)"
if [ -n "$UPSTREAM" ]; then
  COUNTS="$(git -C "$ROOT" rev-list --left-right --count "$UPSTREAM...HEAD" 2>/dev/null)"
  BEHIND="${COUNTS%%	*}"
  AHEAD="${COUNTS##*	}"
  if [ -n "$COUNTS" ]; then
    printf -- '- %s ahead, %s behind %s (%s)\n' \
      "$AHEAD" "$BEHIND" "$UPSTREAM" "$(fetch_age)"
  fi
fi

DIRTY="$(git -C "$ROOT" status --porcelain 2>/dev/null)"
if [ -n "$DIRTY" ]; then
  TOTAL="$(printf '%s\n' "$DIRTY" | wc -l | tr -d ' ')"
  printf -- '- Uncommitted changes (%s), which may be another agent'"'"'s:\n' "$TOTAL"
  printf '%s\n' "$DIRTY" | head -n "$DIRTY_COUNT" | sed 's/^/    /'
  [ "$TOTAL" -gt "$DIRTY_COUNT" ] && printf '    ... and %s more\n' \
    "$((TOTAL - DIRTY_COUNT))"
else
  printf -- '- Working tree clean\n'
fi

printf -- '- Recent commits:\n'
git -C "$ROOT" log --oneline -n "$LOG_COUNT" 2>/dev/null | sed 's/^/    /'

# The `gh` calls, cached together per repository and branch. `find -mmin` is
# the portable freshness test (macOS and Linux both have it).
if command -v gh >/dev/null 2>&1 && [ "$BRANCH" != "(detached HEAD)" ]; then
  CACHE="$CACHE_BASE-$REPO_KEY-$(printf '%s' "$BRANCH" | tr -c 'A-Za-z0-9' '-')"
  if [ -f "$CACHE" ] && [ -n "$(find "$CACHE" -mmin "-$PR_CACHE_MINUTES" 2>/dev/null)" ]; then
    cat "$CACHE"
  else
    GH_LINES="$(gh pr list --head "$BRANCH" --state open \
      --json number,title,url --jq '.[] | "- Open PR #\(.number): \(.title) (\(.url))"' \
      2>/dev/null)"
    if [ -z "$GH_LINES" ]; then
      GH_LINES="- No open PR for this branch."
    fi
    # Whether `main` is green is invisible from local refs, and branching off a
    # red `main` is the incident this exists to surface.
    CI="$(gh run list --branch main --limit 1 \
      --json conclusion,status,workflowName \
      --jq '.[] | "- main CI: \(if .conclusion == "" then .status else .conclusion end) (\(.workflowName))"' \
      2>/dev/null)"
    if [ -n "$CI" ]; then
      GH_LINES="$GH_LINES
$CI"
    fi
    printf '%s\n' "$GH_LINES" > "$CACHE" 2>/dev/null
    printf '%s\n' "$GH_LINES"
  fi
fi

exit 0
