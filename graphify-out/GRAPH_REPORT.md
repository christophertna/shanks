# Graph Report - shanks  (2026-08-02)

## Corpus Check
- 17 files · ~6,956 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 178 nodes · 380 edges · 12 communities (9 shown, 3 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 44 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `753c83d7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NodeDependencies
- GraphRequestHandler
- nodes.py
- Important files
- ralph.sh
- AgentRequest
- Ralph Agent Instructions
- Ralph Agent Instructions
- Ralph Agent Instructions (Codex)
- AGENTS.md
- CLAUDE.md
- .__init__

## God Nodes (most connected - your core abstractions)
1. `AgentRequest` - 27 edges
2. `AgentResult` - 27 edges
3. `NodeDependencies` - 26 edges
4. `WorkflowState` - 25 edges
5. `StubAgentAdapter` - 19 edges
6. `build_graph()` - 15 edges
7. `AgentAdapter` - 15 edges
8. `CheapCriticAdapter` - 13 edges
9. `create_nodes()` - 13 edges
10. `GraphRoutingTests` - 12 edges

## Surprising Connections (you probably didn't know these)
- `build_graph()` --indirect_call--> `route_after_building()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_planning()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_validation()`  [INFERRED]
  graph.py → workflow/nodes.py
- `SequenceAdapter` --uses--> `StubAgentAdapter`  [INFERRED]
  tests/test_graph.py → workflow/adapters.py
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (12 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.32
Nodes (7): build_graph(), Build the workflow with optional provider adapters., GraphRoutingTests, _initial_state(), SequenceAdapter, NodeDependencies, Backends injected into the standardized graph nodes.

### Community 1 - "GraphRequestHandler"
Cohesion: 0.13
Nodes (14): BaseHTTPRequestHandler, ModuleType, graph_revision(), graph_source_files(), GraphRequestHandler, load_graph_module(), Path, Serve graph.html and regenerate its Mermaid definition from graph.py. (+6 more)

### Community 2 - "nodes.py"
Cohesion: 0.11
Nodes (39): LangGraph workflow assembled from standardized agent nodes., NodeFunction, TypedDict, Translate common agent output into shared workflow state fields., state_update_from_result(), Reusable workflow state, agent contracts, adapters, and nodes., building(), create_nodes() (+31 more)

### Community 3 - "Important files"
Cohesion: 0.12
Nodes (15): Current limits, `graph.html`, `graph.py`, `graphify-out/`, Important files, Ralph, `serve_graph.py`, `tests/` (+7 more)

### Community 4 - "ralph.sh"
Cohesion: 0.28
Nodes (3): initialize_metadata_file(), ralph.sh script, upsert_metadata()

### Community 5 - "AgentRequest"
Cohesion: 0.14
Nodes (25): Protocol, NodeContractTests, CheapCriticAdapter, ClaudeAdapter, CodexAdapter, _format_request(), RalphAdapter, Agent adapter implementations.  The graph defaults to deterministic stubs. CLI a (+17 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.18
Nodes (10): Browser Testing (If Available), Consolidate Patterns, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions, Stop Condition (+2 more)

### Community 7 - "Ralph Agent Instructions"
Cohesion: 0.18
Nodes (10): Browser Testing (Required for Frontend Stories), Consolidate Patterns, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions, Stop Condition (+2 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.25
Nodes (7): Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

## Knowledge Gaps
- **39 isolated node(s):** `graphify`, `graphify`, `The main flow`, ``graph.py``, ``workflow/state.py`` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AgentRequest` connect `AgentRequest` to `NodeDependencies`, `nodes.py`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `AgentRequest` to `NodeDependencies`, `nodes.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `AgentRequest`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentRequest` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentResult` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `NodeDependencies` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`NodeDependencies` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkflowState` (e.g. with `AgentAdapter` and `AgentRequest`) actually correct?**
  _`WorkflowState` has 4 INFERRED edges - model-reasoned connections that need verification._