# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 37 files · ~29,044 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 625 nodes · 1498 edges · 37 communities (34 shown, 3 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 142 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5fd13800`
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

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 75 edges
2. `NodeDependencies` - 65 edges
3. `WorkflowState` - 63 edges
4. `AgentRequest` - 60 edges
5. `NodeContractTests` - 51 edges
6. `GraphRoutingTests` - 41 edges
7. `StubAgentAdapter` - 41 edges
8. `GitHubAdapter` - 36 edges
9. `build_graph()` - 34 edges
10. `build_graph()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `VersionedSqliteSaver` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `build_graph()` --indirect_call--> `build_error_handler()`  [INFERRED]
  graph.py → workflow/nodes.py
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `RecordingRepository` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (37 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.13
Nodes (19): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., RecordingRepository (+11 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 2 - "nodes.py"
Cohesion: 0.12
Nodes (22): ArgumentParser, CompletedProcess, Runner, _command_output(), diff_command(), diff_size_errors(), DiffStats, main() (+14 more)

### Community 3 - "Shanks"
Cohesion: 0.33
Nodes (5): Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.11
Nodes (42): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _approval_denied(), _audit_result(), building(), commit_item(), create_nodes() (+34 more)

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
Cohesion: 0.14
Nodes (16): ValueError, ClaudeAdapter, CodexAdapter, _command_path_arguments(), _critic_result(), _debugger_result(), _parse_json_object(), _path_within_any() (+8 more)

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
Cohesion: 0.13
Nodes (13): ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter, claude_opus_4_8_dependencies(), default_dependencies() (+5 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.13
Nodes (5): NodeContractTests, _attach_commands(), GitHubAdapter, Keep the full command trail when a multi-command operation fails., Commit validated items, then push the branch and open its PR.

### Community 23 - "WorkflowState"
Cohesion: 0.18
Nodes (6): _critic_request(), LocalTestAdapter, _preflight_failure(), Add the shared read-only audit instructions to a critic request., Run an item's validation command or the full local suite as a fallback., Check tools, branch state, GitHub auth, and the test environment.

### Community 24 - "Test coverage"
Cohesion: 0.07
Nodes (27): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, GitHub commit and pull-request delivery (+19 more)

### Community 25 - "graph.py"
Cohesion: 0.12
Nodes (16): TypedDict, Common interfaces shared by agent adapters and graph nodes., Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), _mark_current_item_built(), _mark_current_item_validated(), Select the first item that is not both built and validated. (+8 more)

### Community 26 - "nodes.py"
Cohesion: 0.10
Nodes (24): attempt_limit(), _default_plan(), failed_build(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations. (+16 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.14
Nodes (13): Exception, FailureClass, Classify failures at the shared adapter boundary., _exception_failure_class(), BaseException, Classify the original exception carried by LangGraph's NodeError., classify_failure(), BaseException (+5 more)

### Community 28 - "create_nodes"
Cohesion: 0.12
Nodes (15): _migrate_checkpoint_tuple(), Open the SQLite checkpoint store shared by workflow and viewer processes., Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., shared_checkpointer(), VersionedSqliteSaver, NodeFunction, SqliteSaver (+7 more)

### Community 29 - "Any"
Cohesion: 0.13
Nodes (11): _format_request(), _parse_uncertainties(), RalphAdapter, Run a configured CLI backend through the common adapter contract., Extract the builder's concise uncertainty bullets from Ralph output., Create a stable prompt envelope for CLI-backed adapters., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story. (+3 more)

### Community 30 - "RalphAdapter"
Cohesion: 0.22
Nodes (6): Protocol, Push the branch and create its pull request., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., Commit one validated item's intended files., RepositoryAdapter

### Community 31 - "planning"
Cohesion: 0.10
Nodes (31): build_graph(), LangGraph workflow assembled from standardized agent nodes., Build the workflow with optional adapters or a Claude/Codex choice., agent_error_handler_for(), Retry transient learn failures without asking for a new mode., Enter intake only after preflight succeeds or is explicitly skipped., Retry transient review failures but never turn them into rebuilds., Send failures to debugging and successes to the commit checkpoint. (+23 more)

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.33
Nodes (6): _audit_command(), _estimate_tokens(), Return a redacted command suitable for the persisted run manifest., Use a conservative four-characters-per-token estimate for CLI text., Remove common credentials before command output enters workflow state., redact_secrets()

### Community 33 - "_apply_failure_policy"
Cohesion: 0.15
Nodes (13): Any, acceptance_criteria_for_item(), _migrate_v0_to_v1(), _migrate_v1_to_v2(), _migrate_v2_to_v3(), _migrate_v3_to_v4(), Read an optional per-item validation command from a PRD item., Mark an unversioned legacy state as the first supported schema. (+5 more)

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.29
Nodes (5): CheapCriticAdapter, Deterministic low-cost critic used by the default graph., AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles., Run the backend for one workflow node invocation.

### Community 35 - "build_error_handler"
Cohesion: 0.33
Nodes (7): NodeError, agent_error_handler(), build_error_handler(), Route an exhausted native build-node failure to the terminal path., Classify an exhausted non-build node exception and stop safely., append_run_manifest(), Append one timestamped, persisted audit event to the current run.

### Community 36 - "DebuggerAdapter"
Cohesion: 0.33
Nodes (4): _debugger_request(), DebuggerAdapter, Give the debugger failure evidence and a read-only analysis mandate., Analyze validation failures with a read-only structured Codex run.

## Knowledge Gaps
- **91 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentResult` connect `NodeDependencies` to `CheapCriticAdapter`, `CheapCriticAdapter`, `DebuggerAdapter`, `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `GraphRequestHandler`, `CheapCriticAdapter`, `DebuggerAdapter`, `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `create_nodes`, `Any`, `RalphAdapter`, `planning`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `Any` to `NodeDependencies`, `CheapCriticAdapter`, `CheapCriticAdapter`, `DebuggerAdapter`, `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `PreflightOnlyRepository`) actually correct?**
  _`AgentResult` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `GraphRoutingTests`) actually correct?**
  _`NodeDependencies` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `WorkflowState` (e.g. with `VersionedSqliteSaver` and `AgentAdapter`) actually correct?**
  _`WorkflowState` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `PreflightOnlyRepository`) actually correct?**
  _`AgentRequest` has 20 INFERRED edges - model-reasoned connections that need verification._