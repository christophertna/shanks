# Graph Report - shanks  (2026-08-02)

## Corpus Check
- 18 files · ~7,222 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 189 nodes · 405 edges · 16 communities (13 shown, 3 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 47 edges (avg confidence: 0.53)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `057ab281`
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
- WorkflowState
- create_nodes
- __init__.py
- select_next_item

## God Nodes (most connected - your core abstractions)
1. `WorkflowState` - 28 edges
2. `AgentRequest` - 27 edges
3. `AgentResult` - 27 edges
4. `NodeDependencies` - 26 edges
5. `StubAgentAdapter` - 19 edges
6. `build_graph()` - 18 edges
7. `AgentAdapter` - 15 edges
8. `create_nodes()` - 15 edges
9. `CheapCriticAdapter` - 13 edges
10. `GraphRoutingTests` - 12 edges

## Surprising Connections (you probably didn't know these)
- `build_graph()` --indirect_call--> `route_after_building()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_item_router()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_planning()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_validation()`  [INFERRED]
  graph.py → workflow/nodes.py
- `SequenceAdapter` --uses--> `StubAgentAdapter`  [INFERRED]
  tests/test_graph.py → workflow/adapters.py

## Import Cycles
- None detected.

## Communities (16 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.32
Nodes (7): build_graph(), Build the workflow with optional provider adapters., GraphRoutingTests, _initial_state(), SequenceAdapter, NodeDependencies, Backends injected into the standardized graph nodes.

### Community 1 - "GraphRequestHandler"
Cohesion: 0.11
Nodes (17): BaseHTTPRequestHandler, ModuleType, graph_revision(), graph_source_files(), GraphRequestHandler, load_graph_module(), Path, Serve graph.html and regenerate its Mermaid definition from graph.py. (+9 more)

### Community 2 - "nodes.py"
Cohesion: 0.24
Nodes (15): Translate common agent output into shared workflow state fields., state_update_from_result(), building(), critic_auditor(), _current_item(), debugger(), _mark_current_item_passed(), _merge_files() (+7 more)

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

### Community 12 - "WorkflowState"
Cohesion: 0.23
Nodes (11): LangGraph workflow assembled from standardized agent nodes., Route code to the critic, validation, or a safe attempt-limit stop., Start the next item or send an already-complete run to the router., Send failures to debugging and successes to the item router., Start the next incomplete item or finish the workflow., route_after_building(), route_after_item_router(), route_after_planning() (+3 more)

### Community 13 - "create_nodes"
Cohesion: 0.29
Nodes (7): NodeFunction, attempt_limit(), create_nodes(), default_dependencies(), Stop safely when an item needs more build attempts than allowed., Return side-effect-free adapters for local graph development., Create state-only node callables with injected agent backends.

### Community 14 - "__init__.py"
Cohesion: 0.33
Nodes (5): TypedDict, Reusable workflow state, agent contracts, adapters, and nodes., PRDItem, Shared state types for the graph-engineering workflow., A single item that the workflow can build and validate.

### Community 15 - "select_next_item"
Cohesion: 0.29
Nodes (7): _default_plan(), item_router(), planning(), Prepare the decision to start another item or finish the workflow., Select the first incomplete item at or after the current index., Plan the current incomplete item without losing retry context., select_next_item()

## Knowledge Gaps
- **39 isolated node(s):** `graphify`, `graphify`, `The main flow`, ``graph.py``, ``workflow/state.py`` (+34 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `NodeDependencies` to `GraphRequestHandler`, `WorkflowState`, `create_nodes`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `AgentRequest` to `NodeDependencies`, `nodes.py`, `WorkflowState`, `__init__.py`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `WorkflowState` connect `WorkflowState` to `NodeDependencies`, `nodes.py`, `AgentRequest`, `create_nodes`, `__init__.py`, `select_next_item`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Are the 4 inferred relationships involving `WorkflowState` (e.g. with `AgentAdapter` and `AgentRequest`) actually correct?**
  _`WorkflowState` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentRequest` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentResult` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `NodeDependencies` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`NodeDependencies` has 9 INFERRED edges - model-reasoned connections that need verification._