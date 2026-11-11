---
name: tdd
description: Implements behavior by writing a failing test, making it pass, then refactoring. Use when implementing a feature, bugfix, or behavior change before production code (TDD, teste primeiro, red green refactor).
---

# TDD

No production code without a failing test first, failing for the right reason.

## Cycle

1. Red. Write the smallest test that expresses the acceptance criterion. Run it. Confirm it fails for the expected reason, not because of a setup error.
2. Green. Write the minimum to pass. Run the target test.
3. Refactor. Improve the code without changing behavior. The relevant suite stays green.

If production code was written before the test, delete that code and start over from the test. Do not adapt the test to fit the code already done.

Bug: the red test is the reproduction. The fix comes after.

Do not use when the user asks for a throwaway prototype, or when no runner exists. In that case, say what was not verified. Doubts of "just this once" on code that will stay: do the cycle.

Test hygiene: the `test-hygiene` skill.
