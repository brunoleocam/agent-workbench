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

File header: goal in one sentence, approach, the stack already used in the repo, constraints copied from the spec.

For M or larger, each task is a `### TASK-NNN` with `- Requirements:`, `- Acceptance:`, `- Files:`, `- Depends on:`, `- Verification:` (TEST IDs), `- Done when:`, `- Gate:`, and `- Status:`; each verification is a `### TEST-NNN` with `- Acceptance:`, `- Task:`, and a `- Command:` executable without a shell. Format in `agent-system/docs/artifacts.md`. Run `validate_tasks.py --feature <slug>` before delivering the plan.

Do not commit the plan unless the user asks. When done, the next step is `implementation` or `tdd`, one task at a time.
