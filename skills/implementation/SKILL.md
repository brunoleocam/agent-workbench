---
name: implementation
description: Executes one independently verifiable implementation step tied to a requirement and its tests. Use when implementing a specified task, continuing planned work, or applying Red-Green-Refactor to a single slice (implementar tarefa, próximo passo, TDD).
---

# Implementation

One step. Do not implement large slices or parts unrelated to this step's requirement.

## Per step

0. If the plan stamped a `Baseline` for the task, run `check_drift.py --feature <slug> --task <TASK-ID> --strict` first; on exit 1, stop and report instead of editing.
1. Point to the exact requirement or acceptance criterion. If none exists for non-trivial behavior, go back to `feature` or `new-project` and write the spec first.
2. Point to the tests or evals that prove that requirement.
3. Follow `tdd`: the smallest useful test fails for the right reason before production code.
4. Green: the smallest coherent change makes the test pass.
5. Run the target verification and the relevant regression.
6. Refactor without changing the intended behavior.
7. Update the task status and the project artifacts.

Do not declare the step complete with a required test failing.

## Handoff

The `implementer` executes. Verification goes to the `tester`. Independent review goes to the `reviewer`. A scope change stops at the orchestrator.

If a new idea, bug, requirement, or dependency appears, stop and use `change-request`.

When closing the step, write the checkpoint (rule `06-checkpoint-and-progress`): what went in, spec met, tests and results, review, findings, fixes, what remains, blockers, next step. The next step comes from the task graph.

Significant change: after this step is green and the regression passes, use `code-review` before calling the work done.
