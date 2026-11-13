# Scaling stages

Start with the smallest design that serves today's peak load and the quality attributes in the brief. Each step below adds capacity and also adds something to operate. Take a step when a measured signal says so, not when the system "might grow".

The entries below are **steps** of a generic progression, numbered 0 to 7. They are not the `Estágio N` of a contract: a contract numbers its own stages from 0 and may skip or reorder these steps.

The order is typical, not mandatory. A read-heavy system may need a cache before it needs a separate database; a system with heavy background work may need a queue right after the first step. Skip what the brief does not need.

## Step 0. One instance, app and database together

One server (or one PaaS app) runs the application and the database.

- Fits: early products, internal tools, and many established ones. A typical CRUD app on one well-sized server serves the low hundreds of requests per second when queries are indexed, and more when reads hit an in-process cache.
- Ready before: nothing beyond the basics in step 2.
- Operational cost: the lowest. One machine to patch.
- Leave when: the app and the database compete for memory or CPU. Example trigger: "Gatilho: memória da máquina > 85% por 3 dias (fonte: métricas do servidor)".

## Step 1. Separate database

The database moves to its own server or to a managed database.

- Signal: resource contention between app and database, or the need for managed backups and point-in-time recovery.
- Example trigger: "Gatilho: CPU do banco > 60% enquanto a app também passa de 60% por 7 dias (fonte: métricas do servidor)".
- Ready before: connection string from configuration, not hard-coded; network access to the database limited to the app.
- Operational cost: a network hop (about 1 ms in the same region) and one more thing to pay for.

## Step 2. Backups and monitoring, before anything else

Not a scaling step, but it comes before every step after it. You cannot justify a stage without measurements, and you cannot survive a failed migration without a restore.

- Automated backups with a tested restore. Write down RPO and RTO.
- Structured logs, the RED metrics of the app, and the USE metrics of the server and the database (see `observability.md`).
- Alerts on error rate and latency.

## Step 3. Cache

A cache in front of expensive or repeated reads.

- Signal: the same reads dominate the load, or a read path is slow even with the right indexes.
- Example trigger: "Gatilho: p95 de leitura > 300 ms por 7 dias com índices revisados (fonte: APM)".
- Ready before: a clear invalidation rule for each cached item (see `caching.md`). Start in process; move to a distributed cache when there is more than one app instance.
- Operational cost: stale data, invalidation bugs, and one more service if distributed.

## Step 4. Several app instances behind a load balancer

Two or more copies of the app, with a load balancer spreading the requests.

- Signal: one instance cannot handle the peak, or the availability target cannot accept a single instance going down during a deploy.
- Example trigger: "Gatilho: CPU da app > 70% no pico por 5 dias (fonte: métricas do servidor)" or "Gatilho: disponibilidade mensal < 99,5% (fonte: monitor externo)".
- Ready before: the app is stateless. Sessions live in the database or a distributed cache, not in process memory; uploads go to object storage, not the local disk; scheduled jobs run on one instance only. Migrations stay compatible with two app versions running at once.
- Operational cost: a load balancer, health checks, and rolling deploys.

## Step 5. Read replicas

The primary database takes writes; one or more replicas serve reads.

- Signal: the database is the bottleneck, and most of its load is reads.
- Example trigger: "Gatilho: CPU do banco primário > 70% por 7 dias com 80% das consultas sendo leitura (fonte: métricas do banco)".
- Ready before: you know which reads must see a write immediately ("read your own writes"); those stay on the primary. Replica lag is monitored.
- Operational cost: replica lag, routing reads, and failover.

## Step 6. Asynchronous work in a queue

Slow or bursty work leaves the request path and goes to workers through a queue.

- Signal: requests wait on slow work (email, image or video processing, reports, calls to slow third parties), or bursts exceed what the app can do in real time.
- Example trigger: "Gatilho: p95 do endpoint de upload > 2 s por causa do processamento (fonte: APM)".
- Ready before: idempotent consumers, a retry policy with backoff, a dead letter queue, and a way to publish that does not lose messages when the database commits (outbox, see `messaging.md`).
- Operational cost: a broker, workers to deploy and monitor, and eventual consistency the user can see.

## Step 7. Partitioning and sharding

Data is split across several databases by a key.

- Signal: one primary cannot take the write volume or hold the data, after indexes, caching, replicas, archiving old data, and a bigger machine.
- Example trigger: "Gatilho: escrita no primário > 5000 req/s no pico ou dados > 2 TB (fonte: métricas do banco)".
- Ready before: a shard key that spreads load evenly and keeps most queries on one shard; a plan for rebalancing; cross-shard queries identified and reduced.
- Operational cost: the highest on this list. Cross-shard transactions, reporting, and rebalancing become your problem. Consider partitioning inside one database, or a managed distributed database, first.

## The rule for components today's load does not need

When a recommendation includes a component that the current load does not require (a container orchestrator, a queue, a distributed cache, a database per service, a service mesh, microservices), it must cite the item of the brief that requires it: a latency target, an availability target, a legal obligation, a burst pattern. If no item requires it, it goes in a later stage of section 9 with a trigger, not in the contract's first stage (stage 0).
