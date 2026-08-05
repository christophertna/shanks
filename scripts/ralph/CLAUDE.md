# Ralph Agent Instructions

You are an autonomous coding agent working on a software project.

## Graphify First

Before searching source files, reading many files, or dispatching another agent,
query the local Graphify code map first:

1. Run `graphify query "<your codebase question>"`.
2. Use `graphify explain "<name>"` or `graphify path "<A>" "<B>"` when useful.
3. Use the results to choose the smallest set of files to read.

Do not dispatch helper agents before using Graphify. If the graph is missing or
the query is not enough, use `graphify extract . --code-only --out .` or fall
back to normal file inspection. After changing code, run `graphify update .`.

## Directories

- Base engine directory: `$RALPH_BASE_DIR`.
- Target project directory: `$RALPH_PROJECT_DIR`.
- Edit files under the target project directory. Ralph's prompts, PRD, progress
  log, and metadata remain in the base engine directory.
- Graphify commands run from the target project directory and should describe
  the target project's code. The Ralph runner and graph engine remain in the
  base engine directory.

## Your Task

1. Read the PRD at `$RALPH_BASE_DIR/scripts/ralph/prd.json`
2. Read the progress log at `$RALPH_BASE_DIR/scripts/ralph/progress.txt` (check Codebase Patterns section first)
3. Check you're on the correct branch from PRD `branchName`. If not, check it out or create from main.
4. Pick the **highest priority** user story where `passes: false` or `validation: false`
5. Implement that single user story
6. Run the target project’s documented validation command and all other quality checks (e.g., typecheck and lint). For this repository, validation is `.venv/bin/python -m unittest discover -s tests`.
   The graph’s validation node is the final gate; do not commit from Ralph.
7. Update CLAUDE.md files if you discover reusable patterns (see below)
8. Leave only files created or changed by this story in the working tree. Leave files that were already dirty at iteration start, unrelated files, and unrelated generated files untouched. Do not commit or push; the graph commits this item only after `validation` passes.
9. Do not edit the PRD’s `passes` or `validation` flags; the runner and graph own those values.
10. Append your progress to `$RALPH_BASE_DIR/scripts/ralph/progress.txt`
11. Track only genuinely uncertain implementation decisions that you actually implemented. Do not list routine or confident choices.
12. Before your final response, print a `RALPH_UNCERTAINTIES:` section with one concise bullet per uncertain decision, or `RALPH_UNCERTAINTIES: none` when there are none. Then print exactly one `RALPH_ERROR: ...` line. Use `RALPH_ERROR: none` when the story and checks completed successfully; otherwise summarize the latest failure in one line.

The Ralph runner automatically updates `$RALPH_BASE_DIR/scripts/ralph/metadata.txt` after this iteration. Do not edit that file directly.

## Progress Report Format

APPEND to `$RALPH_BASE_DIR/scripts/ralph/progress.txt` (never replace, always append):
```
## [Date/Time] - [Story ID]
- What was implemented
- Files changed
- **Uncertainties:** Genuine uncertain implementation decisions, or `None`
- **Learnings for future iterations:**
  - Patterns discovered (e.g., "this codebase uses X for Y")
  - Gotchas encountered (e.g., "don't forget to update Z when changing W")
  - Useful context (e.g., "the evaluation panel is in component X")
---
```

The learnings section is critical - it helps future iterations avoid repeating mistakes and understand the codebase better.

## Consolidate Patterns

If you discover a **reusable pattern** that future iterations should know, add it to the `## Codebase Patterns` section at the TOP of `$RALPH_BASE_DIR/scripts/ralph/progress.txt` (create it if it doesn't exist). This section should consolidate the most important learnings:

```
## Codebase Patterns
- Example: Use `sql<number>` template for aggregations
- Example: Always use `IF NOT EXISTS` for migrations
- Example: Export types from actions.ts for UI components
```

Only add patterns that are **general and reusable**, not story-specific details.

## Update CLAUDE.md Files

Before committing, check if any edited files have learnings worth preserving in nearby CLAUDE.md files:

1. **Identify directories with edited files** - Look at which directories you modified
2. **Check for existing CLAUDE.md** - Look for CLAUDE.md in those directories or parent directories
3. **Add valuable learnings** - If you discovered something future developers/agents should know:
   - API patterns or conventions specific to that module
   - Gotchas or non-obvious requirements
   - Dependencies between files
   - Testing approaches for that area
   - Configuration or environment requirements

**Examples of good CLAUDE.md additions:**
- "When modifying X, also update Y to keep them in sync"
- "This module uses pattern Z for all API calls"
- "Tests require the dev server running on PORT 3000"
- "Field names must match the template exactly"

**Do NOT add:**
- Story-specific implementation details
- Temporary debugging notes
- Information already in `$RALPH_BASE_DIR/scripts/ralph/progress.txt`

Only update CLAUDE.md if you have **genuinely reusable knowledge** that would help future work in that directory.

## Quality Requirements

- ALL commits must pass your project's quality checks (typecheck, lint, test)
- Do NOT commit broken code
- Keep changes focused and minimal
- Follow existing code patterns

## Browser Testing (If Available)

For any story that changes UI, verify it works in the browser if you have browser testing tools configured (e.g., via MCP):

1. Navigate to the relevant page
2. Verify the UI changes work as expected
3. Take a screenshot if helpful for the progress log

If no browser tools are available, note in your progress report that manual browser verification is needed.

## Stop Condition

After implementing and checking the current story, print:

```
<promise>ITEM_BUILT</promise>
```

Do not wait for validation, commits, or the remaining stories. The graph handles those after this iteration.

## Important

- Work on ONE story per iteration
- Leave commits to the graph’s post-validation checkpoint; never push from Ralph
- Keep CI green
- Read the Codebase Patterns section in `$RALPH_BASE_DIR/scripts/ralph/progress.txt` before starting
