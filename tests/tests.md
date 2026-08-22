# Test coverage

This document summarizes the behavior covered by the repository's tracked test
files. The Python suite contains **223 unittest methods** across twelve
modules; every `hooks/test.hooks/test-*.sh` file is a separate shell
regression harness, run in CI alongside the Python suite on both
`ubuntu-latest` and `macos-latest` (see
[`.github/workflows/tests.yml`](../.github/workflows/tests.yml)) - the
harnesses lean on tools that differ between BSD and GNU userland, and
`test_sandbox_claude.py` skips itself off macOS entirely. The harness
rows in the table below are the list this suite iterates, so
`test_every_shell_harness_is_documented_and_run_in_ci` asserts they cover the
directory exactly and that CI runs each one.

Every count in this file - each row and the headline total - is derived, not
typed. `scripts/sync_tests_md.py` recomputes them from the suites themselves;
run it with `--fix` after adding or removing a test instead of editing the
numbers by hand. The guards in `tests/test_cli.py` check the file against that
same derivation, so a stale number fails the suite with the command that fixes
it.

The tests use in-memory graphs, temporary SQLite databases and temporary
projects, real temporary Git repositories, a fake `gh` executable, stub
adapters, and mocked subprocesses. They verify orchestration and adapter
contracts without making real LLM, GitHub, or destructive shell calls.

Run the Python suite with:

```bash
.venv/bin/python -m unittest discover -s tests
```

Update the counts in this file with:

```bash
.venv/bin/python scripts/sync_tests_md.py --fix
```

