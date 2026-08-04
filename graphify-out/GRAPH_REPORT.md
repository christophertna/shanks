# Graph Report - shanks  (2026-08-03)

## Corpus Check
- 27 files · ~15,656 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 365 nodes · 828 edges · 18 communities (16 shown, 2 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3540e4f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NodeDependencies
- GraphRequestHandler
- nodes.py
- Shanks
- ralph.sh
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
5. `NodeContractTests` - 36 edges
6. `build_graph()` - 30 edges
7. `AgentAdapter` - 23 edges
8. `GitHubAdapter` - 22 edges
9. `default_dependencies()` - 22 edges
10. `GraphRoutingTests` - 21 edges

## Surprising Connections (you probably didn't know these)
- `build_graph()` --indirect_call--> `build_error_handler()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_building()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_commit()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_intake()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_item_router()`  [INFERRED]
  graph.py → workflow/nodes.py

## Import Cycles
- None detected.

## Communities (18 total, 2 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.15
Nodes (18): Command, build_graph(), Build the workflow with optional adapters or a Claude/Codex choice., GraphRoutingTests, _initial_state(), RecordingRepository, SequenceAdapter, _stub_dependencies() (+10 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.08
Nodes (26): BaseHTTPRequestHandler, ModuleType, graph_revision(), graph_source_files(), GraphRequestHandler, load_graph_module(), main(), Path (+18 more)

### Community 2 - "nodes.py"
Cohesion: 0.07
Nodes (68): LangGraph workflow assembled from standardized agent nodes., NodeError, NodeFunction, TypedDict, Common interfaces shared by agent adapters and graph nodes., Interface for local commits and the final GitHub handoff., Translate common agent output into shared workflow state fields., RepositoryAdapter (+60 more)

### Community 3 - "Shanks"
Cohesion: 0.40
Nodes (4): Interactive workflow, Main pieces, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

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
Nodes (50): Protocol, NodeContractTests, CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, _critic_request(), _critic_result() (+42 more)

## Knowledge Gaps
- **71 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+66 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `adapters.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `nodes.py`, `.__init__`, `adapters.py`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
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