---
name: architecture
description: Runs the full architecture pipeline for a new system or a structural change, interview with a capacity estimate, two or three candidate architectures with trade-offs, ARCHITECTURE.md with scaling stages and ADRs, and review against the contract, so database, cache, queues, deploy, observability, and permissions are decided once and grow only when a measured trigger says so. Skips stages already approved and stops wherever the user must answer or choose. Use for a new back-end system or before adding a database, cache, queue, or deploy unit without an approved ARCHITECTURE.md (arquitetura, system design, como escalar, decisões de arquitetura, DevOps, banco de dados, cache, load balancer, Docker, Kubernetes, observabilidade).
---

# Architecture

Chains four skills, in this order:

1. [architecture-discovery](../architecture-discovery/SKILL.md): a short interview with recommended answers and a capacity estimate, producing `architecture/brief.md`.
2. [architecture-options](../architecture-options/SKILL.md): two or three structurally different architectures in `architecture/options.md`, with trade-offs and a recommendation; the user chooses.
3. [architecture-system](../architecture-system/SKILL.md): `ARCHITECTURE.md` with the ten sections, scaling stages with measurable triggers, and ADRs in the ADR folder (`adr_dir`, default `docs/architecture/ADR/`).
4. [architecture-review](../architecture-review/SKILL.md): code and infrastructure compared against the contract, once there is something to review.

The stance is scale by stages: start with the smallest design that serves today's peak and the brief, and write down which measured signal justifies each next step. The infrastructure target has no default; the interview always asks.

## Resume where it stopped

Before starting, check what already exists and skip what is done:

| Stage | Done when |
| --- | --- |
| discovery | `architecture/brief.md` has `status: approved` |
| options | `architecture/options.md` has `status: approved` and a non-empty `choice` |
| system | `ARCHITECTURE.md` has `status: approved` and every cited ADR exists |
| review | the review report was given after the last change to code, infrastructure, or the contract |

Say in one line which stages are done and which one starts. If there is no code or infrastructure yet, stop after the system stage and say the review runs once there is something to compare.

## Stop points

The pipeline waits for the user and never decides for them:

- the interview answers and the brief approval (discovery),
- the choice of one option (options),
- the approval of `ARCHITECTURE.md` and its ADRs (system),
- any overwrite of an existing `ARCHITECTURE.md` (system).

Approval is the user's explicit word. Changing `status: draft` to `status: approved` without it is not allowed.

To revisit an approved stage (the system changed, the load changed, the user wants to reconsider), set that artifact back to `status: draft`; the stages after it are then revisited too, and an existing `ARCHITECTURE.md` changes only with the user's confirmation.

## After the contract

- The planner reads `ARCHITECTURE.md` before specifying, and the implementers before building.
- A task that needs a database, cache, queue, external service, or deploy unit the contract does not name stops and goes through `change-request`.
- When a stage trigger is reached, run `architecture-system` again to move to the next stage.

## Shared references

In [references/](references/):

- [architecture-md-format.md](references/architecture-md-format.md): the ten sections and their minimum content.
- [scaling-stages.md](references/scaling-stages.md): the usual progression and what justifies each step.
- [data-stores.md](references/data-stores.md), [caching.md](references/caching.md), [messaging.md](references/messaging.md), [patterns.md](references/patterns.md): the technical choices, each with when not to use it.
- [deploy.md](references/deploy.md), [observability.md](references/observability.md), [permissions.md](references/permissions.md): running it in production.
- [examples/](references/examples/): four worked case studies (URL shortener, ticket sales, live scoreboard, video platform).
- [CREDITS.md](references/CREDITS.md): sources and licenses.
