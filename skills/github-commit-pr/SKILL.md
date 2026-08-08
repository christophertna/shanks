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
- Update relevant `explained.md` or `dev/*.md` files for architecture, workflow,
  or developer context.
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

## Commit, push, and PR checks

- Inspect the diff, current branch, and test results before committing.
- Explicitly ask for approval through the command tool immediately before each
  commit, push, or pull-request creation. Use
  `sandbox_permissions: "require_escalated"` and a concise,
  operation-specific `justification` question such as “May I commit these
  changes?”; the tool call's approval prompt—not a chat message—is the request
  the user approves. Do not infer approval from an earlier user request.
- Make commit, push, and pull-request creation each a separate command-tool
  call with `sandbox_permissions: "require_escalated"`.
- Do not pass `prefix_rule` for those operations or rely on trusted command
  prefixes; the user must receive the normal tool-call approval prompt.
- Proceed only after the tool UI visibly presents that approval prompt and the
  user approves it.
- Keep commit, push, and pull-request approvals separate and never bundle them.
  A denied operation must stop without retrying until a new approval is given.
- If one of these commands executes without a visible approval prompt, stop and
  report that the expected approval was not presented; do not continue or retry.
- Push the feature branch with `git push -u origin <branch>`; do not push to `main` unless explicitly requested.
- Pass the commit or PR title separately from the description when using GitHub CLI or an API.
- Before opening the PR, state the exact title, description, and test command for auditability.
