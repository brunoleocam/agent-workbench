---
name: lean-investigation
description: Finds a bug's cause reading the minimum of code and logs, with directed search and one hypothesis at a time. Does not fix. Use when the failure point is not obvious or the user wants to find the cause spending little context (investigação enxuta, achar a causa, onde quebra, por que dá erro).
---

# Lean investigation

Same principles as `debug` (cause with evidence before any fix). This skill defines how to get there reading little.

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
