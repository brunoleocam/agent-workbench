---
name: debug
description: Finds the root cause of a bug, test failure, or unexpected behavior with evidence before any fix, reading as little code and log as it can. Use when something fails, a test is red, or behavior is wrong (debug, depurar, teste falhando, achar a causa, onde quebra).
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

## Reading little

1. Anchor: extract something searchable from the symptom (exact error message, stack frame, function, route, error code). Without an anchor, ask the user for an objective datum before exploring.
2. Search the anchor with Grep (exact text) or semantic search restricted to the likely folder. Do not list folders or open files "to understand".
3. Read only the result's section (the function, about 30 lines). Follow the next call by searching the symbol, not by opening the whole file.
4. One hypothesis at a time, in one line, with the minimum evidence that confirms or rules it out: a snippet, a value, a test, a log line.
5. Tests and logs: run only the failing case and filter the output by the anchor (`Select-String` or `grep`, with `-First` or `head`).
6. Stop when the cause explains the symptom. After 3 ruled-out hypotheses or about 8 reads without a cause, stop and report what was ruled out and which datum is missing.
7. If broad exploration is unavoidable (many files, a huge log), delegate to an `explore` or `debugger` subagent asking for a short answer with `path:line`.

## Output (up to 6 lines)

```
Cause: <mechanism, in one sentence>
Evidence: <path:line> — <what proves it>
Ruled out: <hypothesis>; <hypothesis>
Suggested fix: <one line, not applied>
Next: /bug-fix or /tdd (and /root-cause if worth recording)
```
