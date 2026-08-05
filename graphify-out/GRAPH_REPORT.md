# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 32 files · ~21,745 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 475 nodes · 1125 edges · 30 communities (27 shown, 3 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 121 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c3c6daaf`
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
- nodes.py
- create_nodes
- PRDItem
- RepositoryAdapter
- github_node
- Any

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 56 edges
2. `AgentRequest` - 55 edges
3. `NodeDependencies` - 52 edges
4. `WorkflowState` - 51 edges
5. `NodeContractTests` - 44 edges
6. `GraphRoutingTests` - 32 edges
7. `GitHubAdapter` - 30 edges
8. `StubAgentAdapter` - 29 edges
9. `build_graph()` - 25 edges
10. `SubprocessAgentAdapter` - 23 edges

## Surprising Connections (you probably didn't know these)
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `VersionedSqliteSaver` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `SequenceAdapter` --uses--> `AgentResult`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `RecordingRepository` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (30 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.16
Nodes (15): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), Keep graph tests isolated from the shared production checkpoint store., RecordingRepository, SequenceAdapter (+7 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 2 - "nodes.py"
Cohesion: 0.11
Nodes (28): build_graph(), LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer(), NodeError, build_error_handler(), Route an exhausted native build-node failure to the terminal path. (+20 more)

### Community 3 - "Shanks"
Cohesion: 0.40
Nodes (4): Interactive workflow, Main pieces, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.19
Nodes (6): _migrate_checkpoint_tuple(), Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver, StateSchemaTests

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
Cohesion: 0.28
Nodes (4): _command_path_arguments(), _path_within_any(), Path, _resolve_path()

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
Cohesion: 0.06
Nodes (55): NodeContractTests, ValueError, CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, _critic_request(), _critic_result() (+47 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.13
Nodes (4): GitHubAdapter, Commit validated items, then push the branch and open its PR., Remove common credentials before command output enters workflow state., redact_secrets()

### Community 23 - "WorkflowState"
Cohesion: 0.19
Nodes (21): Translate common agent output into shared workflow state fields., state_update_from_result(), building(), critic_auditor(), _current_item(), debugger(), learning(), _mark_current_item_built() (+13 more)

### Community 24 - "nodes.py"
Cohesion: 0.17
Nodes (16): _debugger_details(), _default_plan(), _invalid_budget(), _nonnegative_float(), _nonnegative_int(), planning(), Standardized LangGraph node implementations., Return the first configured cancellation or budget stop reason. (+8 more)

### Community 25 - "create_nodes"
Cohesion: 0.17
Nodes (13): NodeFunction, attempt_limit(), create_nodes(), failed_build(), intake(), Migrate state, enforce run budgets, and stamp every checkpoint., Create state-only node callables with injected agent backends., Ask for the top-level workflow mode and route the run accordingly. (+5 more)

### Community 26 - "PRDItem"
Cohesion: 0.20
Nodes (10): TypedDict, Reusable workflow state, agent contracts, adapters, and nodes., _item_complete(), item_router(), Select the first item that is not both built and validated., Treat legacy passes-only items as complete while honoring validation., Prepare the decision to start another item or finish the workflow., select_next_item() (+2 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.29
Nodes (5): Protocol, Interface for local commits and the final GitHub handoff., Commit one validated item's intended files., Push the branch and create its pull request., RepositoryAdapter

### Community 28 - "github_node"
Cohesion: 0.33
Nodes (7): _approval_denied(), commit_item(), github_node(), Commit the validated current item before selecting the next one., Push the completed branch and create its pull request., Pause until a human explicitly approves or rejects a side effect., _request_approval()

### Community 29 - "Any"
Cohesion: 0.40
Nodes (5): Any, _migrate_v0_to_v1(), _migrate_v1_to_v2(), Mark an unversioned legacy state as the first supported schema., Add run budgets and clean-cancellation fields to persisted state.

## Knowledge Gaps
- **71 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `VersionedSqliteSaver`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `nodes.py`, `create_nodes`, `PRDItem`, `RepositoryAdapter`, `github_node`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `adapters.py` to `NodeDependencies`, `GitHubAdapter`, `WorkflowState`, `nodes.py`, `PRDItem`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `build_graph()` connect `nodes.py` to `NodeDependencies`, `GraphRequestHandler`, `VersionedSqliteSaver`, `adapters.py`, `create_nodes`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentResult` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentRequest` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `GraphRoutingTests`) actually correct?**
  _`NodeDependencies` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `WorkflowState` (e.g. with `VersionedSqliteSaver` and `AgentAdapter`) actually correct?**
  _`WorkflowState` has 6 INFERRED edges - model-reasoned connections that need verification._