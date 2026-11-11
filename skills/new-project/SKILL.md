---
name: new-project
description: Scaffolds a spec-driven greenfield project with PRD, architecture, ADR, specs, tasks, and progress before implementation. Use when starting a new project, new repository, new product, or when the user asks to create a project from scratch (projeto novo, greenfield, do zero).
---

# New project

A greenfield project. Do not implement behavior before the problem, requirements, and acceptance criteria exist.

## Before creating files

1. Confirm the project name. Suggest a default from what was described. Ask about layout, git, or boilerplate preferences only if the user wants to decide; otherwise use sensible defaults.
2. Create the directory (prefer `~/Projects/` or `~/Developer/` if they exist; otherwise the home), initialize git, and move the agent to that root before any scaffolding.
3. Do not write the `docs/` tree in the home or the user's profile. Do not create `AGENTS.md`. It only goes in if the user asks for the versioned process inside the repository.

## Tree

Create only what has content:

```
docs/
├── product/PRD.md
├── architecture/ARCHITECTURE.md
├── architecture/ADR/
├── specs/
├── tests/VERIFICATION.md
├── tasks/
├── changes/
└── progress/CURRENT.md
```

If the user already indicated another canonical folder, use that one.

## PRD

`docs/product/PRD.md` must have: problem, desired outcome, users, functional requirements, non-functional requirements where they fit, constraints, assumptions, out of scope, acceptance criteria, existing behavior affected (none, if greenfield).

## Architecture

`docs/architecture/ARCHITECTURE.md`: overview, module boundaries, known data and integrations.

An ADR only for a decision already made. File `docs/architecture/ADR/0001-title.md` with: context, problem, decision, alternatives, rationale, consequences, risks. Do not rewrite an accepted ADR; create another if the decision changes.

## Spec, verification, and tasks

- `docs/specs/`: what the system must do, traceable to the PRD's requirements.
- `docs/tests/VERIFICATION.md`: levels (unit, integration, contract, e2e, acceptance, property-based, eval) and what each acceptance criterion requires.
- `docs/tasks/`: small steps. Each task cites the requirement, the tests, and the dependencies. Example: `TASK-X` depends on `TASK-Z`.
- `docs/progress/CURRENT.md`: current phase, next step, blockers. The next step is not "keep coding" by default.

## Verify the design

Before implementing, check the spec and architecture against the PRD and the acceptance criteria. Fix the artifact, not the code, if the design does not hold.

## Implement

Only after the plan. Each task follows the `implementation` skill. Proportional ceremony: if the user asked for a minimal sketch, deliver a short PRD, one spec, and the first task, and stop to confirm before expanding.
