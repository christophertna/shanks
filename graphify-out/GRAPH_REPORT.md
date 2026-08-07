# Graph Report - shanks  (2026-08-07)

## Corpus Check
- 42 files · ~32,728 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 736 nodes · 1824 edges · 42 communities (39 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 191 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c2794eb5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NodeDependencies
- GraphRequestHandler
- nodes.py
- Shanks
- ralph.sh
- VersionedSqliteSaver
- Ralph Agent Instructions
- GitHub Commits and PRs
- Ralph Agent Instructions (Codex)
- AGENTS.md
- CLAUDE.md
- critic_output.schema.json
- GitHubAdapter
- NodeContractTests
- GitHub Commits and PRs
- .__init__
- RepositoryAdapter
- adapters.py
- test-guard.sh
- GitHubAdapter
- WorkflowState
- Test coverage
- graph.py
- nodes.py
- RepositoryAdapter
- create_nodes
- Any
- RalphAdapter
- planning
- CheapCriticAdapter
- _apply_failure_policy
- CheapCriticAdapter
- build_error_handler
- DebuggerAdapter
- DebuggerAdapter
- CheapCriticAdapter
- .cleanup
- CodexAdapter
- RepositoryAdapter

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 84 edges
2. `NodeDependencies` - 79 edges
3. `AgentRequest` - 72 edges
4. `WorkflowState` - 64 edges
5. `StubAgentAdapter` - 53 edges
6. `NodeContractTests` - 52 edges
7. `GitHubAdapter` - 42 edges
8. `GraphRoutingTests` - 41 edges
9. `build_graph()` - 34 edges
10. `build_graph()` - 32 edges

## Surprising Connections (you probably didn't know these)
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `VersionedSqliteSaver` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `VersionedSqliteSaver` --uses--> `RunWorkspaceManager`  [INFERRED]
  graph.py → workflow/workspaces.py
- `ExplodingBuilder` --uses--> `VersionedSqliteSaver`  [INFERRED]
  tests/test_fault_injection.py → graph.py
- `FaultInjectionTests` --uses--> `VersionedSqliteSaver`  [INFERRED]
  tests/test_fault_injection.py → graph.py

## Import Cycles
- None detected.

## Communities (42 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.14
Nodes (19): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., RecordingRepository (+11 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 2 - "nodes.py"
Cohesion: 0.12
Nodes (22): ArgumentParser, Runner, _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat() (+14 more)

### Community 3 - "Shanks"
Cohesion: 0.33
Nodes (5): Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.15
Nodes (8): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PRD_FILE, RALPH_PROJECT_DIR, RALPH_RUN_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.15
Nodes (29): TypedDict, Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), building(), critic_auditor(), _current_item(), debugger() (+21 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.22
Nodes (8): Directories, Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 10 - "CLAUDE.md"
Cohesion: 0.33
Nodes (5): Commands, Gotchas, graphify, Project overview, Repo etiquette

### Community 11 - "critic_output.schema.json"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 12 - "GitHubAdapter"
Cohesion: 0.18
Nodes (5): _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

### Community 13 - "NodeContractTests"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 15 - "GitHub Commits and PRs"
Cohesion: 0.29
Nodes (6): Commit, push, and PR checks, Commit subject, GitHub Commits and PRs, Merge authority, Pull request description, Pull request title

### Community 17 - ".__init__"
Cohesion: 0.12
Nodes (15): builder_instructions, root_cause, additionalProperties, minLength, type, type, properties, builder_instructions (+7 more)

### Community 19 - "adapters.py"
Cohesion: 0.09
Nodes (21): ClaudeAdapter, ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Adapter for direct Claude Code CLI execution., Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter (+13 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.11
Nodes (5): NodeContractTests, _attach_commands(), GitHubAdapter, Keep the full command trail when a multi-command operation fails., Commit validated items, then push the branch and open its PR.

### Community 23 - "WorkflowState"
Cohesion: 0.16
Nodes (11): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback. (+3 more)

### Community 24 - "Test coverage"
Cohesion: 0.07
Nodes (28): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+20 more)

### Community 25 - "graph.py"
Cohesion: 0.14
Nodes (13): _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5(), Shared state types for the graph-engineering workflow., Mark an unversioned legacy state as the first supported schema., Add run budgets and clean-cancellation fields to persisted state. (+5 more)

### Community 26 - "nodes.py"
Cohesion: 0.17
Nodes (15): RunnableConfig, _invalid_budget(), _nonnegative_float(), _nonnegative_int(), Standardized LangGraph node implementations., Return the first configured cancellation or budget stop reason., Reject malformed limits instead of silently running without guardrails., Return a terminal state update without invoking another backend. (+7 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.18
Nodes (10): Exception, FailureClass, Classify failures at the shared adapter boundary., classify_failure(), BaseException, Use the same classifier for LangGraph's native node retry policy., Classify a failure before deciding whether it is safe to retry., Return a deterministic exponential delay for the next retry. (+2 more)

### Community 28 - "create_nodes"
Cohesion: 0.15
Nodes (11): ValueError, _critic_result(), _debugger_request(), _debugger_result(), DebuggerAdapter, _parse_json_object(), Parse a JSON object even when the CLI adds non-JSON log lines., Give the debugger failure evidence and a read-only analysis mandate. (+3 more)

### Community 29 - "Any"
Cohesion: 0.11
Nodes (22): FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, _command_error(), _git_environment(), _normalize_component(), CompletedProcess (+14 more)

### Community 30 - "RalphAdapter"
Cohesion: 0.15
Nodes (9): _lifecycle_status(), Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease., Release the lease after its terminal checkpoint is persisted., Mark expired leases as abandoned without taking ownership., Delete old terminal or abandoned lifecycle records and leases., The result of acquiring or renewing a run lease., Acquire or renew a lease, recovering it when its owner is stale. (+1 more)

### Community 31 - "planning"
Cohesion: 0.10
Nodes (33): build_graph(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer(), agent_error_handler_for(), Bind a graph node name while preserving LangGraph error injection. (+25 more)

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Migrate state, enforce run budgets, and stamp every checkpoint., Create state-only node callables with injected agent backends. (+9 more)

### Community 33 - "_apply_failure_policy"
Cohesion: 0.17
Nodes (15): Remove common credentials before command output enters workflow state., redact_secrets(), _approval_denied(), _audit_result(), commit_item(), github_node(), _pull_request_id(), Pause until a human explicitly approves or rejects a side effect. (+7 more)

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.14
Nodes (8): _migrate_checkpoint_tuple(), Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver, StateSchemaTests, migrate_state(), Upgrade persisted state to the current schema without mutating it.

### Community 35 - "build_error_handler"
Cohesion: 0.15
Nodes (15): Any, NodeError, agent_error_handler(), build_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError. (+7 more)

### Community 36 - "DebuggerAdapter"
Cohesion: 0.14
Nodes (17): _audit_command(), _command_path_arguments(), _critic_request(), _estimate_tokens(), _format_request(), _path_within_any(), _preflight_failure(), Path (+9 more)

### Community 37 - "DebuggerAdapter"
Cohesion: 0.42
Nodes (4): dependencies(), LifecycleTests, Coordinate one active owner and durable status for each run., RunLifecycleManager

### Community 38 - "CheapCriticAdapter"
Cohesion: 0.19
Nodes (11): LeaseLostError, RuntimeError, Persistent run leases and lifecycle records., Raised when another live owner holds the run lease., Read a persisted lifecycle record., Raised when a process tries to heartbeat a lease it no longer owns., Return lifecycle records, marking expired active runs first., Persisted lifecycle summary for a checkpoint thread. (+3 more)

### Community 39 - ".cleanup"
Cohesion: 0.15
Nodes (11): _debugger_details(), _default_plan(), _item_complete(), item_router(), planning(), Format new debugger findings for the current PRD requirement., Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation. (+3 more)

### Community 40 - "CodexAdapter"
Cohesion: 0.20
Nodes (4): CheapCriticAdapter, CodexAdapter, Adapter for direct Codex CLI execution., Deterministic low-cost critic used by the default graph.

### Community 41 - "RepositoryAdapter"
Cohesion: 0.22
Nodes (6): Protocol, Push the branch and create its pull request., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., Commit one validated item's intended files., RepositoryAdapter

## Knowledge Gaps
- **94 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+89 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `CheapCriticAdapter`, `GraphRequestHandler`, `CheapCriticAdapter`, `_apply_failure_policy`, `DebuggerAdapter`, `VersionedSqliteSaver`, `.cleanup`, `CodexAdapter`, `RepositoryAdapter`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `create_nodes`, `Any`, `planning`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `_apply_failure_policy`, `DebuggerAdapter`, `VersionedSqliteSaver`, `CodexAdapter`, `RepositoryAdapter`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `nodes.py`, `RepositoryAdapter`, `create_nodes`, `Any`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `WorkflowState` to `NodeDependencies`, `_apply_failure_policy`, `DebuggerAdapter`, `VersionedSqliteSaver`, `CodexAdapter`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `nodes.py`, `create_nodes`, `Any`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 29 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `ExplodingBuilder`) actually correct?**
  _`NodeDependencies` has 29 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `WorkflowState` (e.g. with `VersionedSqliteSaver` and `AgentAdapter`) actually correct?**
  _`WorkflowState` has 6 INFERRED edges - model-reasoned connections that need verification._