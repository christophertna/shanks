## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- `explained.md` is human-only orientation documentation. Do not load it into an agent context; it is excluded from Graphify through `.graphifyignore`.

## Project overview

Shanks is a LangGraph workflow that runs "Ralph-style" agent tasks: an intake step
chooses `learn` (documentation) or `implement` (feature) mode, then drives a
plan → build/revise → critic feedback → validate → next-item loop. `graph.py`
assembles the graph; `serve_graph.py` serves a live Mermaid viewer at
`http://127.0.0.1:8765/graph.html`. Core logic lives in `workflow/` (`state.py`,
`contracts.py`, `adapters.py`, `nodes.py`).

## Commands

- Tests: `.venv/bin/python -m unittest discover -s tests` (use the checked-in
  venv's interpreter, not system `python`)
- Viewer: `.venv/bin/python serve_graph.py`
- No linter/formatter is configured in this repo.

## Gotchas

- The graph pauses at the `intake` node on first invocation and must be resumed
  with `Command(resume="implement"|"learn")` — a plain `graph.invoke()` will not
  run to completion.
- Each validated PRD item is committed locally automatically as part of the
  graph run — the workflow itself makes commits, not just the human/agent
  driving it.
- The final step of an `implement` run pushes the current non-`main` branch and
  opens a PR via `gh` — `gh` must be pre-authenticated.
- Skills are split across three locations with overlapping content:
  `.claude/skills/`, `.agents/skills/`, and top-level `skills/`. Check which
  copy is canonical before editing one.

## Repo etiquette

- Commit style: Conventional Commits (`feat:`, `fix:`, `chore:`, `ci:`), short
  imperative subject, no scopes, PR number in parens when applicable.
