# Graph Report - shanks  (2026-08-10)

## Corpus Check
- 50 files · ~45,757 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 967 nodes · 2526 edges · 50 communities (44 shown, 6 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 232 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `091fd9a8`
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

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 99 edges
2. `NodeDependencies` - 84 edges
3. `AgentRequest` - 77 edges
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

## Communities (50 total, 6 thin omitted)

### Community 0 - "AgentResult"
Cohesion: 0.09
Nodes (26): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep the legacy test-double API covered while the graph splits handoffs., Keep graph tests isolated from the shared production checkpoint store. (+18 more)

### Community 1 - "GitHubAdapter"
Cohesion: 0.23
Nodes (5): StateSchemaTests, migrate_state(), Raised when persisted state cannot be migrated safely., Upgrade persisted state to the current schema without mutating it., StateSchemaError

### Community 2 - "RunWorkspaceManager"
Cohesion: 0.08
Nodes (30): GitHubIntegrationTests, Path, FakeWorkspaceManager, Path, WorkspaceTests, _command_error(), _git_environment(), _normalize_component() (+22 more)

### Community 3 - "serve_graph.py"
Cohesion: 0.06
Nodes (37): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+29 more)

### Community 4 - "cli.py"
Cohesion: 0.09
Nodes (60): Namespace, _add_action_options(), _add_runtime_options(), _apply(), _build_graph(), _build_parser(), _cancel(), _check_authentication() (+52 more)

### Community 5 - "graph.py"
Cohesion: 0.09
Nodes (41): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+33 more)

### Community 6 - "run_quality_gates"
Cohesion: 0.12
Nodes (22): _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat(), _parser(), ArgumentParser (+14 more)

### Community 7 - "WorkflowState"
Cohesion: 0.14
Nodes (26): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+18 more)

### Community 8 - "Test coverage"
Cohesion: 0.06
Nodes (31): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, CLI diagnostics, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing (+23 more)

### Community 9 - "AgentRequest"
Cohesion: 0.18
Nodes (10): _critic_request(), _critic_result(), _debugger_request(), _debugger_result(), _parse_json_object(), Parse a JSON object even when the CLI adds non-JSON log lines., Add the shared read-only audit instructions to a critic request., Give the debugger failure evidence and a read-only analysis mandate. (+2 more)

### Community 10 - "During the session"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 11 - "classify_failure"
Cohesion: 0.05
Nodes (17): NodeContractTests, _attach_commands(), _audit_command(), GitHubAdapter, _preflight_failure(), _pull_request_names(), _pull_request_number(), Push and open a PR for callers that do not need approval boundaries. (+9 more)

### Community 12 - "main"
Cohesion: 0.19
Nodes (5): _FakeGraph, Path, ShanksCliTests, main(), Run the Shanks configuration or run-management command.

### Community 13 - "RunLifecycleManager"
Cohesion: 0.26
Nodes (7): Path, Real-CLI smoke tests for the Codex and Claude adapters.  Opt-in and skipped by d, RealAgentSmokeTests, ClaudeAdapter, CodexAdapter, Adapter for direct Codex CLI execution., Adapter for direct Claude Code CLI execution.

