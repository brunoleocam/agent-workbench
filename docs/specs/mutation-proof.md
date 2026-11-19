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
THE SYSTEM SHALL restore every mutated file byte for byte after each run, keep a backup in `.agent-system/mutation/` while it runs, and restore a backup left by an interrupted run before starting.

### REQ-003: Valid baseline
IF a TEST that declares `Mutate` does not pass unmutated, or a listed file is not an existing Python file, THEN THE SYSTEM SHALL record the run as FAIL or ERROR with the reason and exit 1.

### REQ-004: Gate criterion
WHEN a minimum mutation score is set, THE SYSTEM SHALL make `validate_verification.py` fail if the score is missing, not measured, recorded for another workspace state or other TEST commands, or below the minimum; a minimum in the spec with no TEST declaring `Mutate` SHALL fail, and one in `layout.json` SHALL warn.

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

## Assumptions

- Mutants are first-order and include equivalent mutants; the minimum is a project choice, not a universal number.

## Constraints

- Standard library only (`ast`). Python files only; JavaScript, TypeScript, C#, and PHP keep their own tools (Stryker, Infection) outside this gate.

## Open Questions

## Decisions

- The score belongs to the feature's TESTs together: a mutant of a file counts as killed when any TEST that lists the file kills it.
