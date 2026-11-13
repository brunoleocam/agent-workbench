---
name: architecture-system
description: Writes the architecture contract ARCHITECTURE.md from the option the user chose, with the ten fixed sections, scaling stages with measurable triggers, and an ADR for every choice between real alternatives; also updates the contract when a stage trigger is reached. Use after architecture-options, or to record an architecture decision or move to the next scaling stage (gerar ARCHITECTURE.md, contrato de arquitetura, registrar decisão de arquitetura, ADR, avançar estágio de escala).
---

# Architecture system

Third step of `architecture`. Reads `architecture/brief.md` and the choice in `architecture/options.md`, and writes `ARCHITECTURE.md` at the project root plus ADRs in the ADR folder (`adr_dir`, default `docs/architecture/ADR/`). From then on the planner, the implementers, and the architecture reviewer follow the contract.

## 0. Precondition

`architecture/options.md` must have `status: approved` and a non-empty `choice`. Without a recorded choice, stop and say to finish [architecture-options](../architecture-options/SKILL.md). Never pick an option on the user's behalf.

## 1. Existing ARCHITECTURE.md

If `ARCHITECTURE.md` already exists, read it first. Propose the changes section by section (what stays, what changes, and why), and overwrite only after the user's explicit confirmation. Without confirmation, leave the file as it is.

## 2. Write the contract

Write `ARCHITECTURE.md` from [references/architecture-template.md](references/architecture-template.md), following [../architecture/references/architecture-md-format.md](../architecture/references/architecture-md-format.md):

- Front matter `status: draft`, `option` (the `choice` of `architecture/options.md`, uppercase), and `stage: 0`.
- The ten sections, with these headings, in this order, nothing renamed.
- The minimum content of each section, as listed in the format reference: diagram and dependency rule (2); database, migrations, backup with RPO and RTO (3); cache or the decision not to cache (4); sync and async flows with delivery guarantee and idempotency (5); target, environments, commit-to-production path (6); log format with correlation id, metrics, alerts with thresholds (7); authorization model, secrets, exposed ports (8).
- A section that does not apply stays in the file and says why in one sentence.
- Numbers come from the brief and its capacity estimate.

## 3. Scaling stages (section 9)

- Stage 0 is the chosen option, marked `(atual)` in its title.
- At least two later stages, each with `- Gatilho:`, `- Mudança:`, `- Custo:`, and `- Pré-requisito:`.
- A trigger compares a metric with a threshold: an operator (`>`, `<`, `acima de`, `mais de`, ...), a number, a unit, and where it is measured, as in "Gatilho: p95 de leitura > 300 ms por 7 dias (fonte: APM)". "latência de 300 ms" has no operator and is refused; a duration alone ("por 7 dias") is not a threshold. The full rule is in [../architecture/references/architecture-md-format.md](../architecture/references/architecture-md-format.md).
- A vague trigger ("quando crescer", "quando ficar lento", "se precisar") is never recorded. Rewrite it with a metric and a value taken from the brief, or ask the user which value to use.
- Components that the option left out because today's load does not need them (see [../architecture/references/scaling-stages.md](../architecture/references/scaling-stages.md)) go here, each behind its trigger.

## 4. ADRs

For every choice between real alternatives in sections 3 to 8 (for example PostgreSQL or MongoDB, Redis or in-process cache, queue or direct call, VPS or PaaS, RBAC or ABAC, shared tables or schema per tenant):

1. Create an ADR in the project's ADR folder: `adr_dir` in `.cursor/agent-system/layout.json` when it exists, otherwise `docs/architecture/ADR/`. Use the next free number and the format of the existing ADRs: `# ADR-NNNN: <title>`, `Status:`, `Date:`, `## Context`, `## Decision`, `## Alternatives`, `## Consequences`. Name the problem, the rationale, and the risks inside Context, Decision, and Consequences, as the `planner` does.
2. Cite it in the section as `ADR-NNNN`.

Choices with no real alternative for this project do not need an ADR. Never edit an accepted ADR: when a decision changes, write a new ADR that supersedes the old one, and set the old one to `Status: superseded by ADR-NNNN`.

## 5. Approve

Show the user a short summary: the components, the main decisions with their ADRs, and the stages with their triggers. Ask for approval or corrections. Only after the user's explicit confirmation, change the front matter to `status: approved` and the ADRs to `Status: accepted`.

## 6. Moving to the next stage

When the user says a trigger was reached, or asks to move to the next stage:

1. Confirm which trigger and the measurement that reached it.
2. Propose the changes section by section (often 2, 3, 4, 5, 6, and 7), the new ADR, and the new later stage if fewer than two would remain. Wait for the user's explicit confirmation; without it, change nothing.
3. After the confirmation, set `status: draft` while editing, update the sections, move `(atual)` to the new stage, and update `stage:` in the front matter.
4. Create the ADR for the move, citing the trigger and the measurement; it supersedes the earlier ADR of each decision it changes.
5. Show the result and set `status: approved` again only with the user's confirmation.

## References

- Format and minimum content: [../architecture/references/architecture-md-format.md](../architecture/references/architecture-md-format.md).
- Patterns, data stores, caching, messaging, deploy, observability, permissions: [../architecture/references/](../architecture/references/).
- Worked contracts: [../architecture/references/examples/](../architecture/references/examples/).

## Done when

`ARCHITECTURE.md` exists with `status: approved`, the ten sections in order, at least two later stages with measurable triggers, and every cited ADR present in the ADR folder. Next step: [architecture-review](../architecture-review/SKILL.md), once code or infrastructure exists.

Do not write production code or infrastructure files in this step.
