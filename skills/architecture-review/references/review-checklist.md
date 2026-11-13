# Architecture review checklist

Answer every item for the files in scope. Every "yes" becomes a finding with severity, evidence (file and line, or the snippet), and the section of `ARCHITECTURE.md` or the ADR it contradicts. Write the report in the user's language.

## Components and boundaries

1. Does the code or the infrastructure have a component, database, cache, queue, broker, external service, or deploy unit that the contract does not name? (sections 2 to 6)
2. Does any module depend on another in a way that breaks the dependency rule of section 2 (for example, it reads another module's tables, or imports another module's internal code)?
3. Is any entity written by a component that is not its owner in section 3?

## Data

4. Is there a migration that breaks the previous app version while both run (renaming or dropping a column still in use)?
5. Do the backup, RPO, or RTO described in section 3 have no counterpart in the configuration?

## Cache

6. Is there a cache key with per-user or per-tenant data that does not include the user or tenant id?
7. Is permission data or a secret cached beyond what section 4 allows, or is there a key without a TTL?

## Communication

8. Is there an asynchronous flow (queue, event, webhook, job) without idempotency declared and implemented (idempotency key, processed table, or a naturally idempotent operation)?
9. Is there a database write followed by a queue publish with neither an outbox nor a reason in section 5 (dual write)?
10. Is there an outbound call without a timeout, or a retry without backoff or without a maximum number of attempts?

## Deploy and infrastructure

11. Does any infrastructure file have an open P0? When `lint_infra.py` is not available, check these by reading the files:
    - `P0-UNPINNED-IMAGE`: `FROM` or `image:` without a tag, or with `latest` (a `@sha256:` digest counts as pinned; a `FROM` naming an earlier build stage does not count).
    - `P0-ROOT-USER`: the last Dockerfile stage has no `USER`, or `USER root` / `USER 0`; Kubernetes `runAsUser: 0` or `runAsNonRoot: false`.
    - `P0-PRIVILEGED`: `privileged: true` in Compose or Kubernetes, or `allowPrivilegeEscalation: true`.
    - `P0-SECRET-LITERAL`: a literal value for a key whose name contains `PASSWORD`, `PASSWD`, `SECRET`, `TOKEN`, `API_KEY`, `APIKEY`, `PRIVATE_KEY`, or `ACCESS_KEY`, in a Dockerfile `ENV` or `ARG`, a Compose `environment`, or a Kubernetes `env[].value`. Interpolation (`${VAR}`, `$VAR`), an empty value, `valueFrom`, `secretKeyRef`, and `env_file` do not count. Report the key, never the value.
    - `P0-DB-PORT-PUBLIC`: a database, cache, or broker port (5432, 3306, 1433, 27017, 6379, 11211, 9200, 5672, 9092) published on all interfaces in Compose, or exposed by a Kubernetes `LoadBalancer` or `NodePort` service.
    - `P0-DOCKER-SOCKET`: `/var/run/docker.sock` mounted.
12. Do the target, the environments, or the path to production differ from what section 6 describes?

## Observability

13. Is there unstructured logging (free text instead of JSON) where section 7 requires structured logs?
14. Does a flow cross components without passing the correlation id along?
15. Does any log line carry a secret, token, password, or more personal data than needed?
16. Is a metric or alert listed in section 7 missing?

## Security and permissions

17. Is there a secret in the repository, in `docker-compose.yml`, in a manifest, or in a committed `.env`?
18. Is a port or service exposed to the outside that section 8 does not declare?
19. Does the app connect to the database as a superuser, or with more privileges than section 8 describes?
20. Is an authorization check missing on the server, or is the tenant taken from a parameter the client controls?

## Scaling stages

21. Has a trigger of section 9 already been reached by the available metrics without the stage move being recorded?
22. Was a component of a later stage added before its trigger, without an ADR?
