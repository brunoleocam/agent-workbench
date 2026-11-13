---
name: architecture-discovery
description: Short architecture interview that turns "I want it to scale" into an approved architecture/brief.md with load, access pattern, consistency, latency, sensitive data, team, budget, infrastructure target, and a capacity estimate with the arithmetic shown. Use at the start of a new system or before a structural change with no approved brief (entrevista de arquitetura, requisitos não funcionais, como escalar, qual banco usar, começar a arquitetura, system design).
---

# Architecture discovery

First step of `architecture`. Produces `architecture/brief.md`, the input for [architecture-options](../architecture-options/SKILL.md).

## 0. Check whether the step is done

If `architecture/brief.md` exists with `status: approved`, stop and say this step is done; the next one is `architecture-options`. If it exists as `status: draft`, continue from it instead of starting over. To revise an approved brief (the load, the team, or the target changed), the skill sets `status: draft` again, asks only about what changed, and asks for approval again; `architecture-options` must then run again too.

The person answering may have no architecture background. Never ask an abstract question ("What consistency model do you need?", "What is your RPO?"). Ask about their product, their users, and what hurts if something goes wrong; the technical decisions come later, as options with trade-offs.

## 1. Read before asking

Read, in this order, before writing any question:

- The request and the README.
- The code: language, framework, ORM or database driver configuration, background job libraries, HTTP clients to third parties.
- Infrastructure files: `docker-compose*.yml`, `compose*.yaml`, `Dockerfile`, Kubernetes manifests, `fly.toml`, `render.yaml`, `vercel.json`, `Procfile`, Terraform files and their providers, CI workflows that deploy.
- `.env.example` (names only; never read or copy a real `.env`).
- An earlier brief, `ARCHITECTURE.md`, and the ADRs in the ADR folder (`adr_dir`, default `docs/architecture/ADR/`).

Every answer you get from them is recorded as `observado: <file>` (seen in a file) or `inferido` (deduced) and is not asked, except the infrastructure target (step 2).

In an existing system, describe the current architecture before proposing anything: components, databases, caches, queues, deploy method, each with the file it came from. It goes in the `## Arquitetura atual` section of the brief.

## 2. Ask once, with recommendations

Ask in a single message, **at most 6 questions**, only about what is still missing and would change the architecture. Typical gaps, in priority order; question 6 is always asked, and any of 1 to 5 that the context already answers is skipped:

1. How many people use it today and in 12 months, and when the peaks happen (a campaign, a match, the opening of sales, business hours).
2. What users mostly do: look things up, or create and change things (the read/write ratio), and how big the data is (text records, images, video).
3. What must never be wrong or lost (money, stock, seats, medical data), whether it holds personal, health, or payment data or has legal obligations (LGPD), and what can be a few seconds or minutes out of date.
4. How fast it must answer, and what happens to the business if it is down for an hour.
5. Who will operate it (team size, comfort with servers) and the monthly budget for infrastructure.
6. **The infrastructure target. Always asked**, even when the repository shows one. Options include VPS, PaaS, managed cloud containers, Kubernetes, and "ainda não sei". When a file shows a target (`fly.toml`, a Terraform provider, Kubernetes manifests, a production `docker-compose.yml`), that target is the recommended answer and the question cites the file.

Sensitive data and legal obligations are part of question 3, never a seventh question.

Rules for each question:

- Give a **recommended answer** already filled in, inferred from the context. The user can accept it with one word.
- Offer **at most 6 options**, in plain words. Always allow a free answer.
- Explain any unavoidable term in one line. Examples: "consistência eventual: depois de uma mudança, algumas telas podem mostrar o valor antigo por alguns segundos"; "RPO: quanto dado, em tempo, você aceita perder num desastre".
- In Claude Code, use the closed-choice question tool when available, recommended option first. Elsewhere, a numbered list with the recommendation marked.

## 3. Estimate capacity, with the arithmetic shown

From the numbers in the brief, compute and show each step:

- Average and peak requests per second (users × actions per user ÷ seconds in the period, × peak factor).
- Storage per year (records × size, files × size).
- Outbound bandwidth per month, always: responses × average response size, plus files or media served. Small for an API, decisive for media.

Each number says which premises it came from. A number that depends on an `inferido` premise is marked as an estimate. The worked case studies in [../architecture/references/examples/](../architecture/references/examples/) show the format.

## 4. Write and approve the brief

1. Write `architecture/brief.md` from [references/brief-template.md](references/brief-template.md) with `status: draft`. Every item carries its origin: `fornecido`, `observado: <file>`, or `inferido`. A section that does not apply says why.
2. Show the brief in a short summary, highlighting the inferred items and the capacity estimate, and ask for approval or corrections.
3. Only after the user's explicit approval, change it to `status: approved`.

## References

- How load usually grows and which signal justifies each step: [../architecture/references/scaling-stages.md](../architecture/references/scaling-stages.md).
- Choosing data stores, for questions about data size and access: [../architecture/references/data-stores.md](../architecture/references/data-stores.md).

## Done when

`architecture/brief.md` exists with `status: approved`, every section filled or marked as not applicable, and the capacity estimate shows its arithmetic. Next step: [architecture-options](../architecture-options/SKILL.md).

Do not propose options, write `ARCHITECTURE.md`, or change code or infrastructure in this step.
