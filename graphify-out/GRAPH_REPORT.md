# Graph Report - shanks  (2026-08-07)

## Corpus Check
- 43 files · ~34,041 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 763 nodes · 1901 edges · 41 communities (37 shown, 4 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 205 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `06f8bf75`
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
- state_update_from_result
- _migrate_checkpoint_tuple

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 84 edges
2. `NodeDependencies` - 83 edges
3. `AgentRequest` - 72 edges
4. `WorkflowState` - 65 edges
5. `StubAgentAdapter` - 53 edges
6. `NodeContractTests` - 52 edges
7. `GraphRoutingTests` - 42 edges
8. `GitHubAdapter` - 42 edges
9. `build_graph()` - 35 edges
10. `build_graph()` - 32 edges

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

## Communities (41 total, 4 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.11
Nodes (22): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., RecordingRepository (+14 more)

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
Nodes (23): TypedDict, building(), _current_item(), _item_complete(), item_router(), _mark_current_item_built(), _mark_current_item_validated(), _merge_files() (+15 more)

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
Cohesion: 0.10
Nodes (15): _critic_request(), _debugger_request(), _format_request(), RalphAdapter, Run a configured CLI backend through the common adapter contract., Normalize a read-only CLI critic into the common agent result shape., Add the shared read-only audit instructions to a critic request., Give the debugger failure evidence and a read-only analysis mandate. (+7 more)

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
Cohesion: 0.10
Nodes (19): Protocol, ClaudeAdapter, ClaudeOpus48CriticAdapter, DebuggerAdapter, GPT56LunaCriticAdapter, Adapter for direct Claude Code CLI execution., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent. (+11 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.12
Nodes (5): NodeContractTests, _attach_commands(), GitHubAdapter, Keep the full command trail when a multi-command operation fails., Commit validated items, then push the branch and open its PR.

### Community 23 - "WorkflowState"
Cohesion: 0.33
Nodes (4): Common interfaces shared by agent adapters and graph nodes., Interface for local commits and the final GitHub handoff., RepositoryAdapter, Reusable workflow state, agent contracts, adapters, and nodes.

### Community 24 - "Test coverage"
Cohesion: 0.07
Nodes (28): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+20 more)

### Community 25 - "graph.py"
Cohesion: 0.15
Nodes (18): Any, acceptance_criteria_for_item(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5(), _migrate_v5_to_v6() (+10 more)

### Community 26 - "nodes.py"
Cohesion: 0.18
Nodes (13): RunnableConfig, _invalid_budget(), _nonnegative_float(), _nonnegative_int(), Standardized LangGraph node implementations., Return the first configured cancellation or budget stop reason., Reject malformed limits instead of silently running without guardrails., Return a terminal state update without invoking another backend. (+5 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.16
Nodes (13): Exception, FailureClass, Classify failures at the shared adapter boundary., classify_failure(), BaseException, Failure classification and bounded retry helpers., Use the same classifier for LangGraph's native node retry policy., Classify a failure before deciding whether it is safe to retry. (+5 more)

### Community 28 - "create_nodes"
Cohesion: 0.23
Nodes (5): StateSchemaTests, migrate_state(), Upgrade persisted state to the current schema without mutating it., Raised when persisted state cannot be migrated safely., StateSchemaError

### Community 29 - "Any"
Cohesion: 0.09
Nodes (30): FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, execution_mode(), is_development_mode(), Explicit execution modes for local development and normal runs., Return the configured mode, failing closed for unknown values. (+22 more)

### Community 30 - "RalphAdapter"
Cohesion: 0.21
Nodes (7): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run an item's validation command or the full local suite as a fallback.

### Community 31 - "planning"
Cohesion: 0.09
Nodes (35): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+27 more)

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 33 - "_apply_failure_policy"
Cohesion: 0.40
Nodes (5): _debugger_details(), _default_plan(), planning(), Format new debugger findings for the current PRD requirement., Plan the current incomplete item without losing retry context.

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.16
Nodes (8): _checkpoint_timestamp(), CheckpointCleanup, _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver

### Community 35 - "build_error_handler"
Cohesion: 0.24
Nodes (10): NodeError, agent_error_handler(), build_error_handler(), _exception_failure_class(), BaseException, Route an exhausted native build-node failure to the terminal path., Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError. (+2 more)

### Community 36 - "DebuggerAdapter"
Cohesion: 0.09
Nodes (24): ValueError, _audit_command(), CheapCriticAdapter, CodexAdapter, _command_path_arguments(), _critic_result(), _debugger_result(), _estimate_tokens() (+16 more)

### Community 37 - "DebuggerAdapter"
Cohesion: 0.17
Nodes (15): Remove common credentials before command output enters workflow state., redact_secrets(), _approval_denied(), _audit_result(), commit_item(), github_node(), _pull_request_id(), Push the completed branch and create its pull request. (+7 more)

### Community 38 - "CheapCriticAdapter"
Cohesion: 0.08
Nodes (26): Connection, dependencies(), LifecycleTests, LeaseLostError, _lifecycle_status(), RuntimeError, Persistent run leases and lifecycle records., Extend the current owner's lease before another node runs. (+18 more)

### Community 39 - "state_update_from_result"
Cohesion: 0.21
Nodes (12): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), critic_auditor(), debugger(), learning(), preflight(), Record a failure and schedule only safe transient retries. (+4 more)

## Knowledge Gaps
- **94 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+89 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `CheapCriticAdapter`, `GraphRequestHandler`, `CheapCriticAdapter`, `_apply_failure_policy`, `DebuggerAdapter`, `VersionedSqliteSaver`, `CheapCriticAdapter`, `DebuggerAdapter`, `state_update_from_result`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `nodes.py`, `create_nodes`, `Any`, `RalphAdapter`, `planning`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `DebuggerAdapter`, `VersionedSqliteSaver`, `DebuggerAdapter`, `state_update_from_result`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `nodes.py`, `RepositoryAdapter`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `GitHubAdapter` to `NodeDependencies`, `DebuggerAdapter`, `VersionedSqliteSaver`, `DebuggerAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `nodes.py`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `WorkflowState` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`WorkflowState` has 7 INFERRED edges - model-reasoned connections that need verification._