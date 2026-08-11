# Graph Report - shanks  (2026-08-10)

## Corpus Check
- 55 files · ~47,502 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 993 nodes · 2557 edges · 54 communities (45 shown, 9 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 232 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3fb5642a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- AgentResult
- GitHubAdapter
- RunWorkspaceManager
- serve_graph.py
- cli.py
- graph.py
- run_quality_gates
- WorkflowState
- Test coverage
- AgentRequest
- During the session
- classify_failure
- main
- RunLifecycleManager
- migrate_state
- ValueError
- state.py
- nodes.py
- create_nodes
- default_dependencies
- RunLifecycleManager
- github_node
- debugger_output.schema.json
- ralph.sh
- ._setup
- critic_output.schema.json
- Ralph Agent Instructions
- RalphAdapter
- lifecycle.py
- contracts.py
- current_workspace_directory
- Ponytail
- Ralph Agent Instructions (Codex)
- guard-dependency-files.sh
- GitHub Commits and PRs
- .cleanup
- GitHub Commits and PRs
- Shanks
- CLAUDE.md
- RalphAdapter
- deny-dangerous.sh
- test-guard.sh
- AGENTS.md
- shanks
- Path
- .run
- sandbox_claude.sh
- .get_run
- RalphAdapter
- test-secret-scan.sh

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 99 edges
2. `NodeDependencies` - 84 edges
3. `AgentRequest` - 78 edges
4. `GitHubAdapter` - 72 edges
5. `WorkflowState` - 67 edges
6. `NodeContractTests` - 60 edges
7. `StubAgentAdapter` - 53 edges
8. `RunWorkspaceManager` - 52 edges
9. `GraphRoutingTests` - 47 edges
10. `build_graph()` - 39 edges

## Surprising Connections (you probably didn't know these)
- `CheckpointCleanup` --uses--> `RunLifecycleManager`  [INFERRED]
  graph.py → workflow/lifecycle.py
- `CheckpointCleanup` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `CheckpointCleanup` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `CheckpointCleanup` --uses--> `RunWorkspaceManager`  [INFERRED]
  graph.py → workflow/workspaces.py
- `VersionedSqliteSaver` --uses--> `RunLifecycleManager`  [INFERRED]
  graph.py → workflow/lifecycle.py

## Import Cycles
- None detected.

## Communities (54 total, 9 thin omitted)

### Community 0 - "AgentResult"
Cohesion: 0.07
Nodes (41): Command, Protocol, _dependencies(), ExplodingBuilder, _initial_state(), build_graph(), GraphRoutingTests, _initial_state() (+33 more)

### Community 1 - "GitHubAdapter"
Cohesion: 0.11
Nodes (12): _attach_commands(), _audit_command(), _pull_request_number(), Push and open a PR for callers that do not need approval boundaries., Extract the number from a GitHub pull-request URL., Remove common credentials before command output enters workflow state., Return a redacted command suitable for the persisted run manifest., Keep the full command trail when a multi-command operation fails. (+4 more)

### Community 2 - "RunWorkspaceManager"
Cohesion: 0.07
Nodes (33): GitHubIntegrationTests, Path, FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, _command_error(), current_workspace_directory() (+25 more)

### Community 3 - "serve_graph.py"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 4 - "cli.py"
Cohesion: 0.10
Nodes (56): Namespace, _add_action_options(), _add_runtime_options(), _apply(), _build_graph(), _build_parser(), _cancel(), _check_authentication() (+48 more)

### Community 5 - "graph.py"
Cohesion: 0.09
Nodes (37): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+29 more)

### Community 6 - "run_quality_gates"
Cohesion: 0.12
Nodes (22): _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat(), _parser(), ArgumentParser (+14 more)

### Community 7 - "WorkflowState"
Cohesion: 0.13
Nodes (32): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _approval_denied(), _audit_result(), critic_auditor(), _current_item(), debugger() (+24 more)

### Community 8 - "Test coverage"
Cohesion: 0.06
Nodes (32): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, CLI diagnostics, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing (+24 more)

### Community 9 - "AgentRequest"
Cohesion: 0.23
Nodes (5): StateSchemaTests, migrate_state(), Raised when persisted state cannot be migrated safely., Upgrade persisted state to the current schema without mutating it., StateSchemaError

### Community 10 - "During the session"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 11 - "classify_failure"
Cohesion: 0.10
Nodes (24): ValueError, _agent_environment(), _branch_values(), _command_path_arguments(), _critic_result(), _debugger_result(), _estimate_tokens(), _format_request() (+16 more)

### Community 12 - "main"
Cohesion: 0.25
Nodes (4): Path, ShanksCliTests, main(), Run the Shanks configuration or run-management command.

### Community 13 - "RunLifecycleManager"
Cohesion: 0.23
Nodes (10): Path, Real-CLI smoke tests for the Codex and Claude adapters.  Opt-in and skipped by d, RealAgentSmokeTests, ClaudeAdapter, CodexAdapter, Adapter for direct Codex CLI execution., Adapter for direct Claude Code CLI execution., AgentAdapter (+2 more)

### Community 14 - "migrate_state"
Cohesion: 0.09
Nodes (20): FaultInjectionTests, _critic_request(), _debugger_request(), DebuggerAdapter, LocalTestAdapter, _parse_uncertainties(), RalphAdapter, Run a configured CLI backend through the common adapter contract. (+12 more)

### Community 15 - "ValueError"
Cohesion: 0.29
Nodes (5): CompletedProcess, Behavioral tests for scripts/sandbox_claude.sh's write containment.  These exerc, _run(), SandboxClaudeContainmentTests, SandboxClaudeFallbackTests

