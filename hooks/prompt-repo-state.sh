#!/bin/bash
# Put the repository's current state in front of every prompt, so a session
# never starts blind about the branch it is on, what just landed, whether
# someone else's work is sitting in the tree, or whether this branch already
# has an open PR. `UserPromptSubmit` stdout becomes context for that turn.
#
# Deliberately cheap: everything but the PR lookup is local Git. The test
# suite stays out of it (~15s, and it would be paid on every prompt), and the
# one network call is cached per branch so a fast follow-up prompt reuses it.
#
# Advisory only, so it fails open everywhere: a missing tool, a non-repository
# directory, or a failed command prints nothing and exits 0. It must never
# exit non-zero — a non-zero `UserPromptSubmit` hook blocks the prompt itself.

set -u

PR_CACHE_MINUTES="${SHANKS_PROMPT_STATE_CACHE_MINUTES:-5}"
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

printf 'Repository state (%s):\n' "$(basename "$ROOT")"
printf -- '- Branch: %s\n' "$BRANCH"

# Local ref comparison only - no fetch, so this reflects the last fetch rather
# than the remote right now. Cheap and honest; the PR lookup below is the one
# place worth a network round trip.
UPSTREAM="$(git -C "$ROOT" rev-parse --abbrev-ref '@{upstream}' 2>/dev/null)"
if [ -n "$UPSTREAM" ]; then
  COUNTS="$(git -C "$ROOT" rev-list --left-right --count "$UPSTREAM...HEAD" 2>/dev/null)"
  BEHIND="${COUNTS%%	*}"
  AHEAD="${COUNTS##*	}"
  if [ -n "$COUNTS" ] && [ "$BEHIND$AHEAD" != "00" ]; then
    printf -- '- %s ahead, %s behind %s (as of the last fetch)\n' \
      "$AHEAD" "$BEHIND" "$UPSTREAM"
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

# The only network call, so it is cached per repository and branch. `find
# -mmin` is the portable freshness test (macOS and Linux both have it);
# `stat` would need a different flag on each.
if command -v gh >/dev/null 2>&1 && [ "$BRANCH" != "(detached HEAD)" ]; then
  CACHE_KEY="$(printf '%s@%s' "$ROOT" "$BRANCH" | tr -c 'A-Za-z0-9' '-')"
  CACHE="${TMPDIR:-/tmp}/shanks-prompt-state-$(id -u)-$CACHE_KEY"
  if [ -f "$CACHE" ] && [ -n "$(find "$CACHE" -mmin "-$PR_CACHE_MINUTES" 2>/dev/null)" ]; then
    cat "$CACHE"
  else
    PR="$(gh pr list --head "$BRANCH" --state open \
      --json number,title,url --jq '.[] | "- Open PR #\(.number): \(.title) (\(.url))"' \
      2>/dev/null)"
    if [ -z "$PR" ]; then
      PR="- No open PR for this branch."
    fi
    printf '%s\n' "$PR" > "$CACHE" 2>/dev/null
    printf '%s\n' "$PR"
  fi
fi

exit 0
