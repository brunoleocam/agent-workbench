---
name: root-cause
description: Writes a root-cause record with symptom, evidence, mechanism, and the regression test. Use after a defect cause is confirmed and must be documented (causa raiz, root cause, postmortem curto, por que o bug passou).
---

# Root cause

Write it only after `debug` (or equivalent evidence) has confirmed the cause. Without evidence, go back to `debug`. Do not invent a mechanism.

Write it in the repo's place for changes or bugs. If there is none, use `docs/changes/` only when the project already uses that tree; otherwise, leave the record in the reply and in the front's checkpoint.

## Record

- Symptom
- Impact
- How to reproduce
- Cause: the mechanism, not just the file name
- Evidence: test, log, code read
- Why the existing tests did not catch it
- Fix
- Regression test that fails without the fix

Do not rewrite an old record to make it prettier. If the cause changed, write what the new evidence showed.
