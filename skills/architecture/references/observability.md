# Observability

You cannot justify a scaling stage, find a bug in production, or know the system is down before users tell you without it. Observability comes before scaling (step 2 in `scaling-stages.md`).

## Structured logs

- One event per line, in JSON, written to standard output. The platform or a log agent collects it; the app does not manage log files.
- Every line carries: timestamp (UTC, ISO 8601), level, service name, version or commit, environment, message, and a **correlation id**.
- The correlation id is created at the edge (or taken from an incoming `traceparent` or `X-Request-Id` header), passed to every downstream call and message, and logged by every component. With it, one request can be followed across the API, the queue, and the worker.
- Log events, not chatter: a request finished (with status and duration), a job failed (with the error and attempt), a decision made.
- Never log secrets, tokens, passwords, full card numbers, or more personal data than needed. Redact at the logger, not by hoping callers remember (see rule `08-security-engineering`).
- Rotate or cap container logs (`logging` options in Compose) so a chatty service does not fill the disk.

## Metrics

**RED** for each service that receives requests:

- **Rate**: requests per second.
- **Errors**: failed requests per second, or the error ratio.
- **Duration**: latency distribution; track p50, p95, and p99, not the average.

**USE** for each resource (CPU, memory, disk, connections, queue):

- **Utilization**: how busy it is (CPU 70%).
- **Saturation**: how much work is waiting (run queue, queue depth, connection pool waits).
- **Errors**: resource errors (disk full, connection refused).

Add a few business metrics that show the system does its job: orders per minute, uploads processed, messages in the dead letter queue.

## Distributed tracing

A trace follows one request through every component as a tree of timed spans. Use **OpenTelemetry** for instrumentation so the backend (any vendor or self-hosted) can change without touching code.

- Needed when: there is more than one service or a queue in the request path and logs with correlation ids are not enough to find where time goes.
- With a single app, logs with a correlation id and RED metrics are usually enough.

## SLOs and error budgets

- An **SLI** is a measurement of what users feel: the share of requests that succeed in under 500 ms.
- An **SLO** is the target for it over a window: 99.5% over 30 days.
- The **error budget** is what remains: 0.5% of requests may fail or be slow. While budget remains, ship; when it is spent, prioritize reliability.
- Set SLOs when the brief has an availability or latency target. Do not promise 99.99% on a single server.

## Alerts

- Alert on **symptoms** users feel (error rate up, latency up, SLO burning fast, queue backing up), not on every cause (one CPU spike). Causes go to dashboards.
- Every alert has a threshold, a duration ("error ratio > 2% for 5 min"), who is notified, and a short note on what to check first.
- An alert nobody acts on is noise; remove or fix it.

## The minimum for the first stage

1. Structured JSON logs to stdout with a correlation id, collected somewhere searchable.
2. RED metrics for the app and USE metrics for the server and the database.
3. An external uptime check on the main endpoint.
4. Two alerts: error ratio and p95 latency above target for 5 minutes.
5. Backup success monitored, and a restore tested.
