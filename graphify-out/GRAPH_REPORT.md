# Graph Report - shanks  (2026-08-07)

## Corpus Check
- 46 files · ~37,934 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 835 nodes · 2085 edges · 47 communities (42 shown, 5 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 209 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `677d973f`
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
- AgentRequest
- GitHub Commits and PRs
- grilling/SKILL.md
- .__init__
- RepositoryAdapter
- adapters.py
- skills/decisions/SKILL.md
- test-guard.sh
- GitHubAdapter
- main
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
- AGENTS.md
- CheapCriticAdapter
- state_update_from_result
- test_fault_injection.py
- AgentAdapter
- planning

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 99 edges
2. `NodeDependencies` - 84 edges
3. `AgentRequest` - 72 edges
4. `WorkflowState` - 66 edges
5. `GitHubAdapter` - 65 edges
6. `NodeContractTests` - 56 edges
7. `StubAgentAdapter` - 53 edges
8. `GraphRoutingTests` - 44 edges
9. `build_graph()` - 37 edges
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

## Communities (47 total, 5 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.10
Nodes (23): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., Keep the legacy test-double API covered while the graph splits handoffs. (+15 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.10
Nodes (18): _attach_commands(), _audit_command(), GitHubAdapter, _preflight_failure(), _pull_request_names(), _pull_request_number(), Extract case-insensitive label or reviewer names from gh JSON., Extract the number from a GitHub pull-request URL. (+10 more)

### Community 2 - "nodes.py"
Cohesion: 0.08
Nodes (32): ShanksCliTests, FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, main(), Small command-line helpers for inspecting Shanks configuration., Print the configured execution mode when requested. (+24 more)

### Community 3 - "Shanks"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 4 - "ralph.sh"
Cohesion: 0.17
Nodes (8): _lifecycle_status(), Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease., Release the lease after its terminal checkpoint is persisted., Read a persisted lifecycle record., The result of acquiring or renewing a run lease., Acquire or renew a lease, recovering it when its owner is stale., RunLease

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.09
Nodes (37): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+29 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.19
Nodes (6): Connection, _migrate_checkpoint_tuple(), Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.12
Nodes (22): ArgumentParser, Runner, _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat() (+14 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.14
Nodes (32): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+24 more)

### Community 9 - "AGENTS.md"
Cohesion: 0.07
Nodes (29): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+21 more)

### Community 10 - "CLAUDE.md"
Cohesion: 0.13
Nodes (13): _critic_request(), _debugger_request(), _format_request(), LocalTestAdapter, Add the shared read-only audit instructions to a critic request., Give the debugger failure evidence and a read-only analysis mandate., Create a stable prompt envelope for CLI-backed adapters., Persist the graph's full PRD before Ralph reads its next story. (+5 more)

### Community 11 - "critic_output.schema.json"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 12 - "GitHubAdapter"
Cohesion: 0.11
Nodes (15): ClaudeOpus48CriticAdapter, CodexAdapter, GPT56LunaCriticAdapter, Adapter for direct Codex CLI execution., Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter (+7 more)

### Community 13 - "NodeContractTests"
Cohesion: 0.13
Nodes (20): Any, acceptance_criteria_for_item(), append_run_manifest(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5() (+12 more)

### Community 14 - "AgentRequest"
Cohesion: 0.11
Nodes (20): ValueError, ClaudeAdapter, _command_path_arguments(), _critic_result(), _debugger_result(), _estimate_tokens(), _parse_json_object(), _parse_uncertainties() (+12 more)

### Community 15 - "GitHub Commits and PRs"
Cohesion: 0.11
Nodes (20): RunnableConfig, _default_plan(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL. (+12 more)

### Community 16 - "grilling/SKILL.md"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 17 - ".__init__"
Cohesion: 0.18
Nodes (11): Exception, FailureClass, Classify failures at the shared adapter boundary., classify_failure(), BaseException, Failure classification and bounded retry helpers., Use the same classifier for LangGraph's native node retry policy., Classify a failure before deciding whether it is safe to retry. (+3 more)

### Community 18 - "RepositoryAdapter"
Cohesion: 0.12
Nodes (15): builder_instructions, root_cause, additionalProperties, minLength, type, type, properties, builder_instructions (+7 more)

### Community 19 - "adapters.py"
Cohesion: 0.15
Nodes (8): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PRD_FILE, RALPH_PROJECT_DIR, RALPH_RUN_DIR, ralph.sh script, upsert_metadata()

### Community 20 - "skills/decisions/SKILL.md"
Cohesion: 0.21
Nodes (10): LeaseLostError, RuntimeError, Persistent run leases and lifecycle records., Raised when another live owner holds the run lease., Return lifecycle records, marking expired active runs first., Raised when a process tries to heartbeat a lease it no longer owns., Persisted lifecycle summary for a checkpoint thread., _record() (+2 more)

### Community 21 - "test-guard.sh"
Cohesion: 0.14
Nodes (15): TypedDict, Common interfaces shared by agent adapters and graph nodes., Interface for local commits and the final GitHub handoff., RepositoryAdapter, Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), Select the first item that is not both built and validated. (+7 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.24
Nodes (13): is_dry_run(), Return whether side-effecting delivery actions should be previewed., _approval_denied(), commit_item(), github_node(), _preview_repository_action(), pull_request_node(), Request approval, then push the completed branch. (+5 more)

### Community 23 - "main"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 24 - "Test coverage"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 25 - "graph.py"
Cohesion: 0.31
Nodes (5): dependencies(), LifecycleTests, Coordinate one active owner and durable status for each run., Serialize checkpoint and lifecycle transactions on this connection., RunLifecycleManager

### Community 26 - "nodes.py"
Cohesion: 0.08
Nodes (5): NodeContractTests, RalphAdapter, Run a configured CLI backend through the common adapter contract., Adapter for the project-local Ralph runner., SubprocessAgentAdapter

### Community 27 - "RepositoryAdapter"
Cohesion: 0.23
Nodes (5): StateSchemaTests, migrate_state(), Raised when persisted state cannot be migrated safely., Upgrade persisted state to the current schema without mutating it., StateSchemaError

### Community 28 - "create_nodes"
Cohesion: 0.25
Nodes (7): Commit, push, and PR checks, Commit subject, Documentation synchronization, GitHub Commits and PRs, Merge authority, Pull request description, Pull request title

### Community 29 - "Any"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 30 - "RalphAdapter"
Cohesion: 0.22
Nodes (8): Directories, Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 31 - "planning"
Cohesion: 0.29
Nodes (6): Commands, Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.25
Nodes (7): Commit, push, and PR checks, Commit subject, Documentation synchronization, GitHub Commits and PRs, Merge authority, Pull request description, Pull request title

### Community 33 - "_apply_failure_policy"
Cohesion: 0.33
Nodes (5): Commands, Gotchas, graphify, Project overview, Repo etiquette

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.33
Nodes (6): NodeError, agent_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError.

### Community 42 - "state_update_from_result"
Cohesion: 0.25
Nodes (5): _checkpoint_timestamp(), CheckpointCleanup, _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup.

### Community 43 - "test_fault_injection.py"
Cohesion: 0.25
Nodes (5): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state()

### Community 44 - "AgentAdapter"
Cohesion: 0.18
Nodes (8): Protocol, CheapCriticAdapter, DebuggerAdapter, Deterministic low-cost critic used by the default graph., Analyze validation failures with a read-only structured Codex run., AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles., Run the backend for one workflow node invocation.

## Knowledge Gaps
- **103 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentResult` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `test_fault_injection.py`, `GitHubAdapter`, `AgentAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `.__init__`, `test-guard.sh`, `GitHubAdapter`, `nodes.py`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `Shanks`, `VersionedSqliteSaver`, `Ralph Agent Instructions`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `grilling/SKILL.md`, `skills/decisions/SKILL.md`, `test-guard.sh`, `GitHubAdapter`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `state_update_from_result`, `test_fault_injection.py`, `AgentAdapter`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `GitHubAdapter` connect `GraphRequestHandler` to `NodeDependencies`, `CLAUDE.md`, `test_fault_injection.py`, `GitHubAdapter`, `AgentAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `nodes.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `WorkflowState` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`WorkflowState` has 7 INFERRED edges - model-reasoned connections that need verification._