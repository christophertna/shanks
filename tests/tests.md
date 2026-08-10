# Test coverage

This document summarizes the behavior covered by the repository's tracked test
files. The Python suite contains **150 unittest methods** across eleven
modules; `hooks/test-guard.sh` is a separate shell regression harness with
eight command checks.

The tests use in-memory graphs, temporary SQLite databases and temporary
projects, real temporary Git repositories, a fake `gh` executable, stub
adapters, and mocked subprocesses. They verify orchestration and adapter
contracts without making real LLM, GitHub, or destructive shell calls.

Run the Python suite with:

```bash
.venv/bin/python -m unittest discover -s tests
```

Run the repository quality gates from a feature branch with:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/quality_gates.py --diff-base origin/main
```

## Test file inventory

| File | Tests | Main areas |
| --- | ---: | --- |
| [`test_cli.py`](test_cli.py) | 14 | Execution-mode reporting, doctor diagnostics (including Git/gh version checks), and run listing, status, resume, cancellation, recovery, cleanup, pruning, and safety checks |
| [`test_graph.py`](test_graph.py) | 39 | Workflow orchestration, item metadata, targeted retries, budgets, approvals, dry-run previews, and GitHub handoff |
| [`test_node_contracts.py`](test_node_contracts.py) | 42 | Agent, failure-classification, subprocess, Ralph, local-test, critic, quality-gate, and GitHub adapter contracts |
| [`test_state_schema.py`](test_state_schema.py) | 9 | State migration, retry metadata, versioned checkpoints, and legacy resume behavior |
| [`test_lifecycle.py`](test_lifecycle.py) | 5 | Run leases, stale recovery, interruption/resume, terminal release, and checkpoint cleanup |
| [`test_workspaces.py`](test_workspaces.py) | 9 | Run identity, Git worktree creation/reuse, local/remote branch listing and deletion, workspace context, and workspace state migration |
| [`test_viewer.py`](test_viewer.py) | 5 | Viewer HTML, execution-state data, checkpoint sharing, and Mermaid output |
| [`test_quality_gates.py`](test_quality_gates.py) | 9 | Quality command definitions, safe diff refs, numstat parsing, generated-output handling, diff limits, and gate failure reporting |
| [`test_fault_injection.py`](test_fault_injection.py) | 7 | Injected Git, GitHub, validation, checkpoint, and agent process failures |
| [`test_git_integration.py`](test_git_integration.py) | 2 | Real temporary Git repositories, worktrees, commits, pushes, PR creation/reuse, and fake-`gh` recovery |
| [`test_agent_integration.py`](test_agent_integration.py) | 2 | Real Codex and Claude CLI smoke tests against a small deterministic project (opt-in) |
| [`../hooks/test-guard.sh`](../hooks/test-guard.sh) | 8 shell checks | Dangerous-command blocking and safe-command allowlisting |

### CLI diagnostics

- `test_cli.py` verifies healthy doctor output and non-zero results for invalid
  mode, lease, retention, and checkpoint configuration, and for a Git or gh
  version below the supported minimum.

### Run management

- `test_cli.py` verifies run listing, checkpoint status, resume and cancellation
  requests, stale-lease recovery, checkpoint cleanup, safe removal guards, and
  the `runs prune` dry-run report and orphan worktree/branch removal.
- `test_workspaces.py` verifies local and remote run-branch listing and the
  development-mode, protected-branch, and run-scope guards on remote branch
  deletion.

## Workflow orchestration

Sources: [`test_graph.py`](test_graph.py), with graph topology assertions also
in [`test_viewer.py`](test_viewer.py).

### Entry, intake, and item routing

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

## Guardrails, hooks, and command safety

Sources: [`test_node_contracts.py`](test_node_contracts.py) and
[`../hooks/test-guard.sh`](../hooks/test-guard.sh).

### Process and workspace boundaries

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
- Structured debugger JSON is mapped to status, root cause, builder
  instructions, and feedback.
- Debugger requests include the validation failure and item description.

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
  state, and displays checkpoint history and the run manifest.
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
- Structured labels and visual classes are applied to main, decision, and
  highlighted nodes, including Intake, Preflight, Learn codebase, Build,
  Validate, commit item, GitHub, and the item router.
- Detailed rendering exposes the main and recovery sections and their links.
- Invalid or unintended edges are excluded, including direct GitHub-to-debugger
  routing, validation-to-debugger dashed styling, critic-to-validation or
  critic-to-item-router edges, self-loops, and direct building-to-end edges.
