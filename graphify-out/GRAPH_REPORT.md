# Graph Report - shanks  (2026-08-07)

## Corpus Check
- 42 files · ~35,417 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 776 nodes · 1926 edges · 40 communities (37 shown, 3 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 204 edges (avg confidence: 0.56)
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
- CheapCriticAdapter
- RepositoryAdapter
- DebuggerAdapter

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 86 edges
2. `NodeDependencies` - 83 edges
3. `AgentRequest` - 72 edges
4. `WorkflowState` - 65 edges
5. `GitHubAdapter` - 58 edges
6. `NodeContractTests` - 55 edges
7. `StubAgentAdapter` - 53 edges
8. `GraphRoutingTests` - 41 edges
9. `build_graph()` - 34 edges
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

## Communities (40 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.13
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
Cohesion: 0.11
Nodes (36): Remove common credentials before command output enters workflow state., redact_secrets(), Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _approval_denied(), _audit_result(), building() (+28 more)

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
Cohesion: 0.16
Nodes (11): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback. (+3 more)

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
Cohesion: 0.12
Nodes (13): ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter, claude_opus_4_8_dependencies(), default_dependencies() (+5 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.09
Nodes (3): NodeContractTests, RalphAdapter, Adapter for the project-local Ralph runner.

### Community 23 - "WorkflowState"
Cohesion: 0.22
Nodes (10): TypedDict, _item_complete(), item_router(), _mark_current_item_built(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow., select_next_item() (+2 more)

### Community 24 - "Test coverage"
Cohesion: 0.07
Nodes (29): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+21 more)

### Community 25 - "graph.py"
Cohesion: 0.12
Nodes (17): _audit_command(), ClaudeAdapter, CodexAdapter, _command_path_arguments(), _estimate_tokens(), _format_request(), _path_within_any(), Path (+9 more)

### Community 26 - "nodes.py"
Cohesion: 0.13
Nodes (17): RunnableConfig, _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL., Return the first configured cancellation or budget stop reason. (+9 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.18
Nodes (12): Exception, FailureClass, Common interfaces shared by agent adapters and graph nodes., Classify failures at the shared adapter boundary., classify_failure(), BaseException, Failure classification and bounded retry helpers., Use the same classifier for LangGraph's native node retry policy. (+4 more)

### Community 28 - "create_nodes"
Cohesion: 0.22
Nodes (6): CheapCriticAdapter, Deterministic low-cost critic used by the default graph., AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles., Run the backend for one workflow node invocation., Reusable workflow state, agent contracts, adapters, and nodes.

### Community 29 - "Any"
Cohesion: 0.11
Nodes (22): FakeWorkspaceManager, Path, RecordingAdapter, WorkspaceTests, _command_error(), _git_environment(), _normalize_component(), CompletedProcess (+14 more)

### Community 30 - "RalphAdapter"
Cohesion: 0.25
Nodes (5): _critic_request(), _parse_uncertainties(), Extract the builder's concise uncertainty bullets from Ralph output., Add the shared read-only audit instructions to a critic request., Persist the graph's full PRD before Ralph reads its next story.

### Community 31 - "planning"
Cohesion: 0.10
Nodes (35): build_graph(), _env_float(), _env_int(), Path, LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+27 more)

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Stop safely when an item needs more build attempts than allowed., Wait between safe retries without retrying side-effecting operations. (+9 more)

### Community 33 - "_apply_failure_policy"
Cohesion: 0.15
Nodes (13): _debugger_details(), _default_plan(), planning(), Format new debugger findings for the current PRD requirement., Return the current run's remaining wall-clock budget for adapters., Plan the current incomplete item without losing retry context., remaining_runtime_seconds(), _request_for() (+5 more)

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.06
Nodes (30): Any, Connection, _checkpoint_timestamp(), CheckpointCleanup, _migrate_checkpoint_tuple(), _now(), Retain recent checkpoints and delete their associated writes., Counts returned by checkpoint retention cleanup. (+22 more)

### Community 35 - "build_error_handler"
Cohesion: 0.29
Nodes (8): NodeError, agent_error_handler(), build_error_handler(), _exception_failure_class(), BaseException, Route an exhausted native build-node failure to the terminal path., Classify an exhausted non-build node exception and stop safely., Classify the original exception carried by LangGraph's NodeError.

### Community 36 - "DebuggerAdapter"
Cohesion: 0.11
Nodes (10): _attach_commands(), GitHubAdapter, _preflight_failure(), _pull_request_names(), _pull_request_number(), Extract case-insensitive label or reviewer names from gh JSON., Extract the number from a GitHub pull-request URL., Keep the full command trail when a multi-command operation fails. (+2 more)

### Community 38 - "CheapCriticAdapter"
Cohesion: 0.09
Nodes (25): dependencies(), LifecycleTests, LeaseLostError, _lifecycle_status(), RuntimeError, Persistent run leases and lifecycle records., Extend the current owner's lease before another node runs., Record a pause caused by a human interrupt while keeping the lease. (+17 more)

### Community 41 - "RepositoryAdapter"
Cohesion: 0.22
Nodes (6): Protocol, Commit one validated item's intended files., Push the branch and reconcile its pull request lifecycle., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., RepositoryAdapter

### Community 42 - "DebuggerAdapter"
Cohesion: 0.13
Nodes (13): ValueError, _critic_result(), _debugger_request(), _debugger_result(), DebuggerAdapter, _parse_json_object(), _policy_values(), Normalize and deduplicate configured reviewer or label names. (+5 more)

## Knowledge Gaps
- **95 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `RALPH_RUN_DIR`, `RALPH_PRD_FILE`, `$schema` (+90 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `CheapCriticAdapter`, `GraphRequestHandler`, `CheapCriticAdapter`, `_apply_failure_policy`, `DebuggerAdapter`, `VersionedSqliteSaver`, `CheapCriticAdapter`, `RepositoryAdapter`, `DebuggerAdapter`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `create_nodes`, `Any`, `planning`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `DebuggerAdapter`, `VersionedSqliteSaver`, `RepositoryAdapter`, `DebuggerAdapter`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `create_nodes`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `GitHubAdapter` connect `DebuggerAdapter` to `NodeDependencies`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `create_nodes`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 25 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `NodeDependencies` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`NodeDependencies` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `WorkflowState` (e.g. with `CheckpointCleanup` and `VersionedSqliteSaver`) actually correct?**
  _`WorkflowState` has 7 INFERRED edges - model-reasoned connections that need verification._