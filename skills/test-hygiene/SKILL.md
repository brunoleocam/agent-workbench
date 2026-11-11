---
name: test-hygiene
description: Reviews or writes tests so each one proves a behavior, fails for the right reason, and stays deterministic. Use when adding, cleaning, or reviewing tests (higiene de teste, teste frágil, teste que não prova nada).
---

# Test hygiene

A test is evidence of behavior, not a description of the internal implementation.

When writing or reviewing:

- The name states the behavior and the condition.
- A test fails for one reason. If it needs several unrelated asserts, split it.
- Arrange, act, assert are visible. No magic data scattered around.
- Deterministic: no `sleep` to synchronize, no uncontrolled clock or randomness, no real network in a unit test.
- It does not depend on suite order.
- It does not assert a private detail (how many times an internal function was called) if the contract is the observable result.
- The test that covers a bug fails on the old code for the bug's reason.
- Explicit fixtures and mocks. Mock only at the boundary you do not control.

If a test passes with the wrong implementation, it is useless. Rewrite the test before trusting it.

Apply `tdd` when you are still creating the test. This skill judges quality; it does not replace seeing the test fail.