### Community 14 - "migrate_state"
Cohesion: 0.15
Nodes (12): TypedDict, Interface for local commits and the final GitHub handoff., RepositoryAdapter, _item_complete(), item_router(), _mark_current_item_built(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation. (+4 more)

### Community 15 - "ValueError"
Cohesion: 0.27
Nodes (7): Connection, ValueError, _branch_values(), _policy_values(), Normalize protected branch names and reject unsafe refs early., Normalize and deduplicate configured reviewer or label names., _validate_policy_values()

### Community 16 - "state.py"
Cohesion: 0.13
Nodes (20): acceptance_criteria_for_item(), append_run_manifest(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5(), _migrate_v5_to_v6() (+12 more)

### Community 17 - "nodes.py"
Cohesion: 0.12
Nodes (19): RunnableConfig, _debugger_details(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Format new debugger findings for the current PRD requirement. (+11 more)

### Community 18 - "create_nodes"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 19 - "default_dependencies"
Cohesion: 0.12
Nodes (19): Protocol, ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter, AgentAdapter (+11 more)

### Community 20 - "RunLifecycleManager"
Cohesion: 0.19
Nodes (7): dependencies(), LifecycleTests, Mark expired leases as abandoned without taking ownership., Delete old terminal or abandoned lifecycle records and leases., Coordinate one active owner and durable status for each run., Serialize checkpoint and lifecycle transactions on this connection., RunLifecycleManager

### Community 21 - "github_node"
Cohesion: 0.18
Nodes (17): Remove common credentials before command output enters workflow state., redact_secrets(), is_dry_run(), Return whether side-effecting delivery actions should be previewed., _approval_denied(), commit_item(), github_node(), _preview_repository_action() (+9 more)

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
Cohesion: 0.20
Nodes (5): _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

### Community 28 - "lifecycle.py"
Cohesion: 0.21
Nodes (9): LeaseLostError, RuntimeError, Persistent run leases and lifecycle records., Read a persisted lifecycle record., Return lifecycle records, marking expired active runs first., Raised when a process tries to heartbeat a lease it no longer owns., Persisted lifecycle summary for a checkpoint thread., _record() (+1 more)

### Community 29 - "contracts.py"
Cohesion: 0.12
Nodes (18): Exception, FailureClass, NodeError, agent_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError. (+10 more)

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
Cohesion: 0.13
Nodes (10): _checkpoint_timestamp(), CheckpointCleanup, _migrate_checkpoint_tuple(), _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup., Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes. (+2 more)

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
Cohesion: 0.16
Nodes (11): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback. (+3 more)

### Community 48 - "Path"
Cohesion: 0.18
Nodes (9): CheapCriticAdapter, _command_path_arguments(), DebuggerAdapter, _path_within_any(), Path, Agent adapter implementations for graph nodes and external runners., Deterministic low-cost critic used by the default graph., Analyze validation failures with a read-only structured Codex run. (+1 more)

### Community 49 - ".run"
Cohesion: 0.22
Nodes (8): _agent_environment(), _estimate_tokens(), _format_request(), Keep GitHub credentials out of agent and test subprocesses., Create a stable prompt envelope for CLI-backed adapters., Use a conservative four-characters-per-token estimate for CLI text., current_workspace_directory(), Return the workspace for the current graph invocation, if any.

## Knowledge Gaps
- **109 isolated node(s):** `graphify-update.sh script`, `guard-dependency-files.sh script`, `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR` (+104 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `AgentResult` to `GitHubAdapter`, `RunWorkspaceManager`, `.cleanup`, `cli.py`, `graph.py`, `RalphAdapter`, `WorkflowState`, `classify_failure`, `RunLifecycleManager`, `migrate_state`, `Path`, `nodes.py`, `create_nodes`, `default_dependencies`, `RunLifecycleManager`, `github_node`, `RalphAdapter`, `lifecycle.py`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `RunWorkspaceManager` connect `RunWorkspaceManager` to `AgentResult`, `.cleanup`, `cli.py`, `graph.py`, `main`, `nodes.py`, `create_nodes`, `default_dependencies`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `AgentResult` to `RunWorkspaceManager`, `graph.py`, `RalphAdapter`, `WorkflowState`, `AgentRequest`, `classify_failure`, `RunLifecycleManager`, `migrate_state`, `Path`, `.run`, `nodes.py`, `default_dependencies`, `github_node`, `RalphAdapter`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `AgentRequest` (e.g. with `RealAgentSmokeTests` and `ExplodingBuilder`) actually correct?**
  _`AgentRequest` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `GitHubAdapter` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`GitHubAdapter` has 8 INFERRED edges - model-reasoned connections that need verification._