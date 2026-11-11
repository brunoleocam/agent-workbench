---
name: brainstorm
description: Refines a rough idea into an approved design through structured Socratic questioning, alternative exploration, and incremental validation. Use immediately when creating or developing anything, before writing code or an implementation plan (brainstorm, ideia, desenhar, antes de codar, antes do plano).
---

# Brainstorm

Use before creating or developing behavior, a product, or an interface, and before writing code or an implementation plan, when there is no approved design yet.

Do not use when the user told you to execute an already approved spec or plan, when the request is only investigation, review, commit, push, or a trivial fix.

Do not write code, scaffold a project, or call `implementation-plan` or `implementation` until the user approves the design.

## Flow

1. Read the repository context (code, spec, recent commits) before the first question.
2. If the idea spans several independent systems, stop and propose splitting it into parts. Brainstorm only the first.
3. Ask one question per message. Prefer a closed choice. Goal, constraint, and success criterion.
4. Propose 2 or 3 approaches, with trade-offs and a recommendation.
5. Present the design in short parts. Ask for approval of each part before the next.
6. With the design approved, write the spec in the repo's canonical place, or in `docs/specs/` if that is the tree. No placeholders. No contradiction with what was approved.
7. Ask the user to review the spec. Adjust if they ask.
8. The next step is `implementation-plan`. Do not implement in this turn.
