---
name: roadmap-review
description: Review and maintain `dev/new features.txt` during project work. Use when starting or finishing a task, evaluating a change, or explicitly reviewing the roadmap; analyze the code, present findings and suggestions, ask for a poll decision before editing, and identify worthwhile improvements, features, implementations, fixes, tests, refactors, documentation, tooling, security, performance, and other changes.
---

# Roadmap Review

Read and maintain the repository roadmap as part of the current work.

## Workflow

1. Read `dev/new features.txt` at the repository root before planning or closing
   the work. Preserve its plain-text format and existing sections.
2. Compare the current task, code discoveries, failures, and follow-up risks with
   the roadmap. Ask the agent explicitly: “Is there anything worthwhile to add
   to the roadmap?” Treat “nothing worth adding” as a valid answer.
3. Check for concrete candidates across all of these areas:
   - improvements, refactors, architecture, developer experience, and usability;
   - product or user-facing features and integrations;
   - implementations, automation, migrations, and infrastructure;
   - bug fixes, regressions, reliability, security, and performance;
   - tests, regression coverage, CI, observability, documentation, and tooling;
   - other follow-up changes revealed by the current work.
4. Present the review findings to the user before editing the roadmap. Summarize
   the relevant code and roadmap observations, list concrete suggestions and any
   proposed priority changes, and explain which possible ideas were rejected as
   duplicates or speculation. State clearly when no change is recommended.
5. Ask the user for a poll-style decision before changing `dev/new features.txt`.
   Use the product's `AskUserQuestion`/poll UI when available, with one question
   such as “What should I do with these roadmap suggestions?” and these choices:
   - **Implement in roadmap** — apply the proposed additions and reordering.
   - **Reject suggestions** — leave the roadmap unchanged.
   - **Discuss first** — continue the conversation before editing.
   Do not edit the roadmap while waiting. If the user chooses discussion, answer
   the follow-up and ask the same decision poll again. If the user rejects the
   suggestions, report that no roadmap changes were made.
6. After the user chooses implementation, add only actionable, non-duplicate
   items. Put committed or clearly planned work in the appropriate priority list.
   Put useful but lower-confidence ideas in the existing `Suggestions` section.
   Give each addition a concise title and enough rationale or implementation
   direction to make it actionable.
7. Re-order the numbered item listing whenever priority changes. The listing is
   ordered by priority, so move an item to the appropriate position and renumber
   the full list sequentially without gaps. For example, if a newly identified
   feature should be implemented ASAP, move it to the top of the Priority 1 list
   and shift the former items down.
8. If the current work completes an existing roadmap item, remove that completed
   item and renumber the remaining items; remove any stale related suggestion.
9. Leave the file unchanged when the review finds no worthwhile addition or the
   user rejects the proposals. Do not add speculative filler or rewrite
   unrelated roadmap prose.
10. Re-read the edited section and verify that numbering, priority order,
    indentation, cross-references, and suggestions remain consistent.
