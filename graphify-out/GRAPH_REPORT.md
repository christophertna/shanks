# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 32 files · ~20,478 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 447 nodes · 1039 edges · 22 communities (19 shown, 3 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cc64c112`
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

## God Nodes (most connected - your core abstractions)
1. `AgentRequest` - 54 edges
2. `AgentResult` - 52 edges
3. `NodeDependencies` - 48 edges
4. `NodeContractTests` - 43 edges
5. `WorkflowState` - 43 edges
6. `GitHubAdapter` - 30 edges
7. `GraphRoutingTests` - 27 edges
8. `StubAgentAdapter` - 25 edges
9. `AgentAdapter` - 23 edges
10. `default_dependencies()` - 23 edges

## Surprising Connections (you probably didn't know these)
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `VersionedSqliteSaver` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `SequenceAdapter` --uses--> `NodeDependencies`  [INFERRED]
  tests/test_graph.py → workflow/nodes.py
- `RecordingRepository` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (22 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.14
Nodes (15): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), Keep graph tests isolated from the shared production checkpoint store., RecordingRepository, SequenceAdapter (+7 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (38): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+30 more)

### Community 2 - "nodes.py"
Cohesion: 0.06
Nodes (81): build_graph(), LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer(), NodeError, NodeFunction, TypedDict (+73 more)

### Community 3 - "Shanks"
Cohesion: 0.40
Nodes (4): Interactive workflow, Main pieces, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.14
Nodes (13): Any, _migrate_checkpoint_tuple(), Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., VersionedSqliteSaver, SqliteSaver, StateSchemaTests, migrate_state() (+5 more)

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
Nodes (6): _command_path_arguments(), _path_within_any(), Path, Remove common credentials before command output enters workflow state., redact_secrets(), _resolve_path()

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
Cohesion: 0.05
Nodes (53): Protocol, NodeContractTests, ValueError, CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, _critic_request() (+45 more)

## Knowledge Gaps
- **71 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `nodes.py` to `NodeDependencies`, `adapters.py`, `VersionedSqliteSaver`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `build_graph()` connect `nodes.py` to `NodeDependencies`, `GraphRequestHandler`, `adapters.py`, `VersionedSqliteSaver`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `adapters.py` to `NodeDependencies`, `nodes.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentRequest` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentResult` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `GraphRoutingTests`) actually correct?**
  _`NodeDependencies` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `NodeContractTests` (e.g. with `CheapCriticAdapter` and `ClaudeAdapter`) actually correct?**
  _`NodeContractTests` has 13 INFERRED edges - model-reasoned connections that need verification._