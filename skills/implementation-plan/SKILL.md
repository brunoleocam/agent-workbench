---
name: implementation-plan
description: Writes a comprehensive implementation plan with exact file paths, complete code examples, and verification steps for an engineer with zero codebase context. Use when the design or spec is approved and tasks must be detailed before coding (plano de implementação, quebrar em tarefas, design pronto).
---

# Implementation plan

The design or spec is already approved. This skill produces the plan. It does not implement.

The reader is a skilled engineer with no context on this repository and little knowledge of the domain. File paths, examples, and verification must be enough on their own.

## Before writing

1. Read the approved spec and the code the paths cite. Do not invent a path. If the file does not exist yet, mark it as create and show the real parent directory.
2. If the spec covers independent subsystems, propose one plan per subsystem. Each plan delivers testable software.
3. Map the files to create or change and each one's responsibility. Follow the repo's pattern. Do not restructure files unrelated to the spec.

## Where to write

`docs/tasks/` if the project uses the spec-driven tree. Otherwise, the place for plans the repo already has. One file per front: `docs/tasks/NNNN-title.md`.

## Each task

A task is the smallest piece a reviewer can accept or reject alone, with its own test.

For each task:

- The requirement or acceptance criterion it covers
- Exact paths
- Steps in order: failing test, command to see the failure, minimal code, command to see green, regression
- A complete code example for whatever is not obvious, in the repo's style. No pseudocode in place of code
- Expected result of each command
- Dependency on another task, if any
- Out of scope: what the executor must not touch, so a cheaper model does not wander
- Stop if: the observations that mean the plan no longer matches reality (a file is missing or already changed, a function has another signature, a command fails before any edit). The executor halts and reports instead of improvising

File header: goal in one sentence, approach, the stack already used in the repo, constraints copied from the spec.

For M or larger, each task is a `### TASK-NNN` with `- Requirements:`, `- Acceptance:`, `- Files:`, `- Depends on:`, `- Verification:` (TEST IDs), `- Done when:`, `- Gate:`, `- Status:`, and, recommended, `- Out of scope:` and `- Stop if:`; each verification is a `### TEST-NNN` with `- Acceptance:`, `- Task:`, and a `- Command:` executable without a shell. Format in `agent-system/docs/artifacts.md`. Run `validate_tasks.py --feature <slug>` before delivering the plan, then stamp it against the code it was written for:

```bash
python .cursor/agent-system/scripts/check_drift.py --feature <slug> --stamp
```

This adds a `- Baseline:` line (short content digests of each task's `Files:`) to every todo task. An executor runs `check_drift.py --feature <slug> --task TASK-NNN --strict` before touching anything and stops when it exits 1: someone changed those files after the plan was written. A change made by another task of the same plan that is done or in progress is expected and does not stop the executor. After an intentional re-plan, `--stamp --refresh` records the new baseline. The per-file stamp is adapted from [shadcn/improve](https://github.com/shadcn/improve) (MIT), which stamps a git commit into each plan.

Do not commit the plan unless the user asks. When done, the next step is `implementation` or `tdd`, one task at a time.
