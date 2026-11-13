---
name: architecture-options
description: Turns an approved architecture brief into 2 or 3 structurally different candidate architectures, each with a Mermaid diagram and a trade-off table (cost range, operational complexity, single points of failure, what happens when load doubles, when it stops serving), recommends the simplest one that meets the brief, and stops for the user to choose. Use after architecture-discovery (opções de arquitetura, comparar arquiteturas, trade-offs, monólito ou microsserviços, qual arquitetura escolher).
---

# Architecture options

Second step of `architecture`. Reads `architecture/brief.md` and produces `architecture/options.md`, the input for [architecture-system](../architecture-system/SKILL.md).

## 0. Precondition

`architecture/brief.md` must exist with `status: approved`. Without it, stop and say to run [architecture-discovery](../architecture-discovery/SKILL.md) first. If `architecture/options.md` has `status: approved` and a non-empty `choice`, this step is done; the next one is `architecture-system`. To revisit the options (the brief changed, or the user wants to reconsider), set `status: draft` again, clear `choice`, and regenerate.

## 1. Build 2 or 3 options that really differ

Every pair of options differs in at least one of these axes:

- **Deploy units**: one app, an app plus workers, several services.
- **Data topology**: how many stores and of which kind (one relational database; database plus cache; database plus search index; a store per service).
- **Communication style**: synchronous calls, asynchronous work through a queue, events.

A difference of vendor only (PostgreSQL or MySQL, one cloud or another) is not a different option; it is a detail inside one option, decided later in an ADR.

In an existing system, one option is always **keep the current architecture with adjustments**, described from the `## Arquitetura atual` section of the brief.

## 2. Describe each option

For each option, from [references/options-template.md](references/options-template.md):

- A Mermaid diagram of the components, data stores, and external services, with the direction of each call.
- Two or three sentences on how it handles the main flows of the brief.
- One row in the trade-off table with five columns: monthly cost range for the brief's load; operational complexity (low, medium, or high, with the reason); single points of failure; what happens when the load doubles; the load or condition at which it stops serving.

Cost ranges are rough orders of magnitude without live price lookup; say so in the file. Use the capacity estimate of the brief, not round guesses.

## 3. Recommend the simplest option that meets the brief

Recommend the option with the **lowest operational complexity** that serves the peak load and the quality attributes of the brief, and say why in terms of brief items.

Components that are often premature: Kubernetes, microservices, a distributed cache, a queue or broker, a database per service, a service mesh, event sourcing. If the recommendation includes any of them, cite the brief item that requires it (a latency target, a burst pattern, a legal obligation, slow work that cannot stay in the request path). If no item requires it, leave it out of the recommendation; `architecture-system` can place it in a later scaling stage with a measurable trigger. See the rule at the end of [../architecture/references/scaling-stages.md](../architecture/references/scaling-stages.md).

Explain each rejected option in one line: what it would cost and which brief item does not justify that cost.

## 4. Stop for the choice

1. Write `architecture/options.md` with the options, the table, and `## Recomendação`.
2. Show a short summary to the user: the options in one line each, the recommendation, and the main trade-off.
3. **Stop and wait** for the user to choose. In Claude Code, use the closed-choice question tool when available, recommended option first.
4. Only after the user names an option, record it in the front matter: `choice: B` (uppercase letter), `chosen_on: <date>`, and `status: approved`. Until then `choice` stays empty and `status` stays `draft`.

Do not write `ARCHITECTURE.md`, ADRs, code, or infrastructure files in this step. If the user asks to combine parts of two options, explain the coherence risk and propose a single revised option instead of pasting the parts.

## References

- Patterns and when not to use them: [../architecture/references/patterns.md](../architecture/references/patterns.md).
- Data stores: [../architecture/references/data-stores.md](../architecture/references/data-stores.md).
- Deploy targets and their operational cost: [../architecture/references/deploy.md](../architecture/references/deploy.md).
- Worked examples of options and recommendations: [../architecture/references/examples/](../architecture/references/examples/).

## Done when

`architecture/options.md` has 2 or 3 options with diagram and table, a recommendation tied to the brief, and the user's choice recorded as `status: approved` with `choice` set. Next step: [architecture-system](../architecture-system/SKILL.md).
