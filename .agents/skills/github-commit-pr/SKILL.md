---
name: github-commit-pr
description: Create concise Git commit subjects and GitHub pull request titles and descriptions for changes being committed, pushed, or submitted for review. Use when preparing commit messages, pushing feature branches, or opening pull requests.
---

# GitHub Commits and PRs

## Documentation synchronization

Before committing, pushing, or opening a pull request, review and update all
affected Markdown documentation before reporting completion.

- Update `README.md` for user-facing behavior, setup, or commands.
- Update `tests/tests.md` when test coverage, commands, or expectations change.
- Update `hooks/HOOKS.md` when a hook is added, removed, or its trigger,
  matcher, or agent scope changes.
- Update relevant `explained.md` or `dev/*.md` files for architecture, workflow,
  or developer context.
- Update the priority listing in `dev/new features.txt` (the roadmap) when a
  change completes a listed item: remove the completed item, renumber the
  remaining items, and drop any related bullet in its Suggestions section.
- Keep documentation changes focused: update only files whose content is
  affected.

## Commit subject

- Use `<type>: <imperative summary>`.
- Keep the subject under 50 characters, including the type prefix.
- Omit a final period.
- Describe the outcome, not the implementation steps.
- Use an applicable prefix: `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`, `ci:`, `build:`, `perf:`, or `revert:`.

Examples:

- `feat: add retry limit`
- `fix: preserve failed item state`
- `ci: run Python tests`

## Pull request title

- Use the same type-prefix format as the commit subject.
- Keep it under 50 characters and make it specific to the change.
- Put explanation in the description, never in the title.

## Pull request description

- Explain only why the change was made and how it was tested.
- Use this structure:

  ```markdown
  ## Why
  - Explain the problem, need, or outcome.

  ## Tested
  - `command used`
  ```

- Omit greetings, filler, implementation walkthroughs, commit inventories, and unrelated future work.
- Report failed or skipped tests honestly.

## Merge authority

- Never merge a pull request or enable auto-merge.
- Only the user or another human may review and merge it.
- The AI may open the pull request and leave it ready for human review.

## Pull request lifecycle checkpoints

There are two separate `AskUserQuestion` checkpoints below. Ask each one on
its own turn, with its own question — never merge them into a single
question (e.g. "open and merge now?"), and never skip the second one just
because the first one already got an answer. Getting a "yes" to open the PR
is not a "yes" to merge it.

1. **After push, before opening the PR.** Ask whether to open it now or wait
   for more items to land on the branch first. Only proceed once they answer.
   Before opening, state the exact title, description, and test command for
   auditability. Pass the title separately from the description when using
   GitHub CLI or an API.
2. **After the PR is open.** Ask a second, distinct question: whether to
   merge it now or wait for more changes to land on the branch first — don't
   ask in prose; it costs the user a typed reply instead of a click.
   - If they choose to wait, stop here — do not poll for merge status.
   - If they choose to merge now, poll the PR's status (e.g. `gh pr view
     <number> --json state,mergeStateStatus,mergeable`) every ~15 seconds for
     up to ~3 minutes. This only watches for the human's merge; the AI still
     never merges the PR itself.
   - Stop the loop and report immediately if the PR closes without merging or
     its merge state shows a conflict (`mergeStateStatus: DIRTY`).
   - If the ~3 minute cap is reached before it merges, stop polling and
     report the current status without deleting anything.
   - Once the PR's state is `MERGED`, delete the local feature branch: check
     out the base branch, pull, then `git branch -d <branch>`.
   - If the user reports the PR was merged outside this checkpoint (e.g. they
     merged it themselves before checkpoint 2 ran), skip straight to the
     branch cleanup step above — do not retroactively poll.

## Commit, push, and PR checks

- Inspect the diff, current branch, and test results before any side effect.
- Keep commit, push, and pull-request creation as separate operations.
- Stop and report if any operation fails.
- Push the feature branch with `git push -u origin <branch>`; do not push to `main` unless explicitly requested.
