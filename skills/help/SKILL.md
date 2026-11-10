---
name: help
description: Explains each profile slash command, when to use it, and what it refuses to do. Use only when the user invokes /help.
disable-model-invocation: true
---

# /help

Reply only with the guide below, in the language the user is writing in. Do not start any flow.

## How to use

Call a command by name in a new conversation. In Claude Code, commands carry the plugin prefix: `/agent-workbench:feature` instead of `/feature`. A command handles one phase. The next one does not start on its own, unless the skill itself says which comes next.

Typical order for something new: `/brainstorm` → approved spec → `/implementation-plan` → `/git-worktree` if you want isolation → `/tdd` or `/implementation` → `/test-hygiene` if the tests turn out weak → `/code-review` → `/update-docs` → `/commit-push` only if you ask.

Defect: `/debug` → `/root-cause` → `/tdd` or `/bug-fix`.

Interface: `/brainstorm` or `/ui-ux-experiment` → you choose → `/ui-ux`.

A trivial change needs no command. An old repository is not migrated wholesale.

For M or larger with `/init-agent-system`, the gates are scripts in `.cursor/agent-system/scripts/`: `validate_spec.py`, `validate_tasks.py`, `check_proofs.py` (runs the tests and records the real exit code), and `validate_verification.py` (exits 0 only with tested criteria, proofs of the current code, a review, and blocking findings resolved). Contracts in the plugin's `agent-system/docs/cli.md`.

## Commands

- `/brainstorm` — a raw idea. One question at a time, alternatives, a design approved by you. Writes no code and no plan.
- `/new-project` — a new repository. PRD, architecture, spec, tasks, and progress. Does not create `AGENTS.md`.
- `/feature` — the same flow as `/feature-development`.
- `/feature-development` — a feature in an existing system: impact, spec, tasks, implementation, tests, and review.
- `/init-agent-system` — installs the system in this project without deleting existing config and without creating empty docs.
- `/create-agent` — creates a specialized subagent and registers the delegation in the orchestrator.
- `/agent-status` — agents, skills, rules, hooks, and the workflow state.
- `/timeline` — the append-only events of the initialized project.
- `/investigation` — understand the system. Does not implement.
- `/implementation-plan` — an already approved design. A plan with real paths, code examples, and verification commands, for someone who does not know the repo.
- `/git-worktree` — an isolated copy of the repository. Asks for your agreement. Does not push.
- `/implementation` — one step of the plan, tied to a requirement.
- `/tdd` — the test fails for the right reason, minimum code, refactor. No production code before the red.
- `/test-hygiene` — the test proves behavior, is deterministic, and fails for the right reason.
- `/ui-ux-experiment` — 2 or 3 interfaces to compare. Does not implement all of them.
- `/ui-ux` — builds the chosen interface with empty, error, loading, and success states, and verifies the flow.
- `/apple-design` — Apple-style interactive motion on the web: drag, swipe, sheets, springs, momentum, interruption, and reduced motion; also reviews interactions. Does not handle layout or screen states.
- `/bug-fix` — minimal fix after the cause is confirmed, with a regression test.
- `/debug` — reproduces and finds the cause with evidence. Does not guess patches.
- `/root-cause` — records symptom, mechanism, evidence, and the missing test. Only with a confirmed cause.
- `/refactoring` — changes structure. Behavior stays, covered by tests.
- `/change-request` — new scope in the middle of a task. Updates the spec or creates a dependency before continuing.
- `/code-review` — compares requirements, spec, criteria, tests, and code, with a Verification Audit (would the test fail if the requirement were wrong?). A finding has severity and evidence.
- `/security-review` — security audit of the feature or the repository by the `security-reviewer`, with stack references. Produces a report with SEC findings; does not fix without your authorization. It is not Cursor's built-in `security-review` subagent.
- `/security-best-practices` — secure coding in the detected stack, loading only its reference. Distinguishes vulnerability from hardening.
- `/lessons` — proposes, lists, confirms, or rejects project lessons. Only you confirm; only confirmed lessons enter the context.
- `/update-docs` — aligns the spec, a new ADR, or progress with what changed. Does not rewrite an accepted ADR.
- `/commit-push` — branch before editing; with green tests, a single approval from you for commit, push, PR, and merge. Without approval, nothing leaves your machine.
- `/roadmap` — shows which phase and task you are in, what is left, and what is blocked. Also creates, updates, or renders the Canvas view (`/roadmap visual`). Only in a project with `/init-agent-system`.
- `/context-summary` — a summary of up to 10 lines (goal, decisions, files, next steps) to paste into a new chat. Does not reread files or write anything.
- `/lean-investigation` — finds a bug's cause reading the minimum, one hypothesis at a time. Does not fix.
- `/staged-task` — splits a large request into 3 to 7 verifiable steps and executes one at a time. Does not create a PRD, ADR, or detailed plan.
- `/create-skill` — creates a new skill in the plugin and adds the command to this guide. Does not create a skill inside the repository unless you ask.
- `/help` — shows this guide.
