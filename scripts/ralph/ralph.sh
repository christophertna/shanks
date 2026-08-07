#!/bin/bash
# Ralph Wiggum - Long-running AI agent loop
# Usage: ./ralph.sh [--project-dir path] [--run-dir path] [--tool claude|codex] [--skill skill-name|--no-skill] [max_iterations]

set -e
set -o pipefail

# Parse arguments
TOOL="codex"
SKILL_NAME="ponytail"
TARGET_DIR_ARG=""
RUN_DIR_ARG=""
GRAPH_ITEM_ID=""
GRAPH_INSTRUCTIONS=""
MAX_ITERATIONS=10

while [[ $# -gt 0 ]]; do
  case $1 in
    --tool)
      TOOL="$2"
      shift 2
      ;;
    --tool=*)
      TOOL="${1#*=}"
      shift
      ;;
    --project-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --project-dir requires a path."
        exit 1
      fi
      TARGET_DIR_ARG="$2"
      shift 2
      ;;
    --project-dir=*)
      TARGET_DIR_ARG="${1#*=}"
      shift
      ;;
    --run-dir)
      if [[ $# -lt 2 ]]; then
        echo "Error: --run-dir requires a path."
        exit 1
      fi
      RUN_DIR_ARG="$2"
      shift 2
      ;;
    --run-dir=*)
      RUN_DIR_ARG="${1#*=}"
      shift
      ;;
    --skill)
      if [[ $# -lt 2 ]]; then
        echo "Error: --skill requires a skill name."
        exit 1
      fi
      SKILL_NAME="$2"
      shift 2
      ;;
    --skill=*)
      SKILL_NAME="${1#*=}"
      shift
      ;;
    --no-skill)
      SKILL_NAME=""
      shift
      ;;
    --graph-instructions)
      if [[ $# -lt 2 ]]; then
        echo "Error: --graph-instructions requires text."
        exit 1
      fi
      GRAPH_INSTRUCTIONS="$2"
      shift 2
      ;;
    --graph-item-id)
      if [[ $# -lt 2 ]]; then
        echo "Error: --graph-item-id requires an item id."
        exit 1
      fi
      GRAPH_ITEM_ID="$2"
      shift 2
      ;;
    --graph-item-id=*)
      GRAPH_ITEM_ID="${1#*=}"
      shift
      ;;
    --graph-instructions=*)
      GRAPH_INSTRUCTIONS="${1#*=}"
      shift
      ;;
    *)
      # Assume it's max_iterations if it's a number
      if [[ "$1" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS="$1"
      fi
      shift
      ;;
  esac
done

# Validate tool choice
if [[ "$TOOL" != "claude" && "$TOOL" != "codex" ]]; then
  echo "Error: Invalid tool '$TOOL'. Must be 'claude' or 'codex'."
  exit 1
fi
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -z "$TARGET_DIR_ARG" ]; then
  TARGET_DIR="$BASE_DIR"
elif [[ "$TARGET_DIR_ARG" = /* ]]; then
  TARGET_DIR="$TARGET_DIR_ARG"
else
  TARGET_DIR="$BASE_DIR/$TARGET_DIR_ARG"
fi
if ! TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd)"; then
  echo "Error: Project directory does not exist: $TARGET_DIR_ARG"
  exit 1
fi
cd "$TARGET_DIR"
export RALPH_BASE_DIR="$BASE_DIR"
export RALPH_PROJECT_DIR="$TARGET_DIR"
if [ -z "$RUN_DIR_ARG" ]; then
  RUN_DIR="$SCRIPT_DIR"
elif [[ "$RUN_DIR_ARG" = /* ]]; then
  RUN_DIR="$RUN_DIR_ARG"
else
  RUN_DIR="$BASE_DIR/$RUN_DIR_ARG"
fi
if ! mkdir -p "$RUN_DIR"; then
  echo "Error: Could not create run directory: $RUN_DIR"
  exit 1
fi
export RALPH_RUN_DIR="$RUN_DIR"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
METADATA_FILE="$SCRIPT_DIR/metadata.txt"
ARCHIVE_DIR="$SCRIPT_DIR/archive"
LAST_BRANCH_FILE="$SCRIPT_DIR/.last-branch"
if [ -n "$RUN_DIR_ARG" ]; then
  PRD_FILE="$RUN_DIR/prd.json"
  PROGRESS_FILE="$RUN_DIR/progress.txt"
  METADATA_FILE="$RUN_DIR/metadata.txt"
  ARCHIVE_DIR="$RUN_DIR/archive"
  LAST_BRANCH_FILE="$RUN_DIR/.last-branch"
fi
export RALPH_PRD_FILE="$PRD_FILE"

resolve_skill_file() {
  local skill_name="$1"
  local candidate

  for candidate in \
    "$TARGET_DIR/.agents/skills/$skill_name/SKILL.md" \
    "$TARGET_DIR/.claude/skills/$skill_name/SKILL.md" \
    "$TARGET_DIR/skills/$skill_name/SKILL.md" \
    "$BASE_DIR/.agents/skills/$skill_name/SKILL.md" \
    "$BASE_DIR/.claude/skills/$skill_name/SKILL.md" \
    "$BASE_DIR/skills/$skill_name/SKILL.md"; do
    if [ -f "$candidate" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

SKILL_FILE=""
if [ -n "$SKILL_NAME" ]; then
  if [[ ! "$SKILL_NAME" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Error: Invalid skill name '$SKILL_NAME'."
    exit 1
  fi
  SKILL_FILE="$(resolve_skill_file "$SKILL_NAME" || true)"
  if [ -z "$SKILL_FILE" ]; then
    echo "Error: Missing project-local skill '$SKILL_NAME'."
    echo "Expected it under the target or base directory's .agents/skills/, .claude/skills/, or skills/."
    exit 1
  fi
fi

run_agent() {
  local prompt_file="$1"
  shift

  {
    printf '# Ralph workspace\n\n'
    printf 'Base engine directory: %s\n' "$BASE_DIR"
    printf 'Target project directory: %s\n' "$TARGET_DIR"
    printf 'Edit files under the target project directory. Ralph prompts, PRD, progress, and metadata remain in the base engine directory.\n\n'
    printf '# Pre-existing local changes\n\n'
    if [ -n "${BEFORE_FILES:-}" ]; then
      printf '%s\n' "$BEFORE_FILES"
    else
      printf '(none)\n'
    fi
    printf '\nLeave these files unstaged and uncommitted unless only the current story hunks can be staged safely.\n\n'
    if [ -n "$GRAPH_INSTRUCTIONS" ]; then
      printf '# Graph workflow context\n\n%s\n\n' "$GRAPH_INSTRUCTIONS"
    fi
    if [ -n "$SKILL_FILE" ]; then
      printf '# Project skill: %s\n\n' "$SKILL_NAME"
      printf 'Apply this skill during the Ralph iteration. Read it before making changes.\n\n'
      cat "$SKILL_FILE"
      printf '\n\n'
    fi
    printf '# Ralph iteration instructions\n\n'
    cat "$prompt_file"
  } | "$@" 2>&1
}

sanitize_metadata_field() {
  printf '%s' "$1" | tr '\r\n\t' '   '
}

initialize_metadata_file() {
  if [ ! -f "$METADATA_FILE" ]; then
    {
      echo "# Ralph Metadata"
      echo "# One tab-separated record per PRD item; files_touched is cumulative."
      printf 'story_id\ttitle\tattempts_count\tlast_error\tassigned_model\tfiles_touched\n'
    } > "$METADATA_FILE"
  fi
}

metadata_field() {
  local story_id="$1"
  local field_number="$2"

  awk -F '\t' -v story_id="$story_id" -v field_number="$field_number" \
    '$1 == story_id { print $field_number; exit }' "$METADATA_FILE"
}

merge_touched_files() {
  local previous_files="$1"
  local current_files="$2"

  printf '%s\n' "$previous_files,$current_files" \
    | tr ',' '\n' \
    | sed '/^$/d' \
    | sort -u \
    | paste -sd, -
}

upsert_metadata() {
  local story_id
  local title
  local attempts_count
  local last_error
  local assigned_model
  local files_touched
  local metadata_tmp

  story_id=$(sanitize_metadata_field "$1")
  title=$(sanitize_metadata_field "$2")
  attempts_count=$(sanitize_metadata_field "$3")
  last_error=$(sanitize_metadata_field "$4")
  assigned_model=$(sanitize_metadata_field "$5")
  files_touched=$(sanitize_metadata_field "$6")
  metadata_tmp="$METADATA_FILE.tmp"

  awk -F '\t' \
    -v story_id="$story_id" \
    -v title="$title" \
    -v attempts_count="$attempts_count" \
    -v last_error="$last_error" \
    -v assigned_model="$assigned_model" \
    -v files_touched="$files_touched" \
    'BEGIN { OFS = "\t"; found = 0 }
     /^#/ || NR == 3 { print; next }
     $1 == story_id {
       print story_id, title, attempts_count, last_error, assigned_model, files_touched
       found = 1
       next
     }
     { print }
     END {
       if (!found) {
         print story_id, title, attempts_count, last_error, assigned_model, files_touched
       }
     }' "$METADATA_FILE" > "$metadata_tmp"

  mv "$metadata_tmp" "$METADATA_FILE"
}

collect_touched_files() {
  {
    if [ -n "${START_HEAD:-}" ]; then
      git diff --name-only "$START_HEAD" 2>/dev/null || true
    fi
    git diff --name-only 2>/dev/null || true
    git ls-files --others --exclude-standard 2>/dev/null || true
  } | sort -u | sed '/^$/d' | while IFS= read -r file; do
    if ! printf '%s\n' "$BEFORE_FILES" | grep -Fqx "$file"; then
      printf '%s\n' "$file"
    fi
  done | paste -sd, -
}

collect_status_files() {
  {
    git diff --name-only 2>/dev/null || true
    git diff --cached --name-only 2>/dev/null || true
    git ls-files --others --exclude-standard 2>/dev/null || true
  } | sort -u | sed '/^$/d'
}

mark_item_built() {
  local story_id="$1"
  local prd_tmp="$PRD_FILE.tmp"

  jq --arg story_id "$story_id" \
    '(.userStories[] | select(.id == $story_id)) |= (.passes = true | .validation = false)' \
    "$PRD_FILE" > "$prd_tmp"
  mv "$prd_tmp" "$PRD_FILE"
}

if [ ! -f "$PRD_FILE" ]; then
  echo "Error: Missing $PRD_FILE. Copy prd.json.example to prd.json and define your user stories."
  exit 1
fi

initialize_metadata_file

# Archive previous run if branch changed
if [ -f "$PRD_FILE" ] && [ -f "$LAST_BRANCH_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  LAST_BRANCH=$(cat "$LAST_BRANCH_FILE" 2>/dev/null || echo "")
  
  if [ -n "$CURRENT_BRANCH" ] && [ -n "$LAST_BRANCH" ] && [ "$CURRENT_BRANCH" != "$LAST_BRANCH" ]; then
    # Archive the previous run
    DATE=$(date +%Y-%m-%d)
    # Strip "ralph/" prefix from branch name for folder
    FOLDER_NAME=$(echo "$LAST_BRANCH" | sed 's|^ralph/||')
    ARCHIVE_FOLDER="$ARCHIVE_DIR/$DATE-$FOLDER_NAME"
    
    echo "Archiving previous run: $LAST_BRANCH"
    mkdir -p "$ARCHIVE_FOLDER"
    [ -f "$PRD_FILE" ] && cp "$PRD_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$PROGRESS_FILE" ] && cp "$PROGRESS_FILE" "$ARCHIVE_FOLDER/"
    [ -f "$METADATA_FILE" ] && cp "$METADATA_FILE" "$ARCHIVE_FOLDER/"
    echo "   Archived to: $ARCHIVE_FOLDER"
    
    # Reset progress file for new run
    echo "# Ralph Progress Log" > "$PROGRESS_FILE"
    echo "Started: $(date)" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
    rm -f "$METADATA_FILE"
    initialize_metadata_file
  fi
fi

# Track current branch
if [ -f "$PRD_FILE" ]; then
  CURRENT_BRANCH=$(jq -r '.branchName // empty' "$PRD_FILE" 2>/dev/null || echo "")
  if [ -n "$CURRENT_BRANCH" ]; then
    echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"
  fi
fi

# Initialize progress file if it doesn't exist
if [ ! -f "$PROGRESS_FILE" ]; then
  echo "# Ralph Progress Log" > "$PROGRESS_FILE"
  echo "Started: $(date)" >> "$PROGRESS_FILE"
  echo "---" >> "$PROGRESS_FILE"
fi

echo "Starting Ralph - Base: $BASE_DIR - Target: $TARGET_DIR - Tool: $TOOL - Skill: ${SKILL_NAME:-none} - Max iterations: $MAX_ITERATIONS"

for i in $(seq 1 $MAX_ITERATIONS); do
  if [ -n "$GRAPH_ITEM_ID" ]; then
    STORY_RECORD=$(jq -r --arg story_id "$GRAPH_ITEM_ID" '
      [.userStories[] | select(.id == $story_id)]
      | .[0] // empty
      | [(.id // ""), (.title // "")]
      | @tsv
    ' "$PRD_FILE" 2>/dev/null || true)
  else
    STORY_RECORD=$(jq -r '
      [.userStories[] | select((.passes // false) == false or (.validation // false) == false)]
      | sort_by(.priority // 999999)
      | .[0] // empty
      | [(.id // ""), (.title // "")]
      | @tsv
    ' "$PRD_FILE" 2>/dev/null || true)
  fi
  STORY_ID=$(printf '%s\n' "$STORY_RECORD" | cut -f1)
  STORY_TITLE=$(printf '%s\n' "$STORY_RECORD" | cut -f2-)

  if [ -z "$STORY_ID" ]; then
    echo ""
    echo "Ralph has no incomplete PRD items."
    exit 0
  fi

  PREVIOUS_ATTEMPTS=$(metadata_field "$STORY_ID" 3)
  case "$PREVIOUS_ATTEMPTS" in
    ''|*[!0-9]*) PREVIOUS_ATTEMPTS=0 ;;
  esac
  ATTEMPTS_COUNT=$((PREVIOUS_ATTEMPTS + 1))
  PREVIOUS_FILES=$(metadata_field "$STORY_ID" 6)
  ASSIGNED_MODEL="${RALPH_ASSIGNED_MODEL:-$TOOL}"
  START_HEAD=$(git rev-parse --verify HEAD 2>/dev/null || true)
  BEFORE_FILES=$(collect_status_files)

  echo ""
  echo "==============================================================="
  echo "  Ralph Iteration $i of $MAX_ITERATIONS ($TOOL) - $STORY_ID"
  echo "==============================================================="

  # Run the selected tool with the ralph prompt
  if [[ "$TOOL" == "claude" ]]; then
    # Claude Code: use --dangerously-skip-permissions for autonomous operation, --print for output
    if OUTPUT=$(run_agent "$SCRIPT_DIR/CLAUDE.md" claude --dangerously-skip-permissions --print); then
      TOOL_EXIT=0
    else
      TOOL_EXIT=$?
    fi
  else
    # Codex CLI: use the project-local prompt with workspace write access.
    if OUTPUT=$(run_agent "$SCRIPT_DIR/CODEX.md" codex exec --sandbox workspace-write --cd "$TARGET_DIR"); then
      TOOL_EXIT=0
    else
      TOOL_EXIT=$?
    fi
  fi
  printf '%s\n' "$OUTPUT" >&2

  AGENT_ERROR=$(printf '%s\n' "$OUTPUT" | sed -n 's/^RALPH_ERROR:[[:space:]]*//p' | tail -1)
  if [ "$TOOL_EXIT" -ne 0 ]; then
    if [ -n "$AGENT_ERROR" ] && [ "$AGENT_ERROR" != "none" ]; then
      LAST_ERROR="$AGENT_ERROR (tool exit $TOOL_EXIT)"
    else
      LAST_ERROR="$TOOL exited with status $TOOL_EXIT"
    fi
  elif [ -n "$AGENT_ERROR" ] && [ "$AGENT_ERROR" != "none" ]; then
    LAST_ERROR="$AGENT_ERROR"
  else
    LAST_ERROR="none"
  fi

  ITEM_BUILT=false
  if [ "$TOOL_EXIT" -eq 0 ] && echo "$OUTPUT" | grep -q "<promise>ITEM_BUILT</promise>"; then
    mark_item_built "$STORY_ID"
    ITEM_BUILT=true
  fi

  CURRENT_FILES=$(collect_touched_files)
  FILES_TOUCHED=$(merge_touched_files "$PREVIOUS_FILES" "$CURRENT_FILES")
  upsert_metadata "$STORY_ID" "$STORY_TITLE" "$ATTEMPTS_COUNT" "$LAST_ERROR" "$ASSIGNED_MODEL" "$FILES_TOUCHED"

  # Stop after one item; the graph owns validation, commits, and item routing.
  if [ "$ITEM_BUILT" = true ]; then
    echo ""
    echo "Ralph built $STORY_ID; returning to the graph for validation."
    exit 0
  fi
  
  echo "Iteration $i complete. Continuing..."
  sleep 2
done

echo ""
echo "Ralph reached max iterations ($MAX_ITERATIONS) without completing all tasks."
echo "Check $PROGRESS_FILE for status."
exit 1
