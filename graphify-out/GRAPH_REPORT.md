# Graph Report - shanks  (2026-08-05)

## Corpus Check
- 32 files · ~23,403 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 508 nodes · 1239 edges · 27 communities (24 shown, 3 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 129 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f1c46ebf`
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
- RepositoryAdapter
- Any
- RalphAdapter

## God Nodes (most connected - your core abstractions)
1. `AgentResult` - 67 edges
2. `NodeDependencies` - 59 edges
3. `AgentRequest` - 58 edges
4. `WorkflowState` - 55 edges
5. `NodeContractTests` - 46 edges
6. `GraphRoutingTests` - 35 edges
7. `StubAgentAdapter` - 35 edges
8. `GitHubAdapter` - 33 edges
9. `build_graph()` - 28 edges
10. `SubprocessAgentAdapter` - 23 edges

## Surprising Connections (you probably didn't know these)
- `VersionedSqliteSaver` --uses--> `NodeDependencies`  [INFERRED]
  graph.py → workflow/nodes.py
- `VersionedSqliteSaver` --uses--> `WorkflowState`  [INFERRED]
  graph.py → workflow/state.py
- `SequenceAdapter` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `RecordingRepository` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py
- `PreflightOnlyRepository` --uses--> `AgentRequest`  [INFERRED]
  tests/test_graph.py → workflow/contracts.py

## Import Cycles
- None detected.

## Communities (27 total, 3 thin omitted)

### Community 0 - "NodeDependencies"
Cohesion: 0.15
Nodes (16): Command, build_graph(), GraphRoutingTests, _initial_state(), invoke_with_approvals(), PreflightOnlyRepository, Keep graph tests isolated from the shared production checkpoint store., RecordingRepository (+8 more)

### Community 1 - "GraphRequestHandler"
Cohesion: 0.06
Nodes (39): BaseHTTPRequestHandler, ModuleType, _current_item(), execution_state(), graph_revision(), graph_source_files(), GraphRequestHandler, _json_safe() (+31 more)

### Community 2 - "nodes.py"
Cohesion: 0.07
Nodes (35): build_graph(), _migrate_checkpoint_tuple(), LangGraph workflow assembled from standardized agent nodes., Return a checkpoint tuple whose state channels use the current schema., SqliteSaver that migrates workflow state on reads and writes., Open the SQLite checkpoint store shared by workflow and viewer processes., Build the workflow with optional adapters or a Claude/Codex choice., shared_checkpointer() (+27 more)

### Community 3 - "Shanks"
Cohesion: 0.33
Nodes (5): Interactive workflow, Main pieces, Preflight checks, Quick start, Shanks

### Community 4 - "ralph.sh"
Cohesion: 0.18
Nodes (6): initialize_metadata_file(), mark_item_built(), RALPH_BASE_DIR, RALPH_PROJECT_DIR, ralph.sh script, upsert_metadata()

### Community 5 - "VersionedSqliteSaver"
Cohesion: 0.24
Nodes (8): _audit_command(), _estimate_tokens(), _format_request(), Create a stable prompt envelope for CLI-backed adapters., Use a conservative four-characters-per-token estimate for CLI text., Remove common credentials before command output enters workflow state., Return a redacted command suitable for the persisted run manifest., redact_secrets()

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
Nodes (18): ValueError, CheapCriticAdapter, ClaudeAdapter, CodexAdapter, _command_path_arguments(), _critic_result(), _debugger_result(), _parse_json_object() (+10 more)

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
Cohesion: 0.13
Nodes (15): ClaudeOpus48CriticAdapter, GPT56LunaCriticAdapter, Normalize a read-only CLI critic into the common agent result shape., Run the critic_auditor as a read-only GPT-5.6 Luna Codex subagent., Run the critic_auditor as a read-only Claude Opus 4.8 subagent., StructuredCriticAdapter, AgentAdapter, Interface implemented by Ralph, model CLIs, and test doubles. (+7 more)

### Community 22 - "GitHubAdapter"
Cohesion: 0.15
Nodes (5): NodeContractTests, _attach_commands(), GitHubAdapter, Commit validated items, then push the branch and open its PR., Keep the full command trail when a multi-command operation fails.

### Community 23 - "WorkflowState"
Cohesion: 0.05
Nodes (88): Any, NodeFunction, TypedDict, Common interfaces shared by agent adapters and graph nodes., Translate common agent output into shared workflow state fields., state_update_from_result(), Reusable workflow state, agent contracts, adapters, and nodes., _approval_denied() (+80 more)

### Community 27 - "RepositoryAdapter"
Cohesion: 0.22
Nodes (6): Protocol, Interface for local commits and the final GitHub handoff., Check the repository and execution environment before intake., Commit one validated item's intended files., Push the branch and create its pull request., RepositoryAdapter

### Community 29 - "Any"
Cohesion: 0.11
Nodes (15): _critic_request(), _debugger_request(), DebuggerAdapter, LocalTestAdapter, _preflight_failure(), Run a configured CLI backend through the common adapter contract., Add the shared read-only audit instructions to a critic request., Give the debugger failure evidence and a read-only analysis mandate. (+7 more)

### Community 30 - "RalphAdapter"
Cohesion: 0.20
Nodes (5): _parse_uncertainties(), RalphAdapter, Extract the builder's concise uncertainty bullets from Ralph output., Adapter for the project-local Ralph runner., Persist the graph's full PRD before Ralph reads its next story.

## Knowledge Gaps
- **72 isolated node(s):** `RALPH_BASE_DIR`, `RALPH_PROJECT_DIR`, `$schema`, `type`, `additionalProperties` (+67 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `NodeDependencies` connect `NodeDependencies` to `GraphRequestHandler`, `nodes.py`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `RepositoryAdapter`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.089) - this node is a cross-community bridge._
- **Why does `AgentResult` connect `NodeDependencies` to `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `RepositoryAdapter`, `Any`, `RalphAdapter`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Why does `AgentRequest` connect `Any` to `NodeDependencies`, `VersionedSqliteSaver`, `GitHubAdapter`, `adapters.py`, `GitHubAdapter`, `WorkflowState`, `RalphAdapter`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._
- **Are the 20 inferred relationships involving `AgentResult` (e.g. with `GraphRoutingTests` and `PreflightOnlyRepository`) actually correct?**
  _`AgentResult` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `NodeDependencies` (e.g. with `VersionedSqliteSaver` and `GraphRoutingTests`) actually correct?**
  _`NodeDependencies` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 20 inferred relationships involving `AgentRequest` (e.g. with `GraphRoutingTests` and `PreflightOnlyRepository`) actually correct?**
  _`AgentRequest` has 20 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `WorkflowState` (e.g. with `VersionedSqliteSaver` and `AgentAdapter`) actually correct?**
  _`WorkflowState` has 6 INFERRED edges - model-reasoned connections that need verification._