# Graph Report - shanks  (2026-08-07)

## Corpus Check
- 46 files · ~36,746 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 811 nodes · 2015 edges · 42 communities (38 shown, 4 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 209 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d8ba758c`
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

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 92 edges
2. `NodeDependencies` - 84 edges
3. `AgentRequest` - 72 edges
4. `WorkflowState` - 66 edges
5. `GitHubAdapter` - 60 edges
6. `NodeContractTests` - 55 edges
7. `StubAgentAdapter` - 53 edges
8. `GraphRoutingTests` - 43 edges
9. `build_graph()` - 36 edges
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
Cohesion: 0.12
Nodes (20): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., Keep the legacy test-double API covered while the graph splits handoffs. (+12 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (12): NodeContractTests, _attach_commands(), GitHubAdapter, _preflight_failure(), _pull_request_names(), _pull_request_number(), Extract case-insensitive label or reviewer names from gh JSON., Extract the number from a GitHub pull-request URL. (+4 more)

### Community 2 - "nodes.py"
Cohesion: 0.07
Nodes (32): ShanksCliTests, FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, main(), Small command-line helpers for inspecting Shanks configuration., Print the configured execution mode when requested. (+24 more)

### Community 3 - "Shanks"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 4 - "ralph.sh"
Cohesion: 0.09
Nodes (25): dependencies(), LifecycleTests, LeaseLostError, _lifecycle_status(), RuntimeError, Persistent run leases and lifecycle records., Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease. (+17 more)

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.09
Nodes (37): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+29 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.09
Nodes (16): Connection, _checkpoint_timestamp(), CheckpointCleanup, _migrate_checkpoint_tuple(), _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup., Return a checkpoint tuple whose state channels use the current schema. (+8 more)

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.12
Nodes (22): ArgumentParser, Runner, _command_output(), diff_command(), diff_size_errors(), DiffStats, main(), parse_numstat() (+14 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.13
Nodes (33): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+25 more)

### Community 9 - "AGENTS.md"
Cohesion: 0.07
Nodes (29): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+21 more)

### Community 10 - "CLAUDE.md"
Cohesion: 0.16
Nodes (11): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback. (+3 more)

### Community 11 - "critic_output.schema.json"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 12 - "GitHubAdapter"
Cohesion: 0.15
Nodes (16): ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter, AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles. (+8 more)

### Community 13 - "NodeContractTests"
Cohesion: 0.15
Nodes (18): Any, acceptance_criteria_for_item(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), _migrate_v4_to_v5(), _migrate_v5_to_v6() (+10 more)

### Community 14 - "AgentRequest"
Cohesion: 0.18
Nodes (11): CheapCriticAdapter, ClaudeAdapter, CodexAdapter, _command_path_arguments(), _path_within_any(), Path, Agent adapter implementations for graph nodes and external runners., Adapter for direct Codex CLI execution. (+3 more)

### Community 15 - "GitHub Commits and PRs"
Cohesion: 0.14
Nodes (16): RunnableConfig, _default_plan(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL. (+8 more)

### Community 16 - "grilling/SKILL.md"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 17 - ".__init__"
Cohesion: 0.16
Nodes (13): Exception, FailureClass, Classify failures at the shared adapter boundary., classify_failure(), BaseException, Failure classification and bounded retry helpers., Use the same classifier for LangGraph's native node retry policy., Classify a failure before deciding whether it is safe to retry. (+5 more)

### Community 18 - "RepositoryAdapter"
Cohesion: 0.12
Nodes (15): builder_instructions, root_cause, additionalProperties, minLength, type, type, properties, builder_instructions (+7 more)

### Community 19 - "adapters.py"
Cohesion: 0.15
Nodes (8): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PRD_FILE, RALPH_PROJECT_DIR, RALPH_RUN_DIR, ralph.sh script, upsert_metadata()

### Community 20 - "skills/decisions/SKILL.md"
Cohesion: 0.16
Nodes (12): TypedDict, Common interfaces shared by agent adapters and graph nodes., Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), _mark_current_item_validated(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation. (+4 more)

### Community 21 - "test-guard.sh"
Cohesion: 0.15
Nodes (8): Protocol, Commit one validated item's intended files., Push the validated branch without opening a pull request., Open or reuse the pull request for an already-pushed branch., Push the branch and reconcile its pull request lifecycle., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., RepositoryAdapter

### Community 22 - "GitHubAdapter"
Cohesion: 0.19
Nodes (13): Remove common credentials before command output enters workflow state., redact_secrets(), _approval_denied(), commit_item(), github_node(), pull_request_node(), Request approval, then push the completed branch., Request approval, then open or reuse the pull request. (+5 more)

### Community 23 - "main"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 24 - "Test coverage"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 25 - "graph.py"
Cohesion: 0.21
Nodes (9): ValueError, _critic_result(), _debugger_result(), _parse_json_object(), _policy_values(), Normalize and deduplicate configured reviewer or label names., Parse a JSON object even when the CLI adds non-JSON log lines., Translate a structured CLI response into an AgentResult. (+1 more)

### Community 26 - "nodes.py"
Cohesion: 0.20
Nodes (5): _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

### Community 27 - "RepositoryAdapter"
Cohesion: 0.20
Nodes (6): _critic_request(), _debugger_request(), DebuggerAdapter, Add the shared read-only audit instructions to a critic request., Give the debugger failure evidence and a read-only analysis mandate., Analyze validation failures with a read-only structured Codex run.

### Community 28 - "create_nodes"
Cohesion: 0.22
Nodes (8): _audit_command(), _estimate_tokens(), _format_request(), Return a redacted command suitable for the persisted run manifest., Create a stable prompt envelope for CLI-backed adapters., Use a conservative four-characters-per-token estimate for CLI text., current_workspace_directory(), Return the workspace for the current graph invocation, if any.

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
Cohesion: 0.29
Nodes (6): Commit, push, and PR checks, Commit subject, GitHub Commits and PRs, Merge authority, Pull request description, Pull request title

### Community 33 - "_apply_failure_policy"
Cohesion: 0.33
Nodes (5): Commands, Gotchas, graphify, Project overview, Repo etiquette

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.33
Nodes (6): NodeError, agent_error_handler(), _exception_failure_class(), BaseException, Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError.

## Knowledge Gaps
- **96 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+91 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `Shanks`, `ralph.sh`, `VersionedSqliteSaver`, `Ralph Agent Instructions`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `grilling/SKILL.md`, `skills/decisions/SKILL.md`, `test-guard.sh`, `GitHubAdapter`, `nodes.py`, `RepositoryAdapter`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `Ralph Agent Instructions (Codex)`, `CLAUDE.md`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `.__init__`, `skills/decisions/SKILL.md`, `test-guard.sh`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `create_nodes`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `GitHubAdapter` connect `GraphRequestHandler` to `NodeDependencies`, `CLAUDE.md`, `GitHubAdapter`, `AgentRequest`, `GitHub Commits and PRs`, `graph.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `WorkflowState` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`WorkflowState` has 7 INFERRED edges - model-reasoned connections that need verification._