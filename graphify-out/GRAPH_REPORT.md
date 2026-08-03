# Graph Report - shanks  (2026-08-02)

## Corpus Check
- 20 files · ~9,373 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 237 nodes · 511 edges · 14 communities (11 shown, 3 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 61 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a77d0e34`
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
- Ralph Agent Instructions (Codex)
- AGENTS.md
- CLAUDE.md
- critic_output.schema.json
- default_dependencies
- NodeContractTests

## God Nodes (most connected - your core abstractions)
1. `AgentRequest` - 34 edges
2. `AgentResult` - 32 edges
3. `NodeDependencies` - 30 edges
4. `WorkflowState` - 28 edges
5. `build_graph()` - 19 edges
6. `NodeContractTests` - 19 edges
7. `StubAgentAdapter` - 19 edges
8. `AgentAdapter` - 19 edges
9. `create_nodes()` - 15 edges
10. `SubprocessAgentAdapter` - 14 edges

## Surprising Connections (you probably didn't know these)
- `build_graph()` --indirect_call--> `route_after_building()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_item_router()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_planning()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_validation()`  [INFERRED]
  graph.py → workflow/nodes.py
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (14 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.27
Nodes (11): build_graph(), Build the workflow with optional provider adapters., GraphRoutingTests, _initial_state(), SequenceAdapter, Deterministic adapter used for local graph development and tests., StubAgentAdapter, AgentResult (+3 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.10
Nodes (21): BaseHTTPRequestHandler, ModuleType, graph_revision(), graph_source_files(), GraphRequestHandler, load_graph_module(), Path, Serve graph.html and regenerate its Mermaid definition from graph.py. (+13 more)

### Community 2 - "nodes.py"
Cohesion: 0.11
Nodes (42): LangGraph workflow assembled from standardized agent nodes., NodeFunction, TypedDict, Translate common agent output into shared workflow state fields., state_update_from_result(), attempt_limit(), building(), create_nodes() (+34 more)

### Community 3 - "Important files"
Cohesion: 0.11
Nodes (18): Claude Opus 4.8, Critic, Current limits, GPT-5.6 Luna, `graph.html`, `graph.py`, `graphify-out/`, Important files (+10 more)

### Community 4 - "ralph.sh"
Cohesion: 0.22
Nodes (3): initialize_metadata_file(), ralph.sh script, upsert_metadata()

### Community 5 - "AgentRequest"
Cohesion: 0.08
Nodes (41): Protocol, NodeContractTests, CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, _critic_request(), _critic_result() (+33 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.18
Nodes (10): Browser Testing (If Available), Consolidate Patterns, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions, Stop Condition (+2 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.25
Nodes (7): Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 11 - "critic_output.schema.json"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 13 - "NodeContractTests"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

## Knowledge Gaps
- **46 isolated node(s):** `$schema`, `type`, `additionalProperties`, `type`, `type` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `AgentRequest`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `AgentRequest`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `AgentRequest` to `NodeDependencies`, `nodes.py`?**
  _High betweenness centrality (0.066) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentRequest` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentResult` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `NodeDependencies` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`NodeDependencies` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkflowState` (e.g. with `AgentAdapter` and `AgentRequest`) actually correct?**
  _`WorkflowState` has 4 INFERRED edges - model-reasoned connections that need verification._