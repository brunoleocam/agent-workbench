# ADR-0006: Isolation for untrusted code

Status: proposed (design only; the benchmark uses the minimum described under "Now")
Date: 2026-11-19

## Context

The guardrails (the `check_proofs.py` policy, the infra lint, the hooks) are not a security boundary. A test file runs whatever it contains with the user's permissions, and so does code the agent writes and then runs. That is acceptable on the user's own project, on their own machine, under their review. It is not acceptable for a customer's repository, a pull request from an unknown author, or unattended runs (ADR-0005).

## Decision (proposed)

1. **Trust levels per run:** `own` (the user's project, interactive, today's behavior), `review` (someone else's code, a person watching), and `untrusted` (unattended, or code from outside the organization). `untrusted` is the default for the worker of ADR-0005.
2. **`untrusted` runs only inside a disposable container**:
   - a rootless runtime (Docker rootless or Podman) with a non-root user;
   - the repository copied in, never bind-mounted read-write from the host;
   - no host credentials, SSH agent, or cloud metadata, and only short-lived, scoped tokens passed in;
   - network egress limited to an allowlist (the model API, the package mirror), or none for test execution;
   - CPU, memory, process, and wall-clock limits; destroyed after the run, with only the diff, logs, and proofs exported.
3. **The agent's own tools run inside the same container** (Claude Code headless in the container), so "the agent ran a command" never means "on the host".
4. **Secrets:** none by default. A test that needs a secret uses a fake or a local service; a real credential is a separate, explicitly approved job.
5. The plugin documents this and ships a reference `Dockerfile` and run script. It does not try to be the sandbox.

## Now (0.7.0 benchmark)

Each benchmark run gets a fresh directory and, where Docker is available, a fresh container from one pinned image. The hidden acceptance tests run from outside the agent's workspace and are never copied into it.

## Alternatives

- **gVisor or Firecracker microVMs:** stronger isolation. Worth it for multi-tenant hosting, too heavy as a default for a plugin.
- **OS sandboxing of the agent's tools only** (the Claude Code sandbox, seccomp profiles): useful as a second layer. It does not cover the tests the agent runs through other tools.
- **Trusting the policy lists:** rejected. They are accident protection by design (ADR-0002, ADR-0004).

## Consequences

- Unattended and customer-code work requires a container runtime on the worker.
- Interactive work on the user's own project stays as it is today.
