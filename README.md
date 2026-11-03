<div align="right">
  <a href="README.pt-BR.md">
    <img src="https://img.shields.io/badge/README-PT--BR-blue?style=flat-square" alt="Português 🇧🇷" />
  </a>
</div>

# Agent Workbench

**A pragmatic AI engineering harness for Cursor.**

Agent Workbench transforms AI coding agents into a more structured, traceable, and verifiable software engineering workflow.

Instead of optimizing for code generation speed, it focuses on what actually matters: understanding requirements, making deliberate decisions, implementing the right solution, validating behavior, and producing evidence that the software works.

## Why Agent Workbench?

AI coding agents can generate code quickly, but speed alone does not guarantee good software.

Common problems include:
- Implementing ambiguous requirements.
- Making architectural decisions without documenting trade-offs.
- Writing tests that do not meaningfully verify behavior.
- Repeating reviews and unnecessary refinements.
- Losing project context between sessions.
- Treating successful code generation as proof of completion.

Agent Workbench addresses these problems through a lightweight engineering workflow built around traceability, verification, and risk-aware decisions.

## Engineering philosophy

The guiding principle is **Minimum Effective Engineering (MEE)**:

Use the minimum process, complexity, agents, and tokens necessary to deliver software with an appropriate level of quality and safety.

This means:
- Process should scale with complexity and risk.
- Security risk is evaluated independently from implementation complexity.
- Requirements and acceptance criteria should be clear before implementation.
- Tests must provide meaningful evidence.
- Reviews should focus on material issues, not endless refinement.
- Work stops when acceptance criteria are met and relevant risks are controlled.

The goal is not more process. It is less rework and more reliable outcomes.

## How it works

```text
       User Intent
            |
            v
   Requirements & Specification
            |
            v
    Architecture Decisions
            |
            v
       Task Planning
            |
            v
       Implementation
            |
            v
     Tests & Evidence
            |
            v
     Code & Security Review
            |
            v
       Verification Gate
            |
            v
       Project State
```

The workflow adapts to the task's complexity and security risk. Small changes do not require the full process.

For medium and larger tasks, deterministic validators verify specifications, tasks, test results, and completion evidence. Agent reviews provide the complementary semantic evaluation.

## What's included?

| Component | Purpose |
|---|---|
| Rules | Persistent engineering principles, security boundaries, and token economy |
| Skills | Reusable workflows for features, planning, implementation, debugging, reviews, and more |
| Agents | Specialized roles for planning, implementation, testing, reviewing, and debugging |
| Hooks | Session context, project state, and development timeline |
| Scripts | Deterministic validation, test execution, evidence collection, and evaluation |
| References | On-demand secure coding guidance for supported technology stacks |

### Verification and evidence

The harness includes four main validation tools:

- `validate_spec.py` — validates specification structure and traceability.
- `validate_tasks.py` — validates tasks, dependencies, and verification definitions.
- `check_proofs.py` — executes tests and records actual exit codes, output, and workspace fingerprints.
- `validate_verification.py` — evaluates whether the required evidence, reviews, and task conditions are satisfied.

Proofs are tied to the workspace state, helping detect when code changes after tests have been executed.

### Security

Security is treated as an independent dimension of engineering risk.

The project includes:
- Secure engineering rules.
- Stack-specific secure coding references.
- A dedicated security review skill and agent.
- Secret redaction in relevant logs and outputs.
- Command execution guardrails.

**Important:** command guardrails are best-effort protections, not a sandbox or a security boundary against malicious code. Test files execute their contents and must be reviewed before execution.

## Quick Start

### Requirements

- Cursor
- Python 3
- Git

### Installation

Windows (PowerShell):

```powershell
git clone https://github.com/brunoleocam/agent-workbench "$env:USERPROFILE\.cursor\plugins\local\agent-workbench"
```

Linux:

```bash
git clone https://github.com/brunoleocam/agent-workbench ~/.cursor/plugins/local/agent-workbench
```

Reload the Cursor window using `Developer: Reload Window`.

Then open **Customize** and verify that the plugin's rules, skills, and subagents are available.

### Initialize a project

In the root directory of your project, run:

```text
/init-agent-system
```

This initializes project-specific state, timeline, and roadmap without replacing existing project documentation or unrelated hooks.

Cloud Agents do not load local plugins. Use `/init-agent-system` with `--for-cloud` when preparing a project for that environment.

### Typical workflows

Feature development:

```text
/brainstorm
/implementation-plan
/implementation
/code-review
```

Bug investigation:

```text
/investigacao-enxuta
/bug-fix
```

Use `/help` inside Cursor for the available commands and workflows.

## Human approval and automation

Agent Workbench automates repetitive engineering work, but does not delegate every decision to an agent.

Human approval remains important for:
- Specification and architectural decisions.
- Business behavior changes.
- Security-sensitive changes and permissions.
- New infrastructure and destructive operations.
- Acceptance of residual risks.
- Committing and pushing changes when explicitly authorized.

Agents can propose decisions and changes, but important decisions remain under human control.

## Documentation

| Document | Description |
|---|---|
| [Agent System](agent-system/README.md) | Architecture, workflows, agents, and validation |
| [Artifact Format](agent-system/docs/artifacts.md) | Specification, task, and evidence formats |
| [CLI Reference](agent-system/docs/cli.md) | Script commands and options |
| [Agent Contracts](agent-system/docs/contracts.md) | Agent responsibilities and handoffs |
| [Architecture Decisions](docs/architecture/ADR/) | Architectural decisions and trade-offs |
| [Security Documentation](docs/security/) | Security reviews and accepted limitations |
| [Project Progress](docs/progress/) | Current implementation state and roadmap |

## Tests and evaluations

Run the automated test suite:

```bash
python agent-system/scripts/test_system.py
```

Run deterministic evaluations:

```bash
python agent-system/scripts/run_evals.py
```

The evaluations verify harness behavior using controlled project fixtures. They do not automatically evaluate the quality of the underlying AI model's decisions or generated code.

The current implementation has been tested on Windows and Linux (WSL2). macOS has not yet been tested. CI is not currently configured.

## License

MIT.

Security reference materials are original project documentation based on official sources, including OWASP and framework documentation. See individual references for their sources.
