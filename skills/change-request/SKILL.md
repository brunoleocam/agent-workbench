---
name: change-request
description: Classifies a change discovered during implementation, analyzes impact, and updates the spec or creates a dependent task before resuming. Use when a new requirement, bug, idea, dependency, or scope change appears mid-implementation (change request, mudança de escopo, dependência, requisito novo no meio da tarefa).
---

# Change request

Something new appeared while `TASK-X` was in progress. Do not change `TASK-X`'s code to absorb it without classifying it.

## Classify

- Local implementation adjustment
- Requirement change
- Spec change
- Architecture change
- Prerequisite dependency
- New independent task
- Bug in existing behavior

## Impact

List what is affected: requirements, specs, ADRs, tests/evals, tasks, dependencies, possible regressions.

## What to do

| Class | Action |
| --- | --- |
| Small local adjustment | Update the current task's code and tests |
| Requirement, spec, or architecture | Write `docs/changes/CR-NNNN.md` and update the artifacts before continuing |
| Dependency or new task | Create the task and record that `TASK-X` depends on `TASK-Z`. Do not resolve the dependency inside unrelated work |
| Existing bug | Record it and use `bug-fix` if it is blocking; otherwise leave it as a separate task |

`docs/changes/CR-NNNN.md`: what appeared, class, impact, decision, artifacts updated, task that can resume.

Resume `TASK-X` only after that update. The next step comes from the dependencies, not from the impulse to keep editing.
