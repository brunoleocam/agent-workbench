<div align="right">
  <img src="https://img.shields.io/badge/version-0.4.0-green?style=flat-square" alt="Version 0.4.0" />
  <a href="README.pt-BR.md">
    <img src="https://img.shields.io/badge/README-PT--BR-blue?style=flat-square" alt="Português 🇧🇷" />
  </a>
</div>

# Agent Workbench

**A pragmatic AI engineering harness for Cursor and Claude Code.**

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

- Cursor or Claude Code
- Python 3, available as `python` on the PATH (the hooks call `python`)
- Git

### Installation

#### Cursor

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

#### Claude Code

The repository is also a Claude Code marketplace. In your terminal:

```bash
claude plugin marketplace add brunoleocam/agent-workbench
claude plugin install agent-workbench@agent-workbench
```

Inside a Claude Code session, the same steps are:

```text
/plugin marketplace add brunoleocam/agent-workbench
/plugin install agent-workbench@agent-workbench
```

Start a new session (or run `/reload-plugins`). Check what loaded with:

```bash
claude plugin details agent-workbench
```

In Claude Code, every command has the plugin prefix: `/agent-workbench:feature` instead of `/feature`, and the subagents appear as `agent-workbench:planner`, `agent-workbench:implementer`, and so on.

To work on the plugin itself, load your clone for one session without installing it:

```bash
claude --plugin-dir /path/to/agent-workbench
```

### Initialize a project

In the root directory of your project, run:

```text
/init-agent-system
```

In Claude Code, run `/agent-workbench:init-agent-system`.

This initializes project-specific state, timeline, and roadmap without replacing existing project documentation or unrelated hooks.

In Claude Code, plugins have no always-on rules, so the init also writes a condensed version of rules `00` to `08` into the project `CLAUDE.md`, inside a managed block between the `<!-- agent-workbench:begin -->` and `<!-- agent-workbench:end -->` markers. It creates `CLAUDE.md` when missing and appends the block when the file exists. Text outside the markers is never changed. Commit `CLAUDE.md` with the project so the rules are versioned with it.

Cloud Agents do not load local plugins. Use `/init-agent-system` with `--for-cloud` when preparing a project for that environment.

### Updating

#### Cursor

Check the installed version in `.cursor-plugin/plugin.json` (`version` field) and compare it with the badge at the top of this page on GitHub.

1. Pull the new version into the plugin folder.

   Windows (PowerShell):

   ```powershell
   git -C "$env:USERPROFILE\.cursor\plugins\local\agent-workbench" pull --ff-only
   ```

   Linux:

   ```bash
   git -C ~/.cursor/plugins/local/agent-workbench pull --ff-only
   ```

   If the pull refuses because of local changes, run `git status` in the plugin folder and stash or discard them before pulling again.

2. Reload the Cursor window using `Developer: Reload Window`. Rules, skills, subagents, and hooks are loaded from the plugin, so they are updated right away.

3. In each project you initialized, run `/init-agent-system` again. It refreshes the managed scripts in `.cursor/agent-system/scripts/` and adds new state keys, while keeping the existing state, timeline, roadmap, documentation, and hooks.

For projects prepared with `--for-cloud`, existing rule and subagent copies are never overwritten. To refresh them, delete the copies that came from the plugin (rules `00` to `08` and the subagents) and run `/init-agent-system` with `--for-cloud` again.

#### Claude Code

1. Refresh the marketplace and update the plugin:

   ```bash
   claude plugin marketplace update agent-workbench
   claude plugin update agent-workbench@agent-workbench
   ```

2. Restart Claude Code. The update applies to new sessions.

3. In each initialized project, run `/agent-workbench:init-agent-system` again. It refreshes the managed scripts and replaces only the content of the managed block in `CLAUDE.md`: edits inside the block are lost, edits outside it are kept.

#### Differences in Claude Code

- Rules: only rules `00` to `08` reach Claude Code, through `CLAUDE.md`. `economia-de-tokens`, `mcp-triagem-obrigatoria`, and `uso-ferramentas-mcp` are Cursor-only.
- Hooks: Claude Code runs `hooks/claude-hooks.json`, which feeds the same timeline as the Cursor hooks.
- State: projects keep their state in `.cursor/agent-system/` and `.cursor/timeline/` in both editors, so a project initialized in one editor continues in the other.
- `--for-cloud` and `/roadmap visual` (Canvas) are Cursor-only.

Since 0.4.0, the `implementer`, `tester`, and `debugger` subagents use `model: inherit` in both editors (before, they used a Cursor-only model). To pin a model in Cursor, change `model:` in the agent file.

Commands renamed in 0.3.0: `investigacao-enxuta` is now `/lean-investigation`, `resumo-de-contexto` is now `/context-summary`, and `tarefa-em-etapas` is now `/staged-task`.

## Using Agent Workbench

### How commands work

- Type `/` in the chat and pick a command (in Claude Code, commands start with `/agent-workbench:`). You can add context after it, for example `/feature add CSV export to the sales report`.
- Each command handles one phase. The next phase does not start on its own unless the command says which one comes next.
- You do not need a command for trivial changes. Just ask; the agent classifies the request (class, complexity from XS to XL, and security risk) and scales the process to it.
- Rules and subagents apply automatically. You do not call subagents directly: on medium and larger tasks, the main agent delegates to `planner`, `implementer`, `tester`, `reviewer`, `security-reviewer`, and `debugger`, and for new interfaces to `designer`, `frontend-implementer`, and `design-reviewer`.
- For larger work, start a new chat for each phase. In initialized projects, the current state lives in `docs/progress/CURRENT.md` and `docs/progress/ROADMAP.md`, so a new chat picks up where the previous one stopped.

### Recommended workflows

New feature, from idea to merge:

```text
/brainstorm
/implementation-plan
/git-worktree
/tdd
/test-hygiene
/code-review
/update-docs
/commit-push
```

Feature in an existing system, in a single guided flow:

```text
/feature
```

New repository:

```text
/new-project
```

Bug:

```text
/lean-investigation
/root-cause
/bug-fix
```

Hard or intermittent bug:

```text
/debug
/root-cause
/tdd
```

New user interface (no `DESIGN.md` yet):

```text
/design
/ui-ux
/apple-design
```

`/design` runs `/design-discovery`, `/design-directions`, `/design-system`, and `/design-review` in order and stops wherever you must answer or choose. Each can also run on its own.

Variant of one screen inside an existing design:

```text
/ui-ux-experiment
/ui-ux
```

Large request without a formal spec:

```text
/staged-task
```

Long conversation, before switching to a new chat:

```text
/context-summary
```

### Command reference

Setup and project state:

- `/init-agent-system` — installs project state, timeline, and roadmap in the current project without replacing existing configuration or creating empty documents. Run it at the project root. Add `--for-cloud` to also copy rules and subagents for Cloud Agents.
- `/agent-status` — shows agents, skills, rules, hooks, and the current workflow state.
- `/roadmap` — shows the current phase and task, what is left, and what is blocked. It also creates or updates the roadmap, and `/roadmap visual` renders it as a Canvas. Requires `/init-agent-system`.
- `/timeline` — shows the append-only event history of an initialized project.
- `/lessons` — proposes, lists, confirms, or rejects project lessons. Only you confirm a lesson, and only confirmed lessons enter the agent context.
- `/help` — shows the command guide inside Cursor.

Planning:

- `/brainstorm` — for an idea that is still raw. Asks one question at a time, proposes alternatives, and ends with a design you approve. Writes no code and no plan.
- `/new-project` — new repository: PRD, architecture, specification, tasks, and progress. Does not create `AGENTS.md`.
- `/feature-development` — feature in an existing system: impact analysis, specification, tasks, implementation, tests, and review.
- `/feature` — shortcut for `/feature-development`.
- `/investigation` — understands how part of the system works. Does not implement.
- `/implementation-plan` — for an approved design. Produces a plan with real paths, code examples, and verification commands, written for someone who does not know the repository.
- `/change-request` — new scope discovered mid-task. Updates the specification or creates a dependency before continuing.

Implementation:

- `/implementation` — executes one step of the plan, tied to a requirement.
- `/tdd` — writes a test that fails for the right reason, then the minimum code, then refactors. No production code before the failing test.
- `/staged-task` — splits a large request into 3 to 7 verifiable steps and executes one at a time. Does not create a PRD, ADR, or detailed plan.
- `/refactoring` — changes structure while behavior stays the same, covered by tests.
- `/git-worktree` — creates an isolated copy of the repository to work in. Asks for your agreement and never pushes.

Bugs:

- `/lean-investigation` — finds the cause of a bug reading as little code and log as possible, one hypothesis at a time. Does not fix.
- `/debug` — reproduces the failure and finds the cause with evidence. Does not guess patches.
- `/root-cause` — records symptom, mechanism, evidence, and the missing test. Only after the cause is confirmed.
- `/bug-fix` — minimal fix after the cause is confirmed, with a regression test.

User interface:

- `/design` — full design pipeline for a new interface: interview, three rendered directions, `DESIGN.md` with tokens, and review. Skips approved stages and stops wherever you must answer or choose.
- `/design-discovery` — short interview, at most 5 questions with recommended answers, producing `design/brief.md`.
- `/design-directions` — three structurally different directions as HTML previews in `design/directions/`; you choose one and tune it with variety, motion, and density dials.
- `/design-system` — turns the chosen direction into `DESIGN.md` and `design/tokens.css`, with contrast pairs checked.
- `/design-review` — six-axis self-critique, P0/P1/P2 checklist, microcopy rules, and the anti-slop lint, reported in prose.
- `/ui-ux-experiment` — builds 2 or 3 interface options to compare. Does not implement all of them.
- `/ui-ux` — builds the chosen interface with empty, error, loading, and success states, and verifies the flow. Follows `DESIGN.md` when it exists and runs the lint before delivering.
- `/apple-design` — Apple-style interactive motion on the web: drag, swipe, sheets, springs, momentum, interruption, and reduced motion. Also reviews existing interactions. Does not handle layout or screen states.

Quality and security:

- `/test-hygiene` — checks that tests prove behavior, are deterministic, and fail for the right reason.
- `/code-review` — compares requirements, specification, acceptance criteria, tests, and code, including a Verification Audit (would the test fail if the requirement were wrong?). Each finding has a severity and evidence.
- `/security-review` — security audit of a feature or of the whole repository by the `security-reviewer` subagent, using the stack references. Produces a report with SEC findings and does not fix anything without your authorization. It is not Cursor's built-in `security-review` subagent.
- `/security-best-practices` — secure coding guidance for the detected stack, loading only its reference. Distinguishes vulnerabilities from hardening.

Documentation and delivery:

- `/update-docs` — aligns the specification, a new ADR, or progress with what changed. Does not rewrite accepted ADRs.
- `/commit-push` — branch before editing; with green tests, a single approval from you for commit, push, PR, and merge. Without approval, nothing leaves your machine.
- `/context-summary` — summary of up to 10 lines (goal, decisions, files, next steps) to paste into a new chat. Does not reread files or write anything.

Extending the harness:

- `/create-skill` — creates a new skill in your profile and adds it to `/help`. Does not create the skill inside the open repository unless you ask.
- `/create-agent` — creates a specialized subagent and registers when the orchestrator should delegate to it.

The anti-slop lint, `agent-system/scripts/lint_design.py`, blocks (P0) default indigo, purple-blue gradients, emoji icons, rounded cards with a side stripe, filler text, invented metrics, and placeholder image services, and warns (P1/P2) on raw colors and fonts outside the tokens, `transition: all`, removed focus outlines, and motion without reduced-motion. A color declared in the tokens or in the color section of `DESIGN.md` is the brand and passes; colors listed as forbidden in section 9 are not. In Claude Code, the hook runs it on every edited UI file and reports to the agent without blocking.

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
