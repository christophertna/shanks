# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 34 files · ~27,484 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 588 nodes · 1425 edges · 34 communities (31 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 138 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `04072be8`
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

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 75 edges
2. `NodeDependencies` - 65 edges
3. `WorkflowState` - 63 edges
4. `AgentRequest` - 60 edges
5. `NodeContractTests` - 49 edges
6. `GraphRoutingTests` - 41 edges
7. `StubAgentAdapter` - 41 edges
8. `build_graph()` - 34 edges
9. `GitHubAdapter` - 33 edges
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

## Communities (34 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.14
Nodes (19): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., RecordingRepository (+11 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 2 - "nodes.py"
Cohesion: 0.16
Nodes (10): _migrate_checkpoint_tuple(), Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver, StateSchemaTests, migrate_state(), Upgrade persisted state to the current schema without mutating it. (+2 more)

### Community 3 - "Shanks"
Cohesion: 0.33
Nodes (5): Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.19
Nodes (12): _audit_command(), _command_path_arguments(), _estimate_tokens(), _format_request(), _path_within_any(), Agent adapter implementations for graph nodes and external runners., Create a stable prompt envelope for CLI-backed adapters., Use a conservative four-characters-per-token estimate for CLI text. (+4 more)

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
Cohesion: 0.20
Nodes (8): ValueError, _critic_result(), _debugger_result(), _parse_json_object(), Path, Parse a JSON object even when the CLI adds non-JSON log lines., Translate a structured CLI response into an AgentResult., Translate structured debugger output into the shared result shape.

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
Nodes (22): CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, GPT56LunaCriticAdapter, Adapter for direct Claude Code CLI execution., Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent. (+14 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.14
Nodes (5): NodeContractTests, _attach_commands(), GitHubAdapter, Commit validated items, then push the branch and open its PR., Keep the full command trail when a multi-command operation fails.

### Community 23 - "WorkflowState"
Cohesion: 0.17
Nodes (10): TypedDict, Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow., select_next_item() (+2 more)

### Community 24 - "Test coverage"
Cohesion: 0.07
Nodes (26): Agent and adapter contracts, Approval and handoff behavior, Budgets, cancellation, and run state, Commit scope and resume safety, Common agent and subprocess behavior, Dependency factories and critic models, Entry, intake, and item routing, GitHub commit and pull-request delivery (+18 more)

### Community 25 - "graph.py"
Cohesion: 0.14
Nodes (32): Translate common agent output into shared workflow state fields., state_update_from_result(), _apply_failure_policy(), _audit_result(), building(), critic_auditor(), _current_item(), debugger() (+24 more)

### Community 26 - "nodes.py"
Cohesion: 0.14
Nodes (17): _invalid_budget(), _nonnegative_float(), _nonnegative_int(), _pull_request_id(), Standardized LangGraph node implementations., Extract the numeric or opaque ID at the end of a pull-request URL., Redact strings recursively before they enter persisted state., Return the first configured cancellation or budget stop reason. (+9 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.08
Nodes (21): Exception, FailureClass, Protocol, Common interfaces shared by agent adapters and graph nodes., Push the branch and create its pull request., Classify failures at the shared adapter boundary., Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake. (+13 more)

### Community 28 - "create_nodes"
Cohesion: 0.12
Nodes (17): NodeFunction, attempt_limit(), create_nodes(), failed_build(), failed_run(), intake(), Migrate state, enforce run budgets, and stamp every checkpoint., Create state-only node callables with injected agent backends. (+9 more)

### Community 29 - "Any"
Cohesion: 0.12
Nodes (14): _critic_request(), _debugger_request(), DebuggerAdapter, LocalTestAdapter, _preflight_failure(), Run a configured CLI backend through the common adapter contract., Add the shared read-only audit instructions to a critic request., Give the debugger failure evidence and a read-only analysis mandate. (+6 more)

### Community 30 - "RalphAdapter"
Cohesion: 0.20
Nodes (5): _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

### Community 31 - "planning"
Cohesion: 0.10
Nodes (32): build_graph(), LangGraph workflow assembled from standardized agent nodes., Build the workflow with optional adapters or a Claude/Codex choice., Open the SQLite checkpoint store shared by workflow and viewer processes., shared_checkpointer(), agent_error_handler_for(), Retry transient learn failures without asking for a new mode., Enter intake only after preflight succeeds or is explicitly skipped. (+24 more)

### Community 32 - "CheapCriticAdapter"
Cohesion: 0.33
Nodes (7): _approval_denied(), commit_item(), github_node(), Pause until a human explicitly approves or rejects a side effect., Commit the validated current item before selecting the next one., Push the completed branch and create its pull request., _request_approval()

### Community 33 - "_apply_failure_policy"
Cohesion: 0.12
Nodes (21): Any, NodeError, agent_error_handler(), build_error_handler(), Route an exhausted native build-node failure to the terminal path., Classify an exhausted non-build node exception and stop safely., acceptance_criteria_for_item(), append_run_manifest() (+13 more)

## Knowledge Gaps
- **91 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+86 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `CheapCriticAdapter`, `GraphRequestHandler`, `nodes.py`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `create_nodes`, `Any`, `RalphAdapter`, `planning`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `Any` to `NodeDependencies`, `VersionedSqliteSaver`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `graph.py`, `nodes.py`, `RepositoryAdapter`, `RalphAdapter`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `PreflightOnlyRepository`) actually correct?**
  _`AgentResult` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `GraphRoutingTests`) actually correct?**
  _`NodeDependencies` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `WorkflowState` (e.g. with `VersionedSqliteSaver` and `AgentAdapter`) actually correct?**
  _`WorkflowState` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `PreflightOnlyRepository`) actually correct?**
  _`AgentRequest` has 20 INFERRED edges - model-reasoned connections that need verification._