# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 38 files · ~29,593 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 640 nodes · 1561 edges · 37 communities (34 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 159 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a0ac91f7`
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
1. `AgentResult` - 79 edges
2. `NodeDependencies` - 69 edges
3. `AgentRequest` - 66 edges
4. `WorkflowState` - 63 edges
5. `NodeContractTests` - 51 edges
6. `StubAgentAdapter` - 45 edges
7. `GraphRoutingTests` - 41 edges
8. `GitHubAdapter` - 41 edges
9. `build_graph()` - 34 edges
10. `build_graph()` - 28 edges

## Surprising Connections (you probably didn't know these)
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `VersionedSqliteSaver` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `ExplodingBuilder` --uses--> `VersionedSqliteSaver`  [INFERRED]
  tests/test_fault_injection.py → graph.py
- `FaultInjectionTests` --uses--> `VersionedSqliteSaver`  [INFERRED]
  tests/test_fault_injection.py → graph.py
- `build_graph()` --indirect_call--> `build_error_handler()`  [INFERRED]
  graph.py → workflow/nodes.py

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
Cohesion: 0.13
Nodes (34): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _approval_denied(), _audit_result(), building(), commit_item(), critic_auditor() (+26 more)

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
Cohesion: 0.12
Nodes (18): _command_path_arguments(), _critic_request(), _critic_result(), _debugger_request(), _debugger_result(), _estimate_tokens(), _format_request(), _parse_json_object() (+10 more)

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
Cohesion: 0.08
Nodes (23): CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, GPT56LunaCriticAdapter, Adapter for direct Codex CLI execution., Adapter for direct Claude Code CLI execution., Normalize a read-only CLI critic into the common agent result shape. (+15 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.09
Nodes (11): NodeContractTests, _attach_commands(), _audit_command(), GitHubAdapter, _preflight_failure(), Return a redacted command suitable for the persisted run manifest., Keep the full command trail when a multi-command operation fails., Commit validated items, then push the branch and open its PR. (+3 more)

### Community 23 - "WorkflowState"
Cohesion: 0.16
Nodes (11): _checkpoint_payload(), _dependencies(), ExplodingBuilder, FaultInjectionTests, _initial_state(), LocalTestAdapter, Run a configured CLI backend through the common adapter contract., Run an item's validation command or the full local suite as a fallback. (+3 more)

### Community 24 - "Test coverage"
Cohesion: 0.07
Nodes (28): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, Fault-injection tests (+20 more)

### Community 25 - "graph.py"
Cohesion: 0.20
Nodes (11): TypedDict, _item_complete(), item_router(), _mark_current_item_built(), _mark_current_item_validated(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow. (+3 more)

### Community 26 - "nodes.py"
Cohesion: 0.17
Nodes (15): _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL., Redact strings recursively before they enter persisted state., Return the first configured cancellation or budget stop reason. (+7 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.16
Nodes (14): Exception, FailureClass, Common interfaces shared by agent adapters and graph nodes., Classify failures at the shared adapter boundary., classify_failure(), BaseException, Failure classification and bounded retry helpers., Use the same classifier for LangGraph's native node retry policy. (+6 more)

### Community 28 - "create_nodes"
Cohesion: 0.09
Nodes (19): _migrate_checkpoint_tuple(), Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver, StateSchemaTests, migrate_state(), _migrate_v0_to_v1() (+11 more)

### Community 29 - "Any"
Cohesion: 0.20
Nodes (5): _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

### Community 30 - "RalphAdapter"
Cohesion: 0.22
Nodes (6): Protocol, Push the branch and create its pull request., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., Commit one validated item's intended files., RepositoryAdapter

### Community 31 - "planning"
Cohesion: 0.11
Nodes (32): build_graph(), LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer(), agent_error_handler_for(), Retry transient learn failures without asking for a new mode., Enter intake only after preflight succeeds or is explicitly skipped. (+24 more)

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Migrate state, enforce run budgets, and stamp every checkpoint., Create state-only node callables with injected agent backends. (+9 more)

### Community 33 - "_apply_failure_policy"
Cohesion: 0.40
Nodes (5): Any, acceptance_criteria_for_item(), Read an optional per-item validation command from a PRD item., Read acceptance criteria from either Python or Ralph PRD field names., validation_command_for_item()

### Community 34 - "CheapCriticAdapter"
Cohesion: 0.40
Nodes (5): _debugger_details(), _default_plan(), planning(), Format new debugger findings for the current PRD requirement., Plan the current incomplete item without losing retry context.

### Community 35 - "build_error_handler"
Cohesion: 0.29
Nodes (8): NodeError, agent_error_handler(), build_error_handler(), _exception_failure_class(), BaseException, Classify the original exception carried by LangGraph's NodeError., Route an exhausted native build-node failure to the terminal path., Classify an exhausted non-build node exception and stop safely.

### Community 36 - "DebuggerAdapter"
Cohesion: 0.24
Nodes (4): ValueError, DebuggerAdapter, Path, Analyze validation failures with a read-only structured Codex run.

## Knowledge Gaps
- **92 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+87 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentResult` connect `NodeDependencies` to `DebuggerAdapter`, `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `CheapCriticAdapter`, `GraphRequestHandler`, `CheapCriticAdapter`, `DebuggerAdapter`, `VersionedSqliteSaver`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `create_nodes`, `Any`, `RalphAdapter`, `planning`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `WorkflowState` to `NodeDependencies`, `DebuggerAdapter`, `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `Any`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 22 inferred relationships involving `AgentResult` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentResult` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `ExplodingBuilder`) actually correct?**
  _`NodeDependencies` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `AgentRequest` (e.g. with `ExplodingBuilder` and `FaultInjectionTests`) actually correct?**
  _`AgentRequest` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `WorkflowState` (e.g. with `VersionedSqliteSaver` and `AgentAdapter`) actually correct?**
  _`WorkflowState` has 6 INFERRED edges - model-reasoned connections that need verification._