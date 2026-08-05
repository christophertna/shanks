# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 27 files · ~17,412 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 389 nodes · 875 edges · 19 communities (17 shown, 2 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fced129f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NodeDependencies
- GraphRequestHandler
- nodes.py
- Shanks
- ralph.sh
- RepositoryAdapter
- Ralph Agent Instructions
- GitHub Commits and PRs
- Ralph Agent Instructions (Codex)
- AGENTS.md
- CLAUDE.md
- critic_output.schema.json
- NodeContractTests
- GitHub Commits and PRs
- .__init__
- .__init__
- adapters.py

## God Nodes (most connected - your core abstractions)
1. `AgentRequest` - 51 edges
2. `AgentResult` - 51 edges
3. `NodeDependencies` - 43 edges
4. `WorkflowState` - 40 edges
5. `NodeContractTests` - 37 edges
6. `GraphRoutingTests` - 23 edges
7. `GitHubAdapter` - 23 edges
8. `AgentAdapter` - 23 edges
9. `default_dependencies()` - 22 edges
10. `StubAgentAdapter` - 21 edges

## Surprising Connections (you probably didn't know these)
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `SequenceAdapter` --uses--> `AgentResult`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `RecordingRepository` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `RecordingRepository` --uses--> `AgentResult`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `GraphRoutingTests` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (19 total, 2 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.18
Nodes (14): Command, build_graph(), GraphRoutingTests, _initial_state(), Keep graph tests isolated from the shared production checkpoint store., RecordingRepository, SequenceAdapter, _stub_dependencies() (+6 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.07
Nodes (31): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+23 more)

### Community 2 - "nodes.py"
Cohesion: 0.08
Nodes (52): NodeFunction, TypedDict, Common interfaces shared by agent adapters and graph nodes., Interface for local commits and the final GitHub handoff., Commit one validated item's intended files., Push the branch and create its pull request., Translate common agent output into shared workflow state fields., RepositoryAdapter (+44 more)

### Community 3 - "Shanks"
Cohesion: 0.40
Nodes (4): Interactive workflow, Main pieces, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "RepositoryAdapter"
Cohesion: 0.08
Nodes (30): build_graph(), LangGraph workflow assembled from standardized agent nodes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer(), NodeError, Apply the viewer's white-node theme and diamond decision shapes., Build a readable overview, optionally showing recovery paths. (+22 more)

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
Nodes (52): Protocol, NodeContractTests, CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, _critic_request(), _critic_result() (+44 more)

## Knowledge Gaps
- **71 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `adapters.py`, `RepositoryAdapter`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Why does `build_graph()` connect `RepositoryAdapter` to `NodeDependencies`, `nodes.py`, `adapters.py`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `adapters.py` to `NodeDependencies`, `nodes.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentRequest` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentResult` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `NodeDependencies` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`NodeDependencies` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkflowState` (e.g. with `AgentAdapter` and `AgentRequest`) actually correct?**
  _`WorkflowState` has 5 INFERRED edges - model-reasoned connections that need verification._