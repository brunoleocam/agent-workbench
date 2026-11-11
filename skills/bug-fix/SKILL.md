---
name: bug-fix
description: Diagnoses a defect, reproduces it with a failing test, applies the smallest fix, and checks regressions. Use when the user reports a bug, regression, incorrect behavior, or asks to fix a defect (bug, defeito, correção, regressão).
---

# Defect fix

## Flow

1. Follow `debug` until the cause has evidence. Record it with `root-cause`. Only then write the smallest test that fails for the right reason, via `tdd`.
2. Locate the cause in the existing code. Do not rewrite the module to "take advantage".
3. If the fix changes accepted behavior, a requirement, or architecture, stop and use `change-request`. A local fix stays in this skill.
4. Implement the minimum for the test to pass. Then refactor only if the intended behavior remains.
5. Run the target test and the relevant regression.
6. Do not declare it fixed with a required test failing.
7. For a non-trivial defect, review with `code-review` (the test passing is not enough) and update `docs/progress/CURRENT.md` if the project has spec-driven progress.

Report: cause, the test that proves the fix, the regression result, residual risk.

## Handoff

The `debugger` confirms the cause. The `tester` brings the evidence. The `reviewer` reviews without fixing. New scope goes back to the orchestrator via `change-request`.
