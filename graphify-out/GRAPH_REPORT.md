# Graph Report - shanks  (2026-08-08)

## Corpus Check
- 47 files · ~39,697 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 862 nodes · 2166 edges · 49 communities (44 shown, 5 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 211 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ce7c1866`
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
- adapters.py
- nodes.py
- RepositoryAdapter
- create_nodes
- Any
- RalphAdapter
- planning
- CheapCriticAdapter
- _apply_failure_policy
- RalphAdapter
- build_error_handler
- DebuggerAdapter
- AGENTS.md
- CheapCriticAdapter
- lifecycle.py
- test_fault_injection.py
- migrate_state
- RunLifecycleManager
- ValueError
- _migrate_checkpoint_tuple

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 99 edges
2. `NodeDependencies` - 84 edges
3. `AgentRequest` - 72 edges
4. `GitHubAdapter` - 69 edges
5. `WorkflowState` - 66 edges
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
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py

## Import Cycles
- None detected.

## Communities (49 total, 5 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.12
Nodes (20): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., Keep the legacy test-double API covered while the graph splits handoffs. (+12 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.21
Nodes (4): _audit_command(), Return a redacted command suitable for the persisted run manifest., Check tools, branch state, GitHub auth, and the test environment., Describe the commit without staging or committing anything.

### Community 2 - "nodes.py"
Cohesion: 0.09
Nodes (27): GitHubIntegrationTests, Path, FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, _command_error(), current_workspace_directory() (+19 more)

### Community 3 - "Shanks"
Cohesion: 0.06
Nodes (39): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+31 more)

### Community 4 - "ralph.sh"
Cohesion: 0.17
Nodes (8): _lifecycle_status(), Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease., Release the lease after its terminal checkpoint is persisted., Mark expired leases as abandoned without taking ownership., The result of acquiring or renewing a run lease., Acquire or renew a lease, recovering it when its owner is stale., RunLease

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.09
Nodes (37): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+29 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.12
Nodes (24): ShanksCliTests, _check_authentication(), _check_checkpoint(), _check_dependencies(), _check_environment(), _check_mode(), _check_tools(), doctor_checks() (+16 more)

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.12
Nodes (22): ArgumentParser, _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat(), _parser() (+14 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.14
Nodes (32): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+24 more)

### Community 9 - "AGENTS.md"
Cohesion: 0.07
Nodes (29): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+21 more)

### Community 10 - "CLAUDE.md"
Cohesion: 0.14
Nodes (11): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback. (+3 more)

### Community 11 - "critic_output.schema.json"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 12 - "GitHubAdapter"
Cohesion: 0.09
Nodes (22): ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, DebuggerAdapter, GPT56LunaCriticAdapter, Adapter for direct Codex CLI execution., Adapter for direct Claude Code CLI execution., Normalize a read-only CLI critic into the common agent result shape. (+14 more)

### Community 13 - "NodeContractTests"
Cohesion: 0.13
Nodes (20): Any, acceptance_criteria_for_item(), append_run_manifest(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5() (+12 more)

### Community 14 - "AgentRequest"
Cohesion: 0.26
Nodes (3): CheapCriticAdapter, Path, Deterministic low-cost critic used by the default graph.

### Community 15 - "GitHub Commits and PRs"
Cohesion: 0.14
Nodes (16): RunnableConfig, _default_plan(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL. (+8 more)

### Community 16 - "grilling/SKILL.md"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 17 - ".__init__"
Cohesion: 0.12
Nodes (18): Exception, FailureClass, NodeError, agent_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError. (+10 more)

### Community 18 - "RepositoryAdapter"
Cohesion: 0.12
Nodes (15): builder_instructions, root_cause, additionalProperties, minLength, type, type, properties, builder_instructions (+7 more)

### Community 19 - "adapters.py"
Cohesion: 0.15
Nodes (8): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PRD_FILE, RALPH_PROJECT_DIR, RALPH_RUN_DIR, ralph.sh script, upsert_metadata()

### Community 20 - "skills/decisions/SKILL.md"
Cohesion: 0.16
Nodes (7): _attach_commands(), _pull_request_number(), Extract the number from a GitHub pull-request URL., Keep the full command trail when a multi-command operation fails., Describe the branch push without contacting the remote., Describe PR lookup/creation without changing GitHub., Push and open a PR for callers that do not need approval boundaries.

### Community 21 - "test-guard.sh"
Cohesion: 0.15
Nodes (11): TypedDict, Common interfaces shared by agent adapters and graph nodes., Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow. (+3 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.18
Nodes (17): Remove common credentials before command output enters workflow state., redact_secrets(), is_dry_run(), Return whether side-effecting delivery actions should be previewed., _approval_denied(), commit_item(), github_node(), _preview_repository_action() (+9 more)

### Community 23 - "main"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 24 - "Test coverage"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 25 - "adapters.py"
Cohesion: 0.12
Nodes (19): _command_path_arguments(), _critic_request(), _critic_result(), _debugger_request(), _debugger_result(), _estimate_tokens(), _parse_json_object(), _path_within_any() (+11 more)

### Community 26 - "nodes.py"
Cohesion: 0.14
Nodes (3): NodeContractTests, GitHubAdapter, Commit validated items, then reconcile the branch's pull request.

### Community 27 - "RepositoryAdapter"
Cohesion: 0.25
Nodes (5): _checkpoint_timestamp(), CheckpointCleanup, _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup.

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

### Community 34 - "RalphAdapter"
Cohesion: 0.14
Nodes (7): _format_request(), _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Create a stable prompt envelope for CLI-backed adapters., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

### Community 42 - "lifecycle.py"
Cohesion: 0.21
Nodes (9): LeaseLostError, RuntimeError, Persistent run leases and lifecycle records., Read a persisted lifecycle record., Return lifecycle records, marking expired active runs first., Raised when a process tries to heartbeat a lease it no longer owns., Persisted lifecycle summary for a checkpoint thread., _record() (+1 more)

### Community 43 - "test_fault_injection.py"
Cohesion: 0.15
Nodes (8): Protocol, Commit one validated item's intended files., Push the validated branch without opening a pull request., Open or reuse the pull request for an already-pushed branch., Push the branch and reconcile its pull request lifecycle., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., RepositoryAdapter

### Community 44 - "migrate_state"
Cohesion: 0.26
Nodes (5): StateSchemaTests, migrate_state(), Raised when persisted state cannot be migrated safely., Upgrade persisted state to the current schema without mutating it., StateSchemaError

### Community 45 - "RunLifecycleManager"
Cohesion: 0.18
Nodes (10): SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver, dependencies(), LifecycleTests, Raised when another live owner holds the run lease., Coordinate one active owner and durable status for each run., Serialize checkpoint and lifecycle transactions on this connection. (+2 more)

### Community 47 - "ValueError"
Cohesion: 0.25
Nodes (5): Connection, ValueError, _policy_values(), Normalize and deduplicate configured reviewer or label names., Delete old terminal or abandoned lifecycle records and leases.

## Knowledge Gaps
- **103 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentResult` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `RalphAdapter`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `test_fault_injection.py`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `skills/decisions/SKILL.md`, `test-guard.sh`, `GitHubAdapter`, `adapters.py`, `nodes.py`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `Shanks`, `RalphAdapter`, `VersionedSqliteSaver`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `test_fault_injection.py`, `migrate_state`, `RunLifecycleManager`, `GitHubAdapter`, `GitHub Commits and PRs`, `grilling/SKILL.md`, `lifecycle.py`, `test-guard.sh`, `GitHubAdapter`, `nodes.py`, `RepositoryAdapter`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Why does `GitHubAdapter` connect `nodes.py` to `NodeDependencies`, `GraphRequestHandler`, `nodes.py`, `CLAUDE.md`, `GitHubAdapter`, `ValueError`, `GitHub Commits and PRs`, `skills/decisions/SKILL.md`, `adapters.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `GitHubAdapter` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`GitHubAdapter` has 8 INFERRED edges - model-reasoned connections that need verification._