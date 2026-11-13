# Permissions and access

Section 8 of `ARCHITECTURE.md` states who can do what, where that is enforced, and how secrets reach the system. This file covers the architecture choices. For implementation details and review, follow rule `08-security-engineering` and the `security-best-practices` and `security-review` skills; a change that touches authentication, authorization, tenant isolation, or secrets also goes to the `security-reviewer`.

## Authentication and authorization

- **Authentication** answers "who is this?": a user with a session or token, a service with a credential, a webhook with a signature.
- **Authorization** answers "may this actor do this to this resource?". It is checked on the server, on every request, close to the data. Hiding a button is not authorization.
- List the actors in section 8: end users, administrators, support staff, other services, external systems calling webhooks.

## Authorization models

- **RBAC** (role-based): permissions attach to roles (admin, editor, viewer) and users get roles. Simple to reason about and audit. Fits most products. Grows badly when roles multiply to express exceptions.
- **ABAC** (attribute-based): rules over attributes of the user, the resource, and the context ("editors may change documents of their own department during business hours"). Expressive; harder to audit and test. Use when RBAC would need dozens of roles.
- **Per resource** (ownership and sharing): permissions attach to each record ("owner", "shared with"), as in documents and folders. Combine with RBAC for administrative roles.
- Enforce the model in one place (a policy module or middleware) rather than scattered `if` statements, so it can be tested and reviewed.

## Multi-tenant isolation

When one system serves several customers (tenants), a bug in isolation leaks one customer's data to another. Choose the model by isolation need and tenant count:

- **Database per tenant**: strongest isolation, per-tenant backup and restore, easy to delete a tenant. Costly and slow to migrate with many tenants. Fits few large tenants or strict contractual isolation.
- **Schema per tenant**: one database, one schema each. Middle ground; migrations still run per tenant, and connection handling gets complex beyond a few hundred tenants.
- **Shared tables with a `tenant_id` column**: cheapest and simplest to operate at scale. The risk is one query that forgets the filter. Mitigate with a mandatory filter in the data access layer, database row-level security where available, tests that try to cross tenants, and a tenant id in every cache key.

Record the choice in an ADR. Whatever the model, the tenant comes from the authenticated session, never from a request parameter the client controls.

## Least privilege

For services:

- One database user per service, with only the grants it needs. The application never connects as a superuser or the database owner; migrations run with a separate, more privileged user.
- Cloud credentials scoped to the resources the service uses (one bucket, one queue), not account-wide keys.
- Containers run as a non-root user, without privileged mode, and without the Docker socket mounted (`lint_infra.py` checks these).
- Internal services and databases are not reachable from the internet. Only the load balancer or reverse proxy is.

For people:

- Production access only for those who need it, through individual accounts, with multi-factor authentication.
- Administrative actions in the product are logged with who, what, and when.
- Remove access when people change roles or leave.

## Secrets

- Never in the repository: not in code, not in `docker-compose.yml`, not in Kubernetes manifests, not in `.env` files that are committed. `.env.example` lists the names with empty values.
- Injected at runtime as environment variables or mounted files, from the platform's secret store or a secret manager.
- Different secrets per environment. Staging never holds production secrets.
- Rotatable: the system keeps working while a secret is replaced, and there is a written procedure to do it.
- If a secret was ever committed, rotate it; deleting the commit is not enough.

## What to write in ARCHITECTURE.md

In section 8: the actors and how each authenticates; the authorization model and where it is enforced; tenant isolation if any, with its ADR; where secrets live and how they reach each process; the hosts and ports exposed to the internet; the service accounts and their grants.
