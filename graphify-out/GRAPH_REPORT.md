# Graph Report - shanks  (2026-08-08)

## Corpus Check
- 47 files · ~38,870 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 845 nodes · 2124 edges · 42 communities (38 shown, 4 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 211 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `07a4605e`
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
- nodes.py
- RepositoryAdapter
- create_nodes
- Any
- RalphAdapter
- planning
- CheapCriticAdapter
- _apply_failure_policy
- build_error_handler
- DebuggerAdapter
- AGENTS.md
- CheapCriticAdapter
- test_fault_injection.py

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
- `VersionedSqliteSaver` --uses--> `RunLifecycleManager`  [INFERRED]
  graph.py → workflow/lifecycle.py

## Import Cycles
- None detected.

## Communities (42 total, 4 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.09
Nodes (28): Command, Protocol, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store. (+20 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.13
Nodes (9): _attach_commands(), _audit_command(), Return a redacted command suitable for the persisted run manifest., Keep the full command trail when a multi-command operation fails., Check tools, branch state, GitHub auth, and the test environment., Describe the commit without staging or committing anything., Describe the branch push without contacting the remote., Describe PR lookup/creation without changing GitHub. (+1 more)

### Community 2 - "nodes.py"
Cohesion: 0.10
Nodes (25): GitHubIntegrationTests, Path, FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, _command_error(), _git_environment() (+17 more)

### Community 3 - "Shanks"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 4 - "ralph.sh"
Cohesion: 0.08
Nodes (25): dependencies(), LifecycleTests, LeaseLostError, _lifecycle_status(), RuntimeError, Persistent run leases and lifecycle records., Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease. (+17 more)

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.09
Nodes (37): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+29 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.26
Nodes (6): ShanksCliTests, main(), Small command-line helpers for inspecting Shanks configuration., Print the configured execution mode when requested., execution_mode(), Return the configured mode, failing closed for unknown values.

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.11
Nodes (25): ArgumentParser, Runner, _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat() (+17 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.14
Nodes (32): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+24 more)

### Community 9 - "AGENTS.md"
Cohesion: 0.07
Nodes (29): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+21 more)

### Community 10 - "CLAUDE.md"
Cohesion: 0.08
Nodes (23): _critic_request(), _critic_result(), _debugger_request(), _debugger_result(), _format_request(), _parse_json_object(), RalphAdapter, Run a configured CLI backend through the common adapter contract. (+15 more)

### Community 11 - "critic_output.schema.json"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 12 - "GitHubAdapter"
Cohesion: 0.10
Nodes (20): ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, DebuggerAdapter, GPT56LunaCriticAdapter, Adapter for direct Codex CLI execution., Adapter for direct Claude Code CLI execution., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent. (+12 more)

### Community 13 - "NodeContractTests"
Cohesion: 0.13
Nodes (20): Any, acceptance_criteria_for_item(), append_run_manifest(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5() (+12 more)

### Community 14 - "AgentRequest"
Cohesion: 0.14
Nodes (12): CheapCriticAdapter, _command_path_arguments(), _estimate_tokens(), _parse_uncertainties(), _path_within_any(), _preflight_failure(), Path, Agent adapter implementations for graph nodes and external runners. (+4 more)

### Community 15 - "GitHub Commits and PRs"
Cohesion: 0.14
Nodes (16): RunnableConfig, _default_plan(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL. (+8 more)

### Community 16 - "grilling/SKILL.md"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 17 - ".__init__"
Cohesion: 0.11
Nodes (19): Exception, FailureClass, NodeError, Classify failures at the shared adapter boundary., agent_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely. (+11 more)

### Community 18 - "RepositoryAdapter"
Cohesion: 0.12
Nodes (15): builder_instructions, root_cause, additionalProperties, minLength, type, type, properties, builder_instructions (+7 more)

### Community 19 - "adapters.py"
Cohesion: 0.15
Nodes (8): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PRD_FILE, RALPH_PROJECT_DIR, RALPH_RUN_DIR, ralph.sh script, upsert_metadata()

### Community 20 - "skills/decisions/SKILL.md"
Cohesion: 0.25
Nodes (4): _pull_request_names(), _pull_request_number(), Extract case-insensitive label or reviewer names from gh JSON., Extract the number from a GitHub pull-request URL.

### Community 21 - "test-guard.sh"
Cohesion: 0.18
Nodes (11): TypedDict, Common interfaces shared by agent adapters and graph nodes., Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow. (+3 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.14
Nodes (20): Remove common credentials before command output enters workflow state., redact_secrets(), is_development_mode(), is_dry_run(), Explicit execution modes for local development and normal runs., Return whether local development side effects are explicitly enabled., Return whether side-effecting delivery actions should be previewed., _approval_denied() (+12 more)

### Community 23 - "main"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 24 - "Test coverage"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 26 - "nodes.py"
Cohesion: 0.13
Nodes (3): NodeContractTests, GitHubAdapter, Commit validated items, then reconcile the branch's pull request.

### Community 27 - "RepositoryAdapter"
Cohesion: 0.09
Nodes (16): Connection, _checkpoint_timestamp(), CheckpointCleanup, _migrate_checkpoint_tuple(), _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup., Return a checkpoint tuple whose state channels use the current schema. (+8 more)

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

### Community 43 - "test_fault_injection.py"
Cohesion: 0.21
Nodes (7): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run an item's validation command or the full local suite as a fallback.

## Knowledge Gaps
- **103 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentResult` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `test_fault_injection.py`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `.__init__`, `skills/decisions/SKILL.md`, `test-guard.sh`, `GitHubAdapter`, `nodes.py`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `Shanks`, `ralph.sh`, `VersionedSqliteSaver`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `test_fault_injection.py`, `GitHubAdapter`, `GitHub Commits and PRs`, `grilling/SKILL.md`, `test-guard.sh`, `GitHubAdapter`, `nodes.py`, `RepositoryAdapter`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `GitHubAdapter` connect `nodes.py` to `NodeDependencies`, `GraphRequestHandler`, `nodes.py`, `CLAUDE.md`, `test_fault_injection.py`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `skills/decisions/SKILL.md`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `GitHubAdapter` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`GitHubAdapter` has 8 INFERRED edges - model-reasoned connections that need verification._