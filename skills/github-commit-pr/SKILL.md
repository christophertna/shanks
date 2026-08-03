---
name: github-commit-pr
description: Create concise Git commit subjects and GitHub pull request titles and descriptions for changes being committed, pushed, or submitted for review. Use when preparing commit messages, pushing feature branches, or opening pull requests.
---

# GitHub Commits and PRs

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

## Commit, push, and PR checks

- Inspect the diff, current branch, and test results before committing.
- Push the feature branch with `git push -u origin <branch>`; do not push to `main` unless explicitly requested.
- Pass the commit or PR title separately from the description when using GitHub CLI or an API.
- Before opening the PR, state the exact title, description, and test command for auditability.
