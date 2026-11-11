---
name: investigation
description: Explores an existing system and records findings without implementing. Use when the user asks to investigate, understand, explore, spike, or explain how the current system works before changing it (investigar, entender, explorar, spike, como funciona).
---

# Investigation

Do not implement. Do not "take the opportunity" to fix or refactor. A finding that requires a change becomes a separate task, bug, or change request.

## Flow

1. State the question the investigation answers.
2. Read the existing code, tests, specs, and ADRs. The chat does not replace those artifacts.
3. Answer with evidence (file, symbol, test), not assumption.
4. Write the result where the project already documents discoveries, or in `docs/progress/CURRENT.md` / a note in `docs/specs/` if that is the repo's tree. Include:
   - the question
   - what the system does today
   - constraints and risks
   - what was not verified
   - recommended next step (specify, fix, refactor, or stop)
5. If the user wants to act next, classify again and switch skills. Do not keep coding from the investigation without a spec when the behavior is non-trivial.