Run the repository quality gates from a feature branch with:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/quality_gates.py --diff-base origin/main
```

## Test file inventory

| File | Tests | Main areas |
| --- | ---: | --- |
| [`test_cli.py`](test_cli.py) | 33 | Execution-mode reporting, dev worktree creation and refresh (carrying `.claude/settings.json` and `.claude/skills/` in, leaving `settings.local.json` out) with ignored `.venv` symlinks, doctor diagnostics (including Git/gh/gitleaks version floors, a `core.bare=true` checkout, `core.hooksPath`, unwired Claude Code hooks, and stale worktree hook settings), documentation-count guards for the Python and shell test suites (including the shared count derivation and its fail-closed harness runner), hook-harness coverage in this file and in CI, and run listing, status (including pending interrupts, drift, and recent events), resume, cancellation, recovery, cleanup, pruning, and safety checks |
| [`test_graph.py`](test_graph.py) | 46 | Workflow orchestration, item metadata, repository drift injection, append-only run-manifest behavior, targeted retries, budgets, approvals, dry-run previews, and GitHub handoff |
| [`test_node_contracts.py`](test_node_contracts.py) | 71 | Agent, failure-classification, subprocess, versioned interpreter allowlists, Ralph, local-test, critic, quality-gate, pre-commit policy gate, recovery reconciliation, repository-protocol conformance, preview-protocol narrowing, subprocess timeout budgets, and GitHub adapter contracts |
| [`test_state_schema.py`](test_state_schema.py) | 10 | State migration, one-step migration chains, retry metadata, versioned checkpoints, and legacy resume behavior |
| [`test_lifecycle.py`](test_lifecycle.py) | 8 | Run leases, stale recovery, recovery-state reconciliation, interruption/resume, terminal release, and checkpoint cleanup |
| [`test_workspaces.py`](test_workspaces.py) | 14 | Run identity, Git worktree creation/reuse, syncing the gitignored Claude Code hook guard, project skills, and `.venv` symlink into new worktrees, local/remote branch listing and deletion, workspace context, and workspace state migration |
| [`test_viewer.py`](test_viewer.py) | 11 | Viewer HTML, execution-state data including pending interrupts and repository drift, checkpoint sharing, the live-reload module path, curated-constant node coverage, and Mermaid output |
| [`test_quality_gates.py`](test_quality_gates.py) | 10 | Quality command definitions, typing-gate module coverage, safe diff refs, numstat parsing, generated-output handling, diff limits, and gate failure reporting |
| [`test_fault_injection.py`](test_fault_injection.py) | 7 | Injected Git, GitHub, validation, checkpoint, and agent process failures |
| [`test_git_integration.py`](test_git_integration.py) | 4 | Real temporary Git repositories, worktrees, commits, pushes, PR creation/reuse, fake-`gh` recovery, dry-run preview behavior, and upstream/worktree drift reporting |
| [`test_agent_integration.py`](test_agent_integration.py) | 5 | Real Codex and Claude CLI smoke tests, including the sandboxed Claude write path and the GPT-5.6 Luna/Claude Opus 4.8 critic adapters, against a small deterministic project (opt-in) |
| [`test_sandbox_claude.py`](test_sandbox_claude.py) | 4 | `scripts/sandbox_claude.sh` write containment: allows writes inside the target directory, denies writes outside it (including a shared-temp-root sibling and a `..` escape), and falls back to unsandboxed execution when `sandbox-exec` is unavailable |
| [`../hooks/test.hooks/test-deny-dangerous.sh`](../hooks/test.hooks/test-deny-dangerous.sh) | 8 shell checks | Dangerous-command blocking and safe-command allowlisting |
| [`../hooks/test.hooks/test-secret-scan.sh`](../hooks/test.hooks/test-secret-scan.sh) | 7 shell checks | gitleaks-backed secret blocking on Write/Edit content, new_string, and Bash command text |
| [`../hooks/test.hooks/test-guard-worktree.sh`](../hooks/test.hooks/test-guard-worktree.sh) | 13 shell checks | Branch-switch blocking while tracked files are dirty, with branch creation (`-b`/`-B`/`-c`), `--` path restores, clean trees, untracked-only trees, non-git commands, and the override env var all allowed |
| [`../hooks/test.hooks/test-pre-push.sh`](../hooks/test.hooks/test-pre-push.sh) | 3 shell checks | `pre-push` gates on quality-gate exit status and fails open when the venv Python is missing |
| [`../hooks/test.hooks/test-run-impacted-tests.sh`](../hooks/test.hooks/test-run-impacted-tests.sh) | 16 shell checks | Scoped test-module and shell-harness resolution against the touched file's own Git tree, pass/fail feedback, and silent skip on no match, non-Python files, a missing interpreter, extensionless Git hooks, and shell files outside `hooks/` |
| [`../hooks/test.hooks/test-format-touched.sh`](../hooks/test.hooks/test-format-touched.sh) | 10 shell checks | Black reformat reporting, ruff and mypy failure feedback, `[tool.mypy] files` gating of the mypy run resolved against the touched file's own Git tree, and silent skip on non-Python files, files outside the project, missing files, and a missing interpreter |
| [`../hooks/test.hooks/test-post-merge-checkout.sh`](../hooks/test.hooks/test-post-merge-checkout.sh) | 3 shell checks | `post-checkout`'s same-SHA no-op skip and different-SHA `graphify update` trigger, and `post-merge`'s no-op fallback when `graphify` isn't on PATH - all three under a PATH holding git and nothing else, so a hook that shells out to coreutils fails here rather than on whichever platform ships git outside `/usr/bin` |
| [`../hooks/test.hooks/test-prompt-repo-state.sh`](../hooks/test.hooks/test-prompt-repo-state.sh) | 41 shell checks | `UserPromptSubmit` repository-state injection: branch, upstream drift (printed even at zero, with the last successful fetch's age under both BSD and GNU `stat`, and the truncated-`FETCH_HEAD` case), the no-upstream substitute (commits ahead of `origin/main`, at zero and non-zero, and its degraded form in a remoteless checkout), the debounced background fetch, its skip inside the debounce window, and the in-flight-fetch cases that must not read as never-fetched, uncommitted changes (with truncation), recent commits, and the cached open-PR and `main`-CI lines, plus the fail-open paths - non-repository directory, missing `git`, broken `gh`, and detached HEAD - each of which must still exit zero |

### CLI diagnostics

- `test_cli.py` verifies healthy doctor output and non-zero results for invalid
  mode, lease, retention, and checkpoint configuration, for a Git or gh
  version below the supported minimum, and for an unconfigured
  `core.hooksPath`.
- `test_cli.py` verifies the doctor tool-presence check and
  `GitHubAdapter.preflight()`'s required-tool list stay in sync.
- `test_cli.py` verifies doctor's `gitleaks` floor equals the
  `GITLEAKS_VERSION` pinned in `.github/workflows/tests.yml`. Bumping the CI
  pin without the floor would let a local gitleaks older than CI's pass
  `doctor` and miss secrets CI then catches.
- `test_cli.py` verifies this file's own counts stay accurate: each `test_*.py`
  row against that module's `def test_` count, the headline unittest-method
  total against the sum of those rows, and each shell-harness row against the
  `passed: N, failed: 0` line the harness itself prints. Both guards read those
  numbers through `scripts/sync_tests_md.py`, the same derivation `--fix`
  writes, so the checker and the fixer cannot disagree about a count, and both
  failures name the command that repairs the file.
- `test_cli.py` verifies the fixer can actually correct a wrong number: a stale
  row and a stale headline are both rewritten from a temporary suite, and the
  result is stable on a second pass. A harness that exits non-zero or prints
  anything but `passed: N, failed: 0` raises instead of yielding a count, so
  `--fix` can never document a passing suite that does not exist.
- `test_cli.py` verifies the harness rows cover `hooks/test.hooks/` exactly and
  that `.github/workflows/tests.yml` runs each one. Without it a new harness
  can be committed, pass locally, and never run anywhere: the row list above is
  what the suite iterates, and the CI step is a separate hand-maintained copy.
  It found `test-guard-worktree.sh` documented here but missing from CI.
- `test_cli.py` verifies the `claude-hooks` doctor check: a `hooks/*.sh` script
  the gitignored `.claude/settings.json` never references fails the check, an
  extensionless Git hook beside it does not, an absent settings file is a
  warning rather than a failure (a fresh clone and CI both legitimately lack
  it), and a present-but-unparsable one fails. It also verifies a worktree
  whose `.claude/settings.json` has fallen behind the main checkout's fails
  with a `./shanks dev sync` pointer, that the main checkout is never flagged
  as stale against itself, and that `dev_sync` clears the failure. The
  healthy-doctor test also
  asserts `[OK] claude-hooks` appears, so the check stays wired into
  `doctor_checks()` rather than merely importable.

### Developer worktrees

- `shanks dev worktree <branch>` creates the worktree, copies the gitignored
  `.claude/settings.json` in, and symlinks `.venv`, so a second agent's tree has
  the same hooks and test commands as the main checkout. A bare
  `git worktree add` carries neither, which would leave that agent running with
  no dangerous-command or secret scanning at all.
- It refuses an existing target directory, and warns on stderr when the project
  itself has no `.claude/settings.json` to copy.

### Run management

- `test_cli.py` verifies run listing, checkpoint status, resume and cancellation
  requests, stale-lease recovery, checkpoint cleanup, safe removal guards, and
  the `runs prune` dry-run report and orphan worktree/branch removal.
- `test_workspaces.py` verifies local and remote run-branch listing and the
  development-mode, protected-branch, and run-scope guards on remote branch
  deletion.
- `test_cli.py` verifies that `runs status` surfaces a paused run's pending
  interrupt prompt (question and options), the persisted `repo_drift` note, and
  the newest run-manifest events, in both JSON and human-readable output.

## Workflow orchestration

Sources: [`test_graph.py`](test_graph.py), with graph topology assertions also
in [`test_viewer.py`](test_viewer.py).

### Entry, intake, and item routing

- Every node returned by `create_nodes()` is registered in `build_graph()`
  with the targeted retry policy, so a newly added lease-touching node can't
  silently skip retry coverage.
- GitHub preflight runs before intake; a successful preflight opens the intake
  interrupt, while a failed preflight records `preflight_failed` and ends the
  run without entering intake.
- A normal single-item implement run completes planning, building, critic
  review, validation, and PR handoff, and marks the PRD item as passing.
- Acceptance criteria and an optional validation command are carried from the
  current PRD item into planning and validation requests, including Ralph's
  camelCase JSON field names.
- The graph advances through multiple incomplete PRD items, records completed
  item IDs and per-item attempt counts, and processes each item before the
  final handoff.
- Already-completed items terminate without invoking the builder.
- Item selection skips passing items but retries an item that was built while
  its validation flag remains false.
- Choosing `learn` returns to the same intake question with a learned status and
  no workflow mode selected.
- A transient learning failure retries the learning node with backoff before
  returning to intake.
- Choosing `implement` enters the implementation workflow and creates the
  requested item.
- Learning notes are carried into the later implementation planning request.
- Planning refreshes the repository drift note once per item, stores it in
  `repo_drift`, carries it into every downstream agent request's context, and
  records a `drift_check` manifest event without dropping the planning event.

### Planning, building, and critic review

- A permanent failed builder result stops before critic or validation and leaves
  `build_completed` false; transient failures use the targeted retry path.
- An exception from the builder is converted into a failed-build state with the
  exception message and the failed-build route.
- Permanent exceptions from other agent nodes use the classified terminal
  failure handler instead of escaping the graph.
- Critic rejection sends feedback into the next builder request and causes the
  same item to be rebuilt; the attempt count and subsequent validation are
  checked.
- Repeated critic rejection rebuilds the same item until its per-item attempt
  limit is reached, then produces `attempt_limit_reached`.
- Builder-reported uncertainties are stored under the relevant PRD item ID.
- Transient builder failures retry the builder with bounded backoff; the retry
  count and failure classification are persisted.
- Transient critic failures retry the critic rather than rebuilding already
  produced code.
- Transient validation failures retry validation rather than invoking the
  debugger, while permanent builder failures remain terminal.

### Validation, debugging, and recovery

- Validation failure invokes the debugger with the validation errors, then
  replans and rebuilds the same item.
- Debugger root cause and repair instructions are added to the PRD description,
  planner context, planner instructions, and builder instructions.
- A successful validation retry still commits the repaired item and proceeds to
  pull-request publication.
- GitHub failure and completed GitHub states terminate instead of routing into
  the debugger.

## Quality gates

Sources: [`test_quality_gates.py`](test_quality_gates.py),
[`test_node_contracts.py`](test_node_contracts.py),
[`../scripts/quality_gates.py`](../scripts/quality_gates.py), and
[`.github/workflows/tests.yml`](../.github/workflows/tests.yml).

- The quality runner defines formatting, linting, typing, dependency/security,
  and diff-size gates as separate, inspectable commands.
- Black checks the repository's Python paths without rewriting files; Ruff
  checks the same paths; Mypy checks the production modules; and pip-audit
  scans both runtime and development requirement files.
- The typing gate passes no paths of its own, so `[tool.mypy] files` in
  `pyproject.toml` is the single source of truth for what gets checked. The
  test asserts the command carries no path arguments and that every core
  runtime module is still in that list, so coverage cannot be silently dropped
  the way `workflow/nodes.py` was while the two lists disagreed.
- The diff gate parses `git diff --numstat`, counts binary files safely, rejects
  malformed output, and enforces limits of 50 changed files and 2,000 changed
  lines by default. Derived `graphify-out/` artifacts are excluded from those
  source-diff limits.
- Diff-base refs are validated before they enter a subprocess argument list,
  and the GitHub adapter allowlists only its exact repository quality command.
- GitHub preflight runs the full quality suite on a clean branch; commit
  preparation runs it again against the staged diff and stops before `git
  commit` if any gate fails.
- CI fetches the complete Git history so the diff gate can compare each push or
  pull request with `origin/main`.

## Fault-injection tests

Source: [`test_fault_injection.py`](test_fault_injection.py).

- GitHub adapter Git execution errors are injected as operating-system failures
  and must become classified adapter failures with an audit command.
- GitHub pull-request creation failures are injected after a successful push and
  lookup; the adapter stops without reporting a PR URL.
- Validation subprocess timeouts become transient validation failures with the
  failing output preserved.
- Agent subprocess timeouts are classified as transient, while an injected
  builder exception reaches the terminal build-failure route and records an
  `agent_error` manifest event.
- Checkpoint read and write failures are injected into the versioned SQLite
  saver and are asserted to propagate instead of being silently swallowed.

### Budgets, cancellation, and run state

- A runtime overage stops the graph before external adapters execute.
- Input and output token usage and dollar cost accumulate in state; exceeding
  either configured limit stops the run before the critic.
- The total-attempt budget stops execution before the critic when the budget is
  exhausted.
- Failure classifications distinguish transient, validation, guardrail, budget,
  cancellation, and permanent failures; only transient failures enter targeted
  retry routes.
- A cancellation in the initial state stops the run before the builder and
  preserves the cancellation message.
- A cancellation written into a checkpoint is observed when the graph resumes
  and produces a terminal cancelled state.
- The run manifest records agent events, assigned models, planning prompts and
  item IDs, and pull-request IDs.
- The run manifest is append-only across a two-item run: each item records its
  own drift-check and planning events, and every event timestamp stays unique,
  so a node that returns the whole accumulated list instead of only its new
  events fails the check. The drop direction is covered separately by the
  transient-build-retry test, where one node records twice (the failing build
  audit event, then the retry event) and both must survive.

## Guardrails, hooks, and command safety

Sources: [`test_node_contracts.py`](test_node_contracts.py) and
[`../hooks/test.hooks/`](../hooks/test.hooks/).

### Process and workspace boundaries

- `GitHubAdapter` implements every `RepositoryAdapter` and
  `PreviewRepositoryAdapter` member with an identical signature. The dry-run
  nodes narrow with `isinstance(repository, PreviewRepositoryAdapter)` before
  calling a preview, and that runtime check only compares member *names* - so
  this check is what proves the signatures still match. The graph test doubles
  omit the preview methods, so only the real adapter exercises that path.
- The quick read-only lookups - Git probes plus `gh auth status` and the
  `gh pr list` pull-request lookup - reach `subprocess` with the short
  `probe_timeout_seconds` budget while commits, pushes, `gh pr create`, and
  the quality-gate command keep the hour-long `timeout_seconds`; a
  non-positive `probe_timeout_seconds` is rejected at construction.
- Both of those fixed timeouts, and the policy gate's gitleaks scan, are
  clamped again by whatever is left of the run's wall-clock budget, and fail
  before launching the subprocess once it is gone. The budget reaches them
  through `run_deadline_scope`, which every node installs around its body -
  checked end to end by driving `preflight` with a repository double that reads
  `remaining_deadline_seconds()`.
- Unapproved subprocess executables are rejected before execution.
- Working directories outside the configured allowlist are rejected before
  execution.
- GitHub tokens and API-key-like credentials are redacted from adapter output.
- Debugger requests use read-only execution and structured-output schema
  enforcement.
- GitHub path normalization rejects traversal outside the project and symlinks
  that resolve outside it, while allowing an in-project file.
- The Git/GitHub command allowlist rejects an unapproved command without
  invoking subprocesses.
- The exact quality-gate command is allowed, while altered script paths, refs,
  and extra flags remain rejected.

The Python test that drives these harnesses first checks `bash`, `jq`, and
`gitleaks` are on `PATH` and fails with a message pointing at `./shanks doctor`
when one is not. Every hook the harnesses exercise fails closed without those
binaries, so a missing tool would otherwise report a long list of
`expected=allow got=block` guard regressions instead of an unset-up machine.
The list is asserted to be a subset of `./shanks doctor`'s required tools, so
the two cannot drift.

### Shell guard regression checks

The shell harness invokes `hooks/deny-dangerous.sh`, classifies each command as
allowed or blocked, counts pass/fail results, and exits non-zero if any
expectation fails. It verifies that the guard:

- Blocks destructive root deletion: `rm -rf /`.
- Blocks destructive deletion with `sudo`.
- Blocks remote install pipelines that pipe `curl` into a shell.
- Blocks force-pushing to `main`.
- Blocks `gh auth token` access.
- Allows deletion of a relative build cache.
- Allows a normal push to a feature branch.
- Allows creating a pull request with `gh pr create`.

### Secret-scan regression checks

The shell harness invokes `hooks/secret-scan.sh`, which scans a Write/Edit
tool call's `content`/`new_string`, or a Bash tool call's `command`, with
`gitleaks` before the file is written or the command runs, and blocks
(rather than just flags) any match. It verifies that the guard:

- Allows ordinary code and prose with no credential-shaped content.
- Blocks a high-entropy GitHub personal-access-token-shaped string in
  `content` (Write), `new_string` (Edit), and `command` (Bash).
- Allows a tool call with no content field at all (e.g. an Edit that only
  removes text).
- Allows an ordinary Bash command with no credential-shaped content.

### Scoped test-impact regression checks

The shell harness invokes `hooks/run-impacted-tests.sh` with a synthetic
PostToolUse payload and a stubbed `python` interpreter (`SHANKS_TEST_IMPACT_PYTHON`)
so it never depends on the real suite's runtime. It verifies that the hook:

- Runs quietly (exit 0) when the matched test module's stub interpreter
  succeeds.
- Surfaces a failure (exit 2, with the module's output on stderr) when the
  matched test module's stub interpreter fails.
- Skips silently when the touched file has no `tests/test_<name>.py` match.
- Resolves a touched `tests/test_<name>.py` file to itself rather than
  guessing a `tests.test_test_<name>` module.
- Skips silently for non-Python files and when the configured Python
  interpreter doesn't exist (fails open).
- For a touched `hooks/<name>.sh`, runs the matching
  `hooks/test.hooks/test-<name>.sh` harness directly with `bash` and
  surfaces the same pass/fail/skip behavior; a touched
  `hooks/test.hooks/test-*.sh` file resolves to itself.
- Skips silently for an extensionless Git hook (e.g. `hooks/post-merge`,
  which has no `.sh` match) and for a `.sh` file outside `hooks/`, even if a
  same-named harness coincidentally exists.
- Resolves both the Python and shell cases against the touched file's own Git
  tree, not the session's `.cwd`: a file edited in a sibling worktree runs
  that worktree's test module and harness, which the session's directory
  would never find.

### Scoped formatting and lint checks

The shell harness invokes `hooks/format-touched.sh` with a synthetic
PostToolUse payload and a stubbed `python` interpreter (`SHANKS_FORMAT_PYTHON`)
so it never depends on the real `black`/`ruff`/`mypy` installs. It verifies
that the hook:

- Runs quietly (exit 0) when every stubbed tool succeeds.
- Reports the reformat (exit 2) when `black --check` fails and the following
  `black` write pass succeeds, since the file on disk no longer matches what
  the agent wrote.
- Surfaces `ruff check` and `mypy` failures (exit 2) with their output on
  stderr.
- Reads `[tool.mypy] files` as TOML, including a single-line list, and runs
  `mypy` only for matching files, so a failing stub is never reached for an
  unlisted file.
- Skips silently for non-Python files, Python files outside the project
  directory, files that no longer exist, and a missing Python interpreter
  (fails open).
- Resolves the project root from the touched file's own Git tree, not the
  session's `.cwd`: a file edited in a sibling worktree is formatted and
  type-checked against that worktree's `pyproject.toml`, where the session's
  directory used to skip it silently.

## GitHub commit and pull-request delivery

Sources: [`test_graph.py`](test_graph.py) and
[`test_node_contracts.py`](test_node_contracts.py).

### Commit scope and resume safety

- A completed `commit_sha` prevents the commit side effect from running again.
- Commit preparation excludes files that were already dirty when the run
  started and commits only fresh story files.
- The staged diff, `git add`, and `git commit --only` command arguments are
  constrained to those fresh files.
- A saved `pr_url` prevents the publish side effect from running again.

### Preflight

- Preflight checks tool availability, branch state, authentication, and local
  tests plus the quality gates, and returns the test output on success.
- Preflight's tool check includes `jq` and `gitleaks` (needed by the secret-scan
  hook) alongside `git`, `gh`, and `bash`; a missing tool fails preflight before
  any Git command runs.
- A dirty worktree fails preflight before local tests run.

### Publishing and PR reuse

- Publishing uses a restricted environment: Git receives the non-interactive
  prompt setting, GitHub receives only the GitHub token, unrelated secrets are
  omitted, and pull-request text is redacted.
- Publishing pushes the validation branch before creating or reconciling a PR
  against `main` and returns its URL plus lifecycle state.
- Existing open PR text and reviewer/label policies are updated only when
  needed; closed unmerged PRs are reported without reopening by default, merged
  PRs are reported as merged, and behind or aged branches are reported as
  stale. Reopening is an explicit adapter option.
- A second reconciliation with the same text and policy performs no PR edit.
- Commit failure is reported and stops before pull-request creation.
- Push failure stops before PR lookup or creation.
- PR creation failure is reported after the preceding push and lookup steps.
- A failed GitHub publish stops without invoking the debugger.
- Transient push and PR-reconciliation failures (network interruptions, rate
  limits) retry the same node with backoff instead of ending the run; guardrail
  and other permanent failures still end without retrying.

### Approval and handoff behavior

- Commit approval is requested before any commit side effect; approval then
  leads to a publish approval and pull-request reconciliation.
- Rejecting commit approval ends with no commit or pull request.
- Rejecting publish approval ends with no push or pull request.
- `SHANKS_MODE=dry-run` skips handoff approval pauses, previews commit/push/PR
  actions, records planned commands and file diffs, and makes no repository or
  GitHub side-effect calls.
- The same dry run against the *real* `GitHubAdapter`, over a temporary Git
  repository and worktree, reports `commit_preview`/`branch_push_preview`/
  `pull_request_preview` with the exact `git commit`, `git push -u`, and
  `gh pr create` commands it would have run - while `HEAD`, the worktree
  status, the index, and the remote branch list are all unchanged and the
  fake `gh` records zero calls. The graph-level test above uses a double that
  omits the previews, so this is the only check that exercises the adapter's
  own preview path.
- A repository implementing only *some* previews is not a
  `PreviewRepositoryAdapter`, so the dry-run nodes fall back to the generic
  preview for every action rather than per action. Asserted through
  `commit_item` with a partial double whose methods raise if reached.
- GitHub failure and completed GitHub states terminate rather than entering
  debugger recovery.
- The multi-item workflow commits each passing item and publishes one pull
  request after all items pass.

## Agent and adapter contracts

Source: [`test_node_contracts.py`](test_node_contracts.py).

### Common agent and subprocess behavior

- Planner, builder, critic, validator, and debugger stubs all return the common
  `AgentResult` shape with the configured model and a non-empty status.
- The cheap critic exposes its model name and returns an approval result.
- The generic subprocess adapter maps command output into a completed result,
  including feedback, model, prompt, token counts, and executed commands.
- A request timeout is passed through as the subprocess timeout.

### Local validation and debugging adapters

- A non-zero local test suite becomes `validation_failed`, with validation set
  to false and the failing output captured as validation errors.
- Adapter failures expose a shared classification, including transient network
  or timeout failures and non-retryable guardrail failures.
- The local validator runs a current item's validation command when provided,
  tokenizes it without a shell, and falls back to full unittest discovery when
  the item has no command.
- The local validator's command policy is narrower than the shared agent
  executable allowlist: shell interpreters (`bash`, `/bin/sh`) and
  interpreter-position inline-code flags (`-c`, `-Ic`) are rejected as
  `validation_failed` before any subprocess is launched; options after a
  module or script boundary are passed through.
- Agent and local-validation executable policies accept versioned Python 3
  names such as `python3.11` while continuing to reject unapproved executables.
- Structured debugger JSON is mapped to status, root cause, builder
  instructions, and feedback.
- Debugger requests include the validation failure and item description.
- The Claude-tool debugger uses read-only plan permissions with the
  `Read,Grep,Glob` tool list and JSON-schema output.

### Dependency factories and critic models

- Default dependencies wire Codex planning, Ralph building, local-test
  validation, debugging, and GitHub repository operations.
- The Claude tool option swaps in Claude planning, configures Ralph to use
  Claude, and selects the Claude Opus critic/debugger setup.
- The GPT-5.6 Luna critic is configured for the expected model, maximum
  reasoning, sandboxed read-only execution, and maps structured approval and
  feedback JSON.
- The Claude Opus 4.8 critic is configured for the expected model and medium
  effort, plan/read-only permissions, and JSON-schema output, and maps its
  structured result.
- Luna and Claude dependency factories wire the corresponding critic adapter
  into the node dependencies.
- `hooks/HOOKS.md`'s documented `--tools` scopes for the build agent
  (Ralph/`ClaudeAdapter(read_only=False)`), the read-only Claude adapters
  (`ClaudeAdapter(read_only=True)`, the Claude debugger, and the Claude Opus
  4.8 critic), and the Codex-only adapters (no `--tools` flag) all match the
  live values in `workflow/adapters.py` and `scripts/ralph/ralph.sh`.

### Ralph adapter

- Ralph command construction selects the project directory, agent-engine
  working directory, tool, project skill, and iteration count.
- Ralph receives the graph item ID and an enriched requirement containing the
  current PRD requirement, other PRD items, and repair instructions.
- The `RALPH_UNCERTAINTIES` output section is parsed into structured
  uncertainties.
- A successful process without the `<promise>ITEM_BUILT</promise>` signal is
  treated as a failed build.
- Ralph synchronization updates only the changed PRD item, preserves that
  item's acceptance criteria, and leaves unchanged items untouched.

## State schema and checkpoint persistence

Source: [`test_state_schema.py`](test_state_schema.py), with checkpoint sharing
also covered in [`test_viewer.py`](test_viewer.py).

### Schema migration

- Unversioned state is migrated to the current schema without mutating the
  legacy input, while preserving task data and applying current attempt
  defaults.
- A state declaring a schema newer than the application supports is rejected
  with `StateSchemaError`.
- Version 1 state receives current run-budget defaults, including total token
  and cancellation fields.
- Version 2 state receives an initialized run manifest.
- Version 3 state receives failure classification, retry counters, retry target,
  and backoff fields for resumable targeted retries.
- Migrating v4 to v5 adds the run identity, branch, and isolated workspace
  fields; migrating v5 to v6 adds lease, heartbeat, and recovery metadata.

### SQLite checkpoints and compatibility

- `VersionedSqliteSaver` migrates legacy checkpoint channel values when they
  are read.
- New checkpoints are stamped with the current schema version when written.
- A checkpoint created with the legacy saver can be resumed through the current
  graph, including an intake interrupt and a later implement command, while
  retaining the current schema version.
- Terminal checkpoints release their run lease, and explicit cleanup retains
  recent checkpoint history while deleting associated writes.

## Run isolation and lifecycle safety

Sources: [`test_workspaces.py`](test_workspaces.py) and
[`test_lifecycle.py`](test_lifecycle.py).

- Each configured `thread_id` becomes a persisted run identity with its own
  Git branch and worktree; repeated invocations of the same run reuse that
  workspace.
- A run worktree receives the same gitignored guardrails as a developer
  worktree: `.claude/settings.json` is copied in (and re-copied on reuse), and
  `.venv` is symlinked so the `PostToolUse` hooks - which resolve their
  interpreter from the touched file's own tree - find one there instead of
  failing open. Both are skipped without error when the project has neither,
  and re-syncing an existing worktree does not trip over the existing symlink.
- Workspace context routes agent, Ralph, and GitHub subprocesses into the run's
  directory, and Ralph metadata is stored under the isolated run directory.
- Live leases block a second owner of the same run; expired leases are recovered
  and their recovery count is persisted.
- Interruptions are recorded as resumable lifecycle state, and resuming the
  same run preserves ownership until a terminal checkpoint releases the lease.
- Checkpoint cleanup keeps the configured recent history and removes associated
  writes instead of leaving orphaned SQLite rows.

## Viewer and observability

Source: [`test_viewer.py`](test_viewer.py).

### Viewer page and execution state

- `graph.html` listens for server reconnects, resets the cached graph
  definition, exposes thread and execution-budget controls, fetches graph
  state, and displays checkpoint history and the run manifest. The Live
  execution panel is a native `<details>`/`<summary>` disclosure so it can
  be collapsed without custom JS.
- `load_graph_module()`'s dynamic `exec()` of `graph.py`'s source draws a
  Mermaid diagram without raising, so a change to `graph.py` (e.g. a
  `dataclass` whose `from __future__ import annotations` string
  annotations need module-namespace resolution) can't silently reintroduce
  the "module not registered in `sys.modules`" failure that broke the live
  viewer.
- Mermaid output includes the targeted retry backoff node, dashed recovery edges,
  and the separate terminal route for non-build failures.
- `execution_state` reads the current checkpoint and bounded history using the
  requested thread ID and history limit.
- The execution payload exposes current node, item identity, attempt counts,
  token and cost totals, run identity, branch, workspace, lease/recovery
  metadata, last error, assigned model, checkpoint IDs, and run manifest entries.
- Default graph instances share the configured SQLite checkpoint database, so a
  later graph instance can read an earlier instance's state and history.

### Mermaid graph rendering

- Forward workflow edges render solid and recovery/backward edges render
  dashed.
- The rendered topology includes preflight, intake, planning, building,
  validation, failed-build, commit, item routing, GitHub handoff, debugger,
  and critic-auditor paths.
- Critic rejection loops back to building; debugger and item-router recovery
  paths loop back to planning.
- Structured labels and semantic visual classes are applied to core, learning,
  review, decision, delivery, recovery, safety, failure, stopped, and
  completion nodes, with a legend explaining the colors.
- Detailed rendering exposes the main and recovery sections and their links.
- `retry_backoff` and `failed_run` render in the detailed view's recovery
  section with their curated labels, and stay out of the overview.
- Every curated viewer constant (`GRAPH_NODE_ORDER`, `VIEW_NODE_LABELS`,
  `VIEW_NODE_CLASSES`, and the `VIEW_MAIN_NODES`/`VIEW_RECOVERY_NODES` union)
  covers exactly the nodes `create_nodes()` builds, allowing `__start__` and
  `__end__` as viewer-only extras, and the two view sets stay disjoint. This is
  what keeps a newly added node from silently vanishing from the structured
  view, which is how `failed_run` and `retry_backoff` were both missed.
- Invalid or unintended edges are excluded, including direct GitHub-to-debugger
  routing, validation-to-debugger dashed styling, critic-to-validation or
  critic-to-item-router edges, self-loops, and direct building-to-end edges.
