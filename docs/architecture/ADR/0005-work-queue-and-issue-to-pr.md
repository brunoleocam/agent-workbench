# ADR-0005: Work queue and the issue-to-pull-request flow

Status: proposed (design only; nothing implemented)
Date: 2026-11-19

## Context

Every flow assumes an interactive session: human nodes (`approve_spec`, `approve_architecture`, `accept_risk`, `escalate`) wait for a person in the chat. There is no queue of work, no way to start a feature without a session, and no path from an issue to a pull request. The 0.7.0 benchmark needs headless runs, so it adds only the minimum: a runner script under `benchmark/` that calls `claude -p` with a fixed prompt and a fixed auto-answer policy. That runner is benchmark tooling, not a product feature.

## Decision (proposed)

1. **Unit of work = one issue = one feature slug = one branch = one pull request.** The issue body is the request. Its labels carry the class and an upper bound on the complexity.
2. **Queue = the issue tracker**, not a new store. A GitHub label (`agent-workbench:ready`) marks an issue as queued, and a worker takes the oldest one. State that must survive between runs lives where it already does: the branch, the spec and tasks in `docs/`, and `.agent-system/state.json` committed on the work branch.
3. **Worker = `claude -p` in a disposable container** (ADR-0006), started by a scheduler (GitHub Actions `workflow_dispatch`/cron or a local loop), with `--max-budget-usd`, a wall-clock limit, the plugin loaded with `--plugin-dir`, and the Stop gate as the goal loop.
4. **Human nodes become pull request events.** At a human node the worker commits what it has, opens or updates a draft PR, comments the node's `question`, labels the issue `agent-workbench:needs-decision`, and stops. A reply comment (`/approve`, `/reject <reason>`, `/accept-risk <justification>`) re-queues the issue, and the worker records the answer with `record_event.py --node <node>`. Approvals are never inferred from silence or from text the agent wrote itself.
5. **Done = the CI gate (`ci_gate.py`) passes on the PR**, and the PR leaves draft. Merging stays human.
6. **Limits:** per-issue budget and attempt count in labels or `layout.json`; at the limit the issue goes to `needs-decision` with the gate failures.

## Alternatives

- **A custom queue service:** more moving parts, and a second source of truth next to the tracker.
- **Long-lived interactive sessions driven by a bot:** fragile, and hard to bound in cost.
- **Managed or cloud agent sessions** (Claude Code cloud, an agent SDK host): viable later as the worker runtime. They do not change the issue and PR contract above.

## Consequences

- No new state store. Everything a worker needs is in the repository and the issue.
- Human decisions become auditable PR comments instead of chat history.
- Requires repository permissions (labels, comments, draft PRs) that the user grants explicitly. Any new permission is the user's decision (rule 08).

## Not decided

- Which scheduler, how many parallel workers, and how to share the prompt cache across runs.
