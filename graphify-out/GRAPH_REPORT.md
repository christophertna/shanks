# Graph Report - shanks  (2026-08-03)

## Corpus Check
- 27 files · ~15,203 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 353 nodes · 798 edges · 25 communities (21 shown, 4 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 94 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `972be597`
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
- .__init__
- .__init__
- adapters.py
- AgentRequest
- NodeContractTests
- AgentAdapter
- ClaudeOpus48CriticAdapter
- LocalTestAdapter

## God Nodes (most connected - your core abstractions)
1. `AgentRequest` - 51 edges
2. `AgentResult` - 50 edges
3. `NodeDependencies` - 41 edges
4. `WorkflowState` - 38 edges
5. `NodeContractTests` - 36 edges
6. `build_graph()` - 27 edges
7. `AgentAdapter` - 23 edges
8. `GitHubAdapter` - 22 edges
9. `default_dependencies()` - 22 edges
10. `GraphRoutingTests` - 19 edges

## Surprising Connections (you probably didn't know these)
- `build_graph()` --indirect_call--> `route_after_building()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_commit()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_intake()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_item_router()`  [INFERRED]
  graph.py → workflow/nodes.py
- `build_graph()` --indirect_call--> `route_after_planning()`  [INFERRED]
  graph.py → workflow/nodes.py

## Import Cycles
- None detected.

## Communities (25 total, 4 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.18
Nodes (15): build_graph(), Build the workflow with optional adapters or a Claude/Codex choice., GraphRoutingTests, _initial_state(), RecordingRepository, SequenceAdapter, _stub_dependencies(), Deterministic adapter used for local graph development and tests. (+7 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.08
Nodes (26): BaseHTTPRequestHandler, ModuleType, graph_revision(), graph_source_files(), GraphRequestHandler, load_graph_module(), main(), Path (+18 more)

### Community 2 - "nodes.py"
Cohesion: 0.07
Nodes (61): LangGraph workflow assembled from standardized agent nodes., NodeFunction, TypedDict, Common interfaces shared by agent adapters and graph nodes., Translate common agent output into shared workflow state fields., state_update_from_result(), Reusable workflow state, agent contracts, adapters, and nodes., attempt_limit() (+53 more)

### Community 3 - "Shanks"
Cohesion: 0.40
Nodes (4): Interactive workflow, Main pieces, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "AgentRequest"
Cohesion: 0.14
Nodes (13): ClaudeAdapter, CodexAdapter, GPT56LunaCriticAdapter, Adapter for direct Codex CLI execution., Adapter for direct Claude Code CLI execution., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., claude_opus_4_8_dependencies(), default_dependencies() (+5 more)

### Community 6 - "Ralph Agent Instructions"
Cohesion: 0.17
Nodes (11): Browser Testing (If Available), Consolidate Patterns, Directories, Graphify First, Important, Progress Report Format, Quality Requirements, Ralph Agent Instructions (+3 more)

### Community 7 - "GitHub Commits and PRs"
Cohesion: 0.09
Nodes (19): ADR Format, Numbering, Optional sections, Template, What qualifies, When to offer an ADR, CONTEXT.md Format, Rules (+11 more)

### Community 8 - "Ralph Agent Instructions (Codex)"
Cohesion: 0.22
Nodes (8): Directories, Files, Graphify First, Progress Report Format, Quality Requirements, Ralph Agent Instructions (Codex), Stop Condition, Your Task

### Community 11 - "critic_output.schema.json"
Cohesion: 0.17
Nodes (11): approved, feedback, additionalProperties, type, type, properties, approved, feedback (+3 more)

### Community 12 - "default_dependencies"
Cohesion: 0.29
Nodes (5): Protocol, Interface for local commits and the final GitHub handoff., Commit one validated item's intended files., Push the branch and create its pull request., RepositoryAdapter

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
Cohesion: 0.16
Nodes (13): _critic_result(), _debugger_request(), _debugger_result(), DebuggerAdapter, _parse_json_object(), Agent adapter implementations for graph nodes and external runners., Analyze validation failures with a read-only structured Codex run., Parse a JSON object even when the CLI adds non-JSON log lines. (+5 more)

### Community 20 - "AgentRequest"
Cohesion: 0.20
Nodes (9): _critic_request(), _format_request(), RalphAdapter, Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story., Add the shared read-only audit instructions to a critic request., Create a stable prompt envelope for CLI-backed adapters., AgentRequest (+1 more)

### Community 21 - "NodeContractTests"
Cohesion: 0.21
Nodes (3): NodeContractTests, GitHubAdapter, Commit validated items, then push the branch and open its PR.

### Community 22 - "AgentAdapter"
Cohesion: 0.29
Nodes (5): CheapCriticAdapter, Deterministic low-cost critic used by the default graph., AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles., Run the backend for one workflow node invocation.

### Community 23 - "ClaudeOpus48CriticAdapter"
Cohesion: 0.33
Nodes (4): ClaudeOpus48CriticAdapter, Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter

## Knowledge Gaps
- **67 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+62 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_graph()` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `AgentRequest`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `AgentRequest` to `NodeDependencies`, `nodes.py`, `AgentRequest`, `adapters.py`, `NodeContractTests`, `AgentAdapter`, `ClaudeOpus48CriticAdapter`, `LocalTestAdapter`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `nodes.py`, `AgentRequest`, `default_dependencies`, `adapters.py`, `AgentRequest`, `NodeContractTests`, `AgentAdapter`, `ClaudeOpus48CriticAdapter`, `LocalTestAdapter`?**
  _High betweenness centrality (0.070) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentRequest` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`AgentResult` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `NodeDependencies` (e.g. with `GraphRoutingTests` and `RecordingRepository`) actually correct?**
  _`NodeDependencies` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WorkflowState` (e.g. with `AgentAdapter` and `AgentRequest`) actually correct?**
  _`WorkflowState` has 5 INFERRED edges - model-reasoned connections that need verification._