#!/bin/bash
# Refresh the graphify knowledge graph after every Write/Edit. AST-only
# (`graphify update`), so no LLM/API cost. Runs in the background so it never
# blocks the edit; a lockdir debounces overlapping runs from rapid edits.

set -u

command -v graphify >/dev/null 2>&1 || exit 0

INPUT="$(cat)"
CWD="$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)"
[ -n "$CWD" ] || CWD="$PWD"
[ -f "$CWD/graphify-out/graph.json" ] || exit 0

LOCK="$CWD/graphify-out/.update.lock"
mkdir "$LOCK" 2>/dev/null || exit 0

(cd "$CWD" && graphify update . >/dev/null 2>&1; rmdir "$LOCK" 2>/dev/null) &
disown
exit 0
