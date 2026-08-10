# Graph Report - shanks  (2026-08-09)

## Corpus Check
- 47 files · ~44,398 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 948 nodes · 2479 edges · 49 communities (45 shown, 4 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 229 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `96fde15d`
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
- adapters.py
- github_node
- debugger_output.schema.json
- ralph.sh
- ._setup
- critic_output.schema.json
- Ralph Agent Instructions
- PRDItem
- lifecycle.py
- contracts.py
- current_workspace_directory
- Ponytail
- Ralph Agent Instructions (Codex)
- lifecycle.py
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
- DebuggerAdapter

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 99 edges
2. `NodeDependencies` - 84 edges
3. `AgentRequest` - 73 edges
4. `GitHubAdapter` - 72 edges
5. `WorkflowState` - 67 edges
6. `NodeContractTests` - 60 edges
7. `StubAgentAdapter` - 53 edges
8. `RunWorkspaceManager` - 49 edges
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

## Communities (49 total, 4 thin omitted)

### Community 0 - "AgentResult"
Cohesion: 0.09
Nodes (25): Command, _dependencies(), ExplodingBuilder, _initial_state(), build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals() (+17 more)

### Community 1 - "GitHubAdapter"
Cohesion: 0.06
Nodes (17): _attach_commands(), _branch_values(), GitHubAdapter, _preflight_failure(), _pull_request_names(), _pull_request_number(), Push and open a PR for callers that do not need approval boundaries., Normalize protected branch names and reject unsafe refs early. (+9 more)

### Community 2 - "RunWorkspaceManager"
Cohesion: 0.07
Nodes (34): GitHubIntegrationTests, Path, FakeWorkspaceManager, Path, WorkspaceTests, is_development_mode(), Explicit execution modes for local development and normal runs., Return whether local development side effects are explicitly enabled. (+26 more)

### Community 3 - "serve_graph.py"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 4 - "cli.py"
Cohesion: 0.11
Nodes (53): Namespace, _add_action_options(), _add_runtime_options(), _apply(), _build_graph(), _build_parser(), _cancel(), _check_authentication() (+45 more)

### Community 5 - "graph.py"
Cohesion: 0.09
Nodes (39): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+31 more)

### Community 6 - "run_quality_gates"
Cohesion: 0.11
Nodes (25): _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat(), _parser(), ArgumentParser (+17 more)

### Community 7 - "WorkflowState"
Cohesion: 0.13
Nodes (34): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+26 more)

### Community 8 - "Test coverage"
Cohesion: 0.06
Nodes (31): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, CLI diagnostics, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing (+23 more)

### Community 9 - "AgentRequest"
Cohesion: 0.15
Nodes (8): Protocol, Commit one validated item's intended files., Push the validated branch without opening a pull request., Open or reuse the pull request for an already-pushed branch., Push the branch and reconcile its pull request lifecycle., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., RepositoryAdapter

### Community 10 - "During the session"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 11 - "classify_failure"
Cohesion: 0.22
Nodes (7): CheapCriticAdapter, CodexAdapter, Adapter for direct Codex CLI execution., Deterministic low-cost critic used by the default graph., AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles., Run the backend for one workflow node invocation.

### Community 12 - "main"
Cohesion: 0.26
Nodes (4): Path, ShanksCliTests, main(), Run the Shanks configuration or run-management command.

### Community 13 - "RunLifecycleManager"
Cohesion: 0.20
Nodes (6): Connection, dependencies(), LifecycleTests, Coordinate one active owner and durable status for each run., Serialize checkpoint and lifecycle transactions on this connection., RunLifecycleManager

### Community 14 - "migrate_state"
Cohesion: 0.23
Nodes (5): StateSchemaTests, migrate_state(), Raised when persisted state cannot be migrated safely., Upgrade persisted state to the current schema without mutating it., StateSchemaError

### Community 15 - "ValueError"
Cohesion: 0.20
Nodes (7): _critic_request(), _parse_uncertainties(), Normalize a read-only CLI critic into the common agent result shape., Extract the builder's concise uncertainty bullets from Ralph output., Add the shared read-only audit instructions to a critic request., Persist the graph's full PRD before Ralph reads its next story., StructuredCriticAdapter

### Community 16 - "state.py"
Cohesion: 0.15
Nodes (18): acceptance_criteria_for_item(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5(), _migrate_v5_to_v6(), Any (+10 more)

### Community 17 - "nodes.py"
Cohesion: 0.12
Nodes (20): RunnableConfig, Remove common credentials before command output enters workflow state., redact_secrets(), _default_plan(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id() (+12 more)

### Community 18 - "create_nodes"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 19 - "default_dependencies"
Cohesion: 0.12
Nodes (14): NodeContractTests, ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, RalphAdapter, Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., Adapter for the project-local Ralph runner., claude_opus_4_8_dependencies() (+6 more)

### Community 20 - "adapters.py"
Cohesion: 0.13
Nodes (18): _agent_environment(), _audit_command(), _command_path_arguments(), _critic_result(), _debugger_result(), _estimate_tokens(), _format_request(), _parse_json_object() (+10 more)

### Community 21 - "github_node"
Cohesion: 0.25
Nodes (11): is_dry_run(), Return whether side-effecting delivery actions should be previewed., _approval_denied(), commit_item(), _preview_repository_action(), pull_request_node(), Request approval, then open or reuse the pull request., Pause for human approval before every side effect. (+3 more)

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

### Community 27 - "PRDItem"
Cohesion: 0.15
Nodes (13): TypedDict, Common interfaces shared by agent adapters and graph nodes., Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), _mark_current_item_built(), _mark_current_item_validated(), Select the first item that is not both built and validated. (+5 more)

### Community 28 - "lifecycle.py"
Cohesion: 0.22
Nodes (7): Mark expired leases as abandoned without taking ownership., Read a persisted lifecycle record., Return lifecycle records, marking expired active runs first., Delete old terminal or abandoned lifecycle records and leases., Persisted lifecycle summary for a checkpoint thread., _record(), RunRecord

### Community 29 - "contracts.py"
Cohesion: 0.12
Nodes (18): Exception, FailureClass, NodeError, agent_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError. (+10 more)

### Community 30 - "current_workspace_directory"
Cohesion: 0.29
Nodes (3): ClaudeAdapter, Path, Adapter for direct Claude Code CLI execution.

### Community 31 - "Ponytail"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 32 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.22
Nodes (8): Directories, Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 33 - "lifecycle.py"
Cohesion: 0.20
Nodes (5): _FakeGraph, LeaseLostError, RuntimeError, Persistent run leases and lifecycle records., Raised when a process tries to heartbeat a lease it no longer owns.

### Community 34 - "GitHub Commits and PRs"
Cohesion: 0.22
Nodes (8): Commit, push, and PR checks, Commit subject, Documentation synchronization, GitHub Commits and PRs, Merge authority, Post-open merge monitoring, Pull request description, Pull request title

### Community 35 - ".cleanup"
Cohesion: 0.13
Nodes (11): _checkpoint_timestamp(), CheckpointCleanup, _migrate_checkpoint_tuple(), _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup., Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes. (+3 more)

### Community 36 - "GitHub Commits and PRs"
Cohesion: 0.22
Nodes (8): Commit, push, and PR checks, Commit subject, Documentation synchronization, GitHub Commits and PRs, Merge authority, Post-open merge monitoring, Pull request description, Pull request title

### Community 37 - "Shanks"
Cohesion: 0.29
Nodes (6): Commands, Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks

### Community 38 - "CLAUDE.md"
Cohesion: 0.33
Nodes (5): Commands, Gotchas, graphify, Project overview, Repo etiquette

### Community 39 - "RalphAdapter"
Cohesion: 0.16
Nodes (7): FaultInjectionTests, LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback., SubprocessAgentAdapter, AgentRequest, Structured input passed to any agent backend.

### Community 48 - "DebuggerAdapter"
Cohesion: 0.33
Nodes (4): _debugger_request(), DebuggerAdapter, Give the debugger failure evidence and a read-only analysis mandate., Analyze validation failures with a read-only structured Codex run.

## Knowledge Gaps
- **106 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+101 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `AgentResult` to `GitHubAdapter`, `RunWorkspaceManager`, `serve_graph.py`, `cli.py`, `graph.py`, `WorkflowState`, `AgentRequest`, `classify_failure`, `RunLifecycleManager`, `migrate_state`, `nodes.py`, `create_nodes`, `default_dependencies`, `github_node`, `PRDItem`, `current_workspace_directory`, `lifecycle.py`, `.cleanup`, `RalphAdapter`, `DebuggerAdapter`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `AgentResult` to `GitHubAdapter`, `RunWorkspaceManager`, `RalphAdapter`, `WorkflowState`, `AgentRequest`, `classify_failure`, `ValueError`, `DebuggerAdapter`, `nodes.py`, `default_dependencies`, `adapters.py`, `github_node`, `PRDItem`, `current_workspace_directory`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Why does `GitHubAdapter` connect `GitHubAdapter` to `AgentResult`, `RunWorkspaceManager`, `RalphAdapter`, `classify_failure`, `nodes.py`, `default_dependencies`, `adapters.py`?**
  _High betweenness centrality (0.074) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `GitHubAdapter` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`GitHubAdapter` has 8 INFERRED edges - model-reasoned connections that need verification._