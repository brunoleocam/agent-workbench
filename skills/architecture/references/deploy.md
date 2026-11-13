# Deploy targets

The infrastructure target has no default: the interview always asks, and recommends what the repository already shows. Compare targets by what you must operate yourself, not only by the monthly bill. A cheaper server that the team cannot patch, back up, and monitor is more expensive.

Cost ranges below are rough orders of magnitude for a small production app, with no live price lookup. Check the provider before deciding.

## VPS with Docker Compose and a reverse proxy

One or a few virtual servers (any provider) running the app, workers, and possibly the database in containers through Docker Compose. A reverse proxy (Caddy, Nginx, Traefik) terminates TLS and routes to the containers.

- You operate: the operating system and its updates, the firewall, Docker, TLS renewal (automatic with Caddy or Traefik), backups, monitoring, and the deploy script.
- Typical cost: low; a few to a few tens of dollars per month.
- Worth it when: the team is comfortable with Linux, the load fits a few machines, and cost matters. Common for steps 0 to 4 of `scaling-stages.md`.
- Watch: put the database on a managed service or set up and test backups yourself; never publish database ports; keep secrets out of `docker-compose.yml` (`env_file` outside the repository, or the provider's secret store).

## PaaS (Platform as a Service)

You push code or an image; the platform builds, runs, scales, and routes it. Many offer managed databases and caches beside the app.

- You operate: the app and its configuration. The platform handles servers, TLS, and most of the deploy.
- Typical cost: low to medium; more per unit of compute than a VPS, less time spent operating.
- Worth it when: the team is small, the app is a standard web service plus workers, and speed of delivery matters more than control.
- Watch: limits on long-running connections, background jobs, and disk; cold starts on free tiers; vendor-specific configuration.

## Managed containers

A cloud service that runs your container images with autoscaling and a load balancer, without managing a cluster (for example the container services of the major clouds).

- You operate: images, service definitions, networking, IAM, and the managed database. More cloud configuration than a PaaS.
- Typical cost: medium.
- Worth it when: you already use that cloud, need private networking and IAM integration, or need autoscaling beyond a PaaS.
- Watch: IAM and network configuration is where most mistakes happen; codify it.

## Kubernetes

A container orchestrator. Managed offerings run the control plane; you run the workloads, and often the add-ons (ingress, certificates, metrics, secrets).

- You operate: manifests or charts, ingress, autoscaling, resource requests and limits, probes, upgrades of the cluster and its add-ons, RBAC inside the cluster, and observability.
- Typical cost: medium to high, mostly in people's time.
- Worth it when: many services and teams need a shared platform, the organization already runs Kubernetes, or the workload needs its scheduling features. Rarely at the first stage of a contract.
- Watch: the brief must name the item that requires it (see the rule at the end of `scaling-stages.md`).

## Environments

- **Development**: local, with Compose or the platform's local tools; seeded fake data; no production secrets.
- **Staging**: same images and configuration shape as production, smaller; production data only if anonymized.
- **Production**: secrets from a secret store, backups on, alerts on.

Write down in section 6 what differs between them. The fewer differences, the fewer surprises.

## From commit to production

1. CI runs lint and tests on every change, plus the Workbench infrastructure lint when the project carries it (`.cursor/agent-system/scripts/lint_infra.py` after the init).
2. CI builds one image per commit, tagged with the commit hash, and pushes it to a registry. The same image goes to staging and production.
3. Deploy to staging, run smoke tests.
4. Deploy to production: rolling update or blue-green, with health checks gating traffic.
5. Watch error rate and latency for a few minutes after each deploy.

## Rollback

- Keep the previous image and be able to redeploy it in one command.
- A rollback is only safe if the database schema still works with the previous version: see migrations below.

## Database migrations during deploy

- Run migrations as a separate step before the new version takes traffic, not at every app start in every instance.
- Use expand and contract: add new columns or tables first (compatible with the old code), deploy the new code, then remove the old columns in a later release.
- Never rename or drop a column in the same release that stops using it.
- Long migrations on large tables need an online approach (batches, background index creation).
