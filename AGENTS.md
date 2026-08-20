## Shared checkout: work in your own worktree

More than one coding agent (Claude Code, Codex) may be editing this repo at the
same time, in the same checkout. Git gives no warning about this, and a
`git checkout` moves HEAD under whoever else is mid-edit.

Rules:
- Before your first write, run `git status -sb`. If the tree is dirty with
  changes you did not make, or HEAD is on a branch you did not create, another
  agent is working here. Say so and stop rather than editing on top of it.
- Start your own work with `./shanks dev worktree <branch>`, which creates the
  worktree beside this one and carries in the two gitignored things a bare
  `git worktree add` leaves out: `.claude/settings.json` (without it *no* hooks
  fire there), `.claude/skills/` (without it none of this project's skills
  exist there) and `.venv` (without it the test commands do not exist). Do not
  hand-roll the worktree — a missed `.claude/` copy silently disables every
  guard. Creating a branch in place (`git checkout -b`) is fine too; it carries
  your own changes forward and is not blocked.
- Those are copied at creation time only, so a worktree made before a hook or
  skill change still runs the old wiring. Run `./shanks dev sync` from this
  checkout after any `.claude/` change to refresh every existing worktree.
- Never run `git add -A` / `git add .`. Stage the exact files you changed, so a
  concurrent agent's work cannot ride along in your commit.
- `hooks/guard-worktree.sh` blocks `git checkout`/`git switch` to another ref
  while tracked files are dirty. If you hit it, commit or stash your own work
  first; use `SHANKS_ALLOW_BRANCH_SWITCH=1` only when you are certain the dirty
  files are yours.

### Starting a parallel feature

From a clean, up-to-date `main` checkout:

```bash
git status -sb
git switch main
git pull --ff-only
./shanks dev worktree feat/<feature-name>
```

Run the agent in the directory printed by the command. Each agent commits and
pushes only its own branch; merge the branches through their pull requests
after validation. Keep the parent checkout for worktree setup, not editing.

### Finishing a parallel feature

After the feature PR is merged, verify the merge before deleting its worktree
or branch:

```bash
gh pr view <number> --json state,mergeCommit
git worktree remove ../shanks-<branch>
git branch -D <branch>
git remote prune origin
```

`git branch -d` can refuse a squash-merged branch because its original tip is
not an ancestor of `main`; use `-D` only after the merged check above. The
`dev/commands.md` `Parallel agents` examples show the matching worktree
creation flow. Keep the parent checkout for this cleanup as well.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- `explained.md` is human-only orientation documentation. Do not load it into an agent context; it is excluded from Graphify through `.graphifyignore`.
