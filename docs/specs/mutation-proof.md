---
status: approved
complexity: M
security_risk: LOW
security_triggers: command_execution, file_system
approved_by: brunoleocam (Phase 1 plan, item 2.1)
---

# Spec: mutation proof (0.7.0)

Problem: the `weak-test-passes-gate` eval documents that a TEST without assertions passes the gate. The only defense is the reviewer's Verification Audit, which is a model's judgment.

Outcome: an optional, deterministic mutation proof. A TEST (or its task) lists the Python files it covers in `Mutate`; `check_mutation.py` breaks those files one change at a time and counts the mutants the feature's TESTs kill. When the spec front matter (`mutation_min_score`) or `layout.json` (`mutation.min_score`) sets a minimum, the gate requires a fresh score at or above it.

## Requirements

### REQ-001: Mutation score
WHEN `check_mutation.py --feature <slug>` runs, THE SYSTEM SHALL mutate each Python file listed in a `Mutate` field of a TEST or of its task, one site at a time (comparison, arithmetic, boolean operator, `not`, `if`/`while` condition, boolean and integer constants, returned value), run the TESTs that list the file through the check_proofs.py policy, count a mutant as killed when any of them fails or times out, and record the score with the workspace fingerprint and the TEST commands.

### REQ-002: Safe in-place mutation
THE SYSTEM SHALL restore every mutated file byte for byte (with its modification time) after each run, give each mutant a distinct modification time and run the TESTs with `PYTHONDONTWRITEBYTECODE=1` so no stale bytecode is imported, keep a backup in `.agent-system/mutation/` while it runs, restore a backup left by an interrupted run before starting (only to paths inside the project), refuse a second run while the process holding `.agent-system/mutation.lock` is alive (taking the lock before any restore), and make `check_proofs.py` and `validate_verification.py` refuse to prove while a backup is pending.

### REQ-003: Valid baseline
IF a required TEST that declares `Mutate` does not pass unmutated, or a listed file is not an existing UTF-8 Python file, THEN THE SYSTEM SHALL record the run as FAIL or ERROR with the reason and exit 1; each mutant run SHALL be limited to five times the slowest unmutated run (at least 10 s), and the whole run to `--budget-seconds`, after which the score is marked truncated.

### REQ-004: Gate criterion
WHEN a minimum mutation score is set, THE SYSTEM SHALL make `validate_verification.py` fail if the score is missing, not measured, recorded for another workspace state, other TESTs, other TEST commands, or other `Mutate` files, partial (cut by the time budget or `--max-mutants`), or below the minimum; a minimum in the spec with no TEST declaring `Mutate` SHALL fail, one in `layout.json` SHALL warn, and a minimum that is not a number above 0 and at most 1 SHALL fail the gate and stop `check_mutation.py` with exit 2.

## Acceptance Criteria

### AC-001: Weak test fails the gate
- Requirements: REQ-001, REQ-004
Given the weak-test fixture (TESTs without assertions) with `Mutate: src/coupon.py` and `mutation_min_score: 0.6`
When `check_mutation.py` and then `validate_verification.py` run
Then the score is 0.0 and the gate fails naming the score.

### AC-002: Strong tests pass
- Requirements: REQ-001, REQ-004
Given the complete-feature fixture with the same settings
When the same commands run
Then the score is 1.0 and the gate passes.

### AC-003: Files restored
- Requirements: REQ-002
Given a covered file with CRLF line endings, or a backup left by an interrupted run
When `check_mutation.py` runs
Then the file ends byte-identical to its original and the backup folder is gone.

### AC-004: Invalid baseline
- Requirements: REQ-003
Given a TEST that fails unmutated, or `Mutate` naming a `.ts` file
When `check_mutation.py` runs
Then it exits 1 with the reason.

### AC-005: Fresh score only
- Requirements: REQ-004
Given a recorded score
When a project file changes, or no minimum is set, or the spec sets a minimum and no TEST declares `Mutate`
Then the gate fails as stale, ignores mutation, or fails as undeclared, respectively.

### AC-006: No stale bytecode
- Requirements: REQ-002
Given a module whose only mutant has the same size (`A = 5` -> `A = 6`), its bytecode already cached, and bytecode caching on in the environment
When `check_mutation.py` runs three times
Then each run scores 1.0 and the restored module imports as the original.

### AC-007: Interrupted run blocks proofs
- Requirements: REQ-002
Given a pending backup from an interrupted run, or one that points outside the project
When `check_proofs.py`, `validate_verification.py`, and then `check_mutation.py` run
Then the first exits 2, the gate fails naming the pending run, the file is restored byte for byte, the backup folder is gone, and a path outside the project is never written.

### AC-008: Invalid minimum
- Requirements: REQ-004
Given `mutation_min_score` of `60`, `0`, or `abc`
When the gate and `check_mutation.py` run
Then the gate fails naming the value and `check_mutation.py` exits 2.

### AC-009: Score bound to targets and commands
- Requirements: REQ-001, REQ-004
Given a recorded score
When the `Mutate` files are narrowed, or a TEST command changes
Then the gate fails as targets changed or commands changed.

### AC-010: Unmeasured run, layout minimum, encoding
- Requirements: REQ-003, REQ-004
Given a TEST failing unmutated, a minimum only in `layout.json` with no `Mutate`, or a non-UTF-8 source file
When the scripts run
Then the gate reports "Mutation run is FAIL", warns for the layout minimum, and the run is ERROR "not UTF-8".

### AC-011: The lock protects a live run
- Requirements: REQ-002
Given a lock held by a live process and a pending backup, or a lock left by a finished process
When `check_mutation.py` starts
Then it exits 2 and leaves the live run's file and backup untouched, or it takes the lock over, restores the file, and removes the lock at the end.

### AC-012: Partial runs do not pass
- Requirements: REQ-004
Given a run with `--max-mutants 1`
When the gate runs
Then the score is marked partial and the gate fails.

## Assumptions

- Mutants are first-order and include equivalent mutants; the minimum is a project choice, not a universal number.

## Constraints

- Standard library only (`ast`). Python files only; JavaScript, TypeScript, C#, and PHP keep their own tools (Stryker, Infection) outside this gate.

## Open Questions

## Decisions

- The score belongs to the feature's TESTs together: a mutant of a file counts as killed when any TEST that lists the file kills it.