### Community 16 - "state.py"
Cohesion: 0.15
Nodes (18): acceptance_criteria_for_item(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5(), _migrate_v5_to_v6(), Any (+10 more)

### Community 17 - "nodes.py"
Cohesion: 0.11
Nodes (21): RunnableConfig, building(), _invalid_budget(), _mark_current_item_built(), _merge_files(), _nonnegative_float(), _nonnegative_int(), _pull_request_id() (+13 more)

### Community 18 - "create_nodes"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 19 - "default_dependencies"
Cohesion: 0.13
Nodes (11): ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., claude_opus_4_8_dependencies(), default_dependencies(), gpt_5_6_luna_dependencies(), Path (+3 more)

### Community 20 - "RunLifecycleManager"
Cohesion: 0.24
Nodes (6): Connection, dependencies(), LifecycleTests, Coordinate one active owner and durable status for each run., Serialize checkpoint and lifecycle transactions on this connection., RunLifecycleManager

### Community 21 - "github_node"
Cohesion: 0.11
Nodes (3): NodeContractTests, GitHubAdapter, Commit validated items, then reconcile the branch's pull request.

### Community 22 - "debugger_output.schema.json"
Cohesion: 0.12
Nodes (15): builder_instructions, root_cause, additionalProperties, minLength, type, type, properties, builder_instructions (+7 more)

### Community 23 - "ralph.sh"
Cohesion: 0.15
Nodes (8): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PRD_FILE, RALPH_PROJECT_DIR, RALPH_RUN_DIR, ralph.sh script, upsert_metadata()

### Community 24 - "._setup"
Cohesion: 0.17
Nodes (8): _lifecycle_status(), Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease., Release the lease after its terminal checkpoint is persisted., Return whether a live lease currently protects ``run_id``., The result of acquiring or renewing a run lease., Acquire or renew a lease, recovering it when its owner is stale., RunLease

### Community 25 - "critic_output.schema.json"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 26 - "Ralph Agent Instructions"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 27 - "RalphAdapter"
Cohesion: 0.24
Nodes (10): NodeError, agent_error_handler(), build_error_handler(), _exception_failure_class(), BaseException, Route an exhausted native build-node failure to the terminal path., Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError. (+2 more)

### Community 28 - "lifecycle.py"
Cohesion: 0.18
Nodes (7): _FakeGraph, LeaseLostError, RuntimeError, Persistent run leases and lifecycle records., Raised when another live owner holds the run lease., Raised when a process tries to heartbeat a lease it no longer owns., RunBusyError

### Community 29 - "contracts.py"
Cohesion: 0.14
Nodes (14): Exception, FailureClass, Common interfaces shared by agent adapters and graph nodes., Classify failures at the shared adapter boundary., classify_failure(), BaseException, Failure classification and bounded retry helpers., Use the same classifier for LangGraph's native node retry policy. (+6 more)

### Community 31 - "Ponytail"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 32 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.22
Nodes (8): Directories, Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 34 - "GitHub Commits and PRs"
Cohesion: 0.22
Nodes (8): Commit, push, and PR checks, Commit subject, Documentation synchronization, GitHub Commits and PRs, Merge authority, Pull request description, Pull request lifecycle checkpoints, Pull request title

### Community 35 - ".cleanup"
Cohesion: 0.11
Nodes (11): _checkpoint_timestamp(), CheckpointCleanup, _migrate_checkpoint_tuple(), _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup., Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes. (+3 more)

### Community 36 - "GitHub Commits and PRs"
Cohesion: 0.22
Nodes (8): Commit, push, and PR checks, Commit subject, Documentation synchronization, GitHub Commits and PRs, Merge authority, Pull request description, Pull request lifecycle checkpoints, Pull request title

### Community 37 - "Shanks"
Cohesion: 0.25
Nodes (7): Commands, Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks, Supported toolchain

### Community 38 - "CLAUDE.md"
Cohesion: 0.33
Nodes (5): Commands, Gotchas, graphify, Project overview, Repo etiquette

### Community 39 - "RalphAdapter"
Cohesion: 0.18
Nodes (5): CheapCriticAdapter, _preflight_failure(), Path, Deterministic low-cost critic used by the default graph., Check tools, branch state, GitHub auth, and the test environment.

### Community 48 - "Path"
Cohesion: 0.20
Nodes (10): TypedDict, Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow., select_next_item() (+2 more)

### Community 51 - ".get_run"
Cohesion: 0.22
Nodes (7): Mark expired leases as abandoned without taking ownership., Read a persisted lifecycle record., Return lifecycle records, marking expired active runs first., Delete old terminal or abandoned lifecycle records and leases., Persisted lifecycle summary for a checkpoint thread., _record(), RunRecord

### Community 52 - "RalphAdapter"
Cohesion: 0.33
Nodes (5): Developer, Hooks, Other agents (critic, debugger), Ralph / build agents, Reference

## Knowledge Gaps
- **115 isolated node(s):** `graphify-update.sh script`, `guard-dependency-files.sh script`, `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR` (+110 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `AgentResult` to `RunWorkspaceManager`, `.cleanup`, `serve_graph.py`, `graph.py`, `WorkflowState`, `AgentRequest`, `RunLifecycleManager`, `migrate_state`, `Path`, `nodes.py`, `create_nodes`, `default_dependencies`, `RunLifecycleManager`, `github_node`, `lifecycle.py`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `RunWorkspaceManager` connect `RunWorkspaceManager` to `AgentResult`, `.cleanup`, `cli.py`, `graph.py`, `main`, `nodes.py`, `create_nodes`, `default_dependencies`, `lifecycle.py`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `AgentResult` to `GitHubAdapter`, `RunWorkspaceManager`, `RalphAdapter`, `WorkflowState`, `classify_failure`, `RunLifecycleManager`, `migrate_state`, `Path`, `nodes.py`, `default_dependencies`, `github_node`, `contracts.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `AgentRequest` (e.g. with `RealAgentSmokeTests` and `ExplodingBuilder`) actually correct?**
  _`AgentRequest` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `GitHubAdapter` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`GitHubAdapter` has 8 INFERRED edges - model-reasoned connections that need verification._