# Graph Report - shanks  (2026-08-03)

## Corpus Check
- 22 files · ~9,743 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 238 nodes · 518 edges · 16 communities (13 shown, 3 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 63 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4739d3c5`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- NodeDependencies
- GraphRequestHandler
- nodes.py
- Shanks
- ralph.sh
- AgentRequest
- Ralph Agent Instructions
- GitHub Commits and PRs
- Ralph Agent Instructions (Codex)
- AGENTS.md
- CLAUDE.md
- critic_output.schema.json
- default_dependencies
- NodeContractTests
- GitHub Commits and PRs

## God Nodes (most connected - your core abstractions)
1. `AgentRequest` - 34 edges
2. `AgentResult` - 32 edges
3. `NodeDependencies` - 30 edges
4. `WorkflowState` - 30 edges
5. `build_graph()` - 20 edges
6. `NodeContractTests` - 19 edges
7. `StubAgentAdapter` - 19 edges
8. `AgentAdapter` - 19 edges
9. `create_nodes()` - 16 edges
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

## Communities (16 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.25
Nodes (11): build_graph(), Build the workflow with optional provider adapters., GraphRoutingTests, _initial_state(), SequenceAdapter, Deterministic adapter used for local graph development and tests., StubAgentAdapter, NodeDependencies (+3 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.10
Nodes (21): BaseHTTPRequestHandler, ModuleType, graph_revision(), graph_source_files(), GraphRequestHandler, load_graph_module(), Path, Serve graph.html and regenerate its Mermaid definition from graph.py. (+13 more)

### Community 2 - "nodes.py"
Cohesion: 0.09
Nodes (47): LangGraph workflow assembled from standardized agent nodes., NodeFunction, TypedDict, Translate common agent output into shared workflow state fields., state_update_from_result(), Reusable workflow state, agent contracts, adapters, and nodes., attempt_limit(), building() (+39 more)

### Community 3 - "Shanks"
Cohesion: 0.50
Nodes (3): Main pieces, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (5): initialize_metadata_file(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "AgentRequest"
Cohesion: 0.10
Nodes (35): Protocol, NodeContractTests, CheapCriticAdapter, ClaudeAdapter, ClaudeOpus48CriticAdapter, CodexAdapter, _critic_request(), _critic_result() (+27 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.29
Nodes (5): claude_opus_4_8_dependencies(), gpt_5_6_luna_dependencies(), Path, Use the read-only GPT-5.6 Luna subagent for critic_auditor., Use the read-only Claude Opus 4.8 subagent for critic_auditor.

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.22
Nodes (8): Directories, Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 11 - "critic_output.schema.json"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 13 - "NodeContractTests"
Cohesion: 0.22
Nodes (8): Boundaries, Intensity, Output, Persistence, Ponytail, Rules, The ladder, When NOT to be lazy

### Community 15 - "GitHub Commits and PRs"
Cohesion: 0.29
Nodes (6): Commit, push, and PR checks, Commit subject, GitHub Commits and PRs, Merge authority, Pull request description, Pull request title

## Knowledge Gaps
- **42 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+37 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `AgentRequest` to `NodeDependencies`, `nodes.py`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Why does `NodeDependencies` connect `NodeDependencies` to `nodes.py`, `AgentRequest`, `GitHub Commits and PRs`?**
  _High betweenness centrality (0.068) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentRequest` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`AgentResult` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `NodeDependencies` (e.g. with `GraphRoutingTests` and `SequenceAdapter`) actually correct?**
  _`NodeDependencies` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `WorkflowState` (e.g. with `AgentAdapter` and `AgentRequest`) actually correct?**
  _`WorkflowState` has 4 INFERRED edges - model-reasoned connections that need verification._