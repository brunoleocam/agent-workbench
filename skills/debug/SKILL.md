---
name: debug
description: Finds the root cause of a bug, test failure, or unexpected behavior with evidence before any fix. Use when something fails, a test is red, or behavior is wrong, before proposing a patch (debug, depurar, teste falhando, comportamento inesperado).
---

# Debug

Do not propose a fix before the cause has evidence. A patch on the symptom does not end the debug.

1. Write the symptom: what happened, what was expected, since when.
2. Reproduce. If you cannot reproduce, say what is missing. Do not guess a fix.
3. Read the failing path (test, stack, code). One hypothesis at a time.
4. Test the hypothesis with evidence: a test, a log, reading state, a minimal input. Rule it out or confirm it.
5. The cause explains the symptom. If it does not, keep going. Do not stack attempts.
6. With the cause confirmed, record it with `root-cause` and fix it with `tdd` or `bug-fix`.

Stop if the fix changes a requirement or architecture and use `change-request`.
