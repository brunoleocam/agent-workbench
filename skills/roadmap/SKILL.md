---
name: roadmap
description: Creates, shows, and updates the project roadmap in docs/progress/ROADMAP.md, with phases, tasks, status, and the current position; optionally renders a Canvas view. Use when the user wants to know which stage they are in, what is done and what is left, or when planning large work in a project with /init-agent-system (roadmap, em que etapa estou, o que falta, progresso do plano).
---

# Roadmap

A single file: `docs/progress/ROADMAP.md`, at the project root. It applies only in a project with `.cursor/agent-system/state.json`. Without it, tell the user to run `/init-agent-system` and stop.

## Format

```markdown
# Roadmap — <project or front>

> You are here: Phase 2 — API · TASK-008

Legend: [x] done · [~] in progress · [ ] pending · [!] blocked

## Phase 1 — Data
- [x] TASK-001 Order model — spec: docs/specs/order.md
- [x] TASK-002 Migration

## Phase 2 — API
- [~] TASK-008 Inventory reservation — depends on TASK-002
- [!] TASK-009 Payment — blocked: gateway credential
- [ ] TASK-010 Webhook — depends on TASK-009
```

- One line per task: status, ID, short title, dependency or blocker, a link to the spec or task if any.
- Phases in dependency order. The IDs are the same as in `docs/tasks/`.
- The "You are here" line points to the phase and the task in progress. The session-start hook and `/agent-status` read this line and count the `[x]`, `[~]`, `[ ]`, and `[!]`. (The Portuguese marker "Você está aqui" is still read in existing roadmaps.)

## Modes

No argument: show. With "create", "update", or "visual": the requested mode.

- **Show**: read only `ROADMAP.md`. Reply with the "You are here" line, the count by status, the tasks in progress and blocked, and the next 3 pending ones whose dependencies are already done. Do not list the done tasks.
- **Create**: from the approved plan or the tasks in `docs/tasks/`. If there is no plan, use `/staged-task` or the `planner` first. If a roadmap already exists, extend it; do not rewrite done items.
- **Update**: edit only the lines that changed and the "You are here" line. Status `[x]` only with evidence (test, command, or review). A new task from a change request goes in the right phase, with its dependency.
- **Visual**: read the `canvas` skill and generate a canvas from `ROADMAP.md`, with phases as columns or lanes, tasks colored by status, dependencies, and the current position highlighted. The file remains the source of truth; the canvas is only the view.
