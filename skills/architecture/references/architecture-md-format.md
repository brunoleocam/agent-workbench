# ARCHITECTURE.md format

`ARCHITECTURE.md` sits at the project root. It is the architecture contract: the planner reads it before specifying, the implementer reads it before building, and the architecture reviewer compares code and infrastructure against it. A database, cache, queue, external service, or deploy unit that the contract does not name is not added by a task; it goes through `change-request` first.

Front matter:

```markdown
---
status: draft        # draft | approved; only the user approves
option: B            # the chosen option (the `choice` in architecture/options.md)
stage: 0             # the current stage in section 9
---
```

The ten sections below are fixed: these headings, in this order, with nothing renamed. Write their content in the user's language. A section that does not apply to the project stays in the file and says why in one sentence ("No cache: every read is a single indexed query under 20 ms at peak load"). An omitted section reads as a forgotten decision.

## 1. Contexto e atributos de qualidade

- What the system does and for whom, in two or three sentences.
- The quality attributes from `architecture/brief.md`, each with a number: users and load today and in 12 months, peak factor, read/write ratio, latency target (p95), availability target, data sensitivity.
- The capacity estimate, copied or linked from the brief, with the arithmetic shown.
- What is explicitly out of scope for this architecture.

## 2. Componentes e fronteiras

- A Mermaid diagram of the deploy units, data stores, and external services, with the direction of each call.
- One line per component: responsibility, technology, and who owns it.
- The dependency rule between modules, stated so a reviewer can check it. Example: "modules talk to each other only through the public service in `src/<module>/index.ts`; no module reads another module's tables".

## 3. Dados

- The database chosen and why, citing the ADR (`ADR-0004`).
- The main entities and which component owns each one. Only the owner writes.
- Consistency: where the system needs strong consistency (money, stock, seats) and where stale data is acceptable, with how stale.
- Migrations: tool, and the rule that every migration stays compatible with the previous app version while both run.
- Backup: frequency, retention, where it is stored, RPO (how much data you can lose) and RTO (how long you can be down), and when the restore was last tested.

## 4. Cache

- What is cached, where (in-process, distributed, CDN, HTTP headers), with which TTL, and how it is invalidated.
- Or the decision not to have a cache, with the reason.
- What is never cached (see `caching.md`).

## 5. Comunicação

- Which calls are synchronous (HTTP, gRPC) and which are asynchronous (queue, events), and why.
- For every asynchronous flow: the delivery guarantee (at least once, at most once), how idempotency is achieved, the retry policy, and where failed messages go.
- How a write to the database and a message publish stay consistent (outbox, or why it does not matter here).
- Timeouts on every outbound call.

## 6. Deploy e infraestrutura

- The infrastructure target (VPS, PaaS, managed containers, Kubernetes) and why, citing the ADR.
- Environments (dev, staging, production) and what differs between them.
- The path from commit to production: CI checks, build, image registry, deploy, migration step, rollback.
- Containers: base images pinned, non-root user, health checks, resource limits. `lint_infra.py` checks these.

## 7. Observabilidade

- Log format: structured (JSON), one event per line, with a correlation id that crosses every component, and the fields every log line carries.
- Main metrics: RED for each service, USE for each resource (see `observability.md`).
- Tracing, or why it is not needed yet.
- Alerts, each with a threshold, a duration, and who is notified. Alert on symptoms the user feels.
- SLOs, when the availability target justifies them.

## 8. Segurança e permissões

- Authentication: who the actors are and how each one proves who it is.
- Authorization model (RBAC, ABAC, per resource, per tenant) and where it is enforced.
- Tenant isolation, when the system is multi-tenant.
- Where secrets live and how they reach the process. Never in the repository.
- What is exposed to the internet: hosts, ports, and services. Everything else is private.
- Least privilege for services (a database user per service, no superuser in the app).
- A pointer to rule `08-security-engineering` and to the `security-review` skill for changes that touch these items.

## 9. Estágios de escala

The current stage is marked `(atual)` in its title, and only there. At first it is stage 0. At least two later stages follow. Each later stage uses this format. Like the ten headings, the labels are literal in every project, whatever the contract's language: `### Estágio N: <name>`, `(atual)`, `- Gatilho:`, `- Mudança:`, `- Custo:`, `- Pré-requisito:`. The validators read them as written. The text after each label is in the user's language.

```markdown
### Estágio 1: réplica de leitura
- Gatilho: p95 de leitura > 300 ms por 7 dias (fonte: APM)
- Mudança: uma réplica de leitura; relatórios e listagens leem dela
- Custo: +1 instância de banco; atraso de réplica de até 1 s nas listagens
- Pré-requisito: leituras que precisam do dado recém-escrito continuam no primário
```

A trigger is measurable when it compares a metric with a threshold: an operator (`>`, `<`, `>=`, `<=`, `acima de`, `abaixo de`, `mais de`, `menos de`), a number, and a unit (`%`, `ms`, `s`, `min`, `minutos`, `h`, `horas`, `req/s`, `req/min`, `rps`, `GB`, `TB`, `MB`, `usuários`, `conexões`, or a business rate such as `reservas/s` or `pedidos/min`). Numbers may use thousands separators (`1.000.000`) and decimals (`99,5`). It also names where the number is measured, as `(fonte: ...)`. A duration ("por 7 dias") says how long the threshold must hold; it is not the threshold.

- Accepted: "Gatilho: CPU do banco > 70% por 3 dias no horário de pico (fonte: métricas do provedor)".
- Refused: "Gatilho: quando crescer por 7 dias". Rewrite it with a metric and a value, or ask the user which value to use. Never record a vague trigger.

When a trigger is reached and the team moves to the next stage, propose the changes and get the user's confirmation, then move `(atual)`, update the sections the change touches, and record the move in a new ADR.

## 10. Anti-padrões

What this project must not do, specific to its architecture. Examples: "no module reads another module's tables", "no synchronous call between the API and the video processor", "no secret in `docker-compose.yml`", "no component added without an ADR". Include the P0 rules of `lint_infra.py` that apply.

## Citing ADRs

Every choice between real alternatives in sections 3 to 8 has an ADR in the project's ADR folder (`adr_dir` in `.cursor/agent-system/layout.json`; `docs/architecture/ADR/` by default), numbered with the next free number, in the same format as the existing ADRs: `# ADR-NNNN: <title>`, `Status:`, `Date:`, `## Context`, `## Decision`, `## Alternatives`, `## Consequences`. The section cites it as `ADR-0004`. An accepted ADR is never edited; a changed decision gets a new ADR that supersedes it (`Status: superseded by ADR-0007` on the old one). A cited ADR that does not exist fails `validate_architecture.py`.
