---
name: refactoring
description: Restructures code without changing intended behavior, guarded by existing or characterization tests. Use when the user asks to refactor, clean up, simplify, or restructure without adding behavior (refatorar, limpar, reestruturar, sem mudar comportamento).
---

# Refactoring

The intended behavior does not change. If behavior must change, stop and use `feature` or `change-request`.

## Flow

1. Name what improves (boundaries, duplication, complexity) and what must stay the same.
2. Make sure tests characterize the current behavior. If none exist, write them before moving code and watch them pass on the old code.
3. A new architecture decision becomes an ADR. Do not decide relevant structure only in the diff.
4. Take the smallest coherent step. Run the characterization tests and the regression after each step.
5. Do not mix a feature, bugfix, or mass formatting in the same step.
6. Review with `code-review`, looking at unnecessary changes and unintended behavior.
7. Update the checkpoint if the work is relevant: what changed in the structure, which tests proved the behavior stayed the same.
