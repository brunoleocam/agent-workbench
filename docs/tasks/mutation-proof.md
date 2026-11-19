# Tasks: mutation proof

Spec: [mutation-proof](../specs/mutation-proof.md).

### TASK-001: check_mutation.py
- Requirements: REQ-001, REQ-002, REQ-003
- Acceptance: AC-003, AC-004, AC-006, AC-007, AC-010
- Files: agent-system/scripts/check_mutation.py, agent-system/scripts/artifacts.py, agent-system/scripts/lib.py
- Depends on: none
- Verification: TEST-001
- Done when: TEST-001 passes
- Gate: check_proofs TEST-001
- Status: done

### TASK-002: Gate criterion and evals
- Requirements: REQ-004
- Acceptance: AC-001, AC-002, AC-005, AC-008, AC-009
- Files: agent-system/scripts/validate_verification.py, agent-system/evals/fixtures/mutation-catches-weak-test/, agent-system/evals/fixtures/mutation-strong-tests/
- Depends on: TASK-001
- Verification: TEST-002, TEST-003
- Done when: TEST-002 and TEST-003 pass
- Gate: check_proofs TEST-002 TEST-003
- Status: done

## Checks

### TEST-001: mutator and safety
- Acceptance: AC-003, AC-004, AC-006, AC-007, AC-008, AC-010
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_mutation_"]
- Expected: exit 0; 9 passed

### TEST-002: gate criterion
- Acceptance: AC-005, AC-009, AC-010
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_gate_"]
- Expected: exit 0

### TEST-003: evals
- Acceptance: AC-001, AC-002
- Task: TASK-002
- Command: ["python", "agent-system/scripts/run_evals.py", "mutation-catches-weak-test", "mutation-strong-tests"]
- Expected: exit 0
