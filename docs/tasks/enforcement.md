# Tasks: deterministic enforcement

Spec: [enforcement](../specs/enforcement.md). Tests run through the plugin suite, filtered by name.

### TASK-001: Classification floor
- Requirements: REQ-001, REQ-002, REQ-003
- Acceptance: AC-001, AC-002, AC-003, AC-004
- Files: agent-system/scripts/classify_floor.py, agent-system/scripts/lib.py
- Depends on: none
- Verification: TEST-001, TEST-007
- Done when: TEST-001 and TEST-007 pass
- Gate: check_proofs TEST-001 TEST-007
- Status: done

### TASK-002: Skill events
- Requirements: REQ-004
- Acceptance: AC-005
- Files: agent-system/scripts/hook.py, hooks/claude-hooks.json
- Depends on: none
- Verification: TEST-002
- Done when: TEST-002 passes
- Gate: check_proofs TEST-002
- Status: done

### TASK-003: Stop gate goal loop
- Requirements: REQ-005, REQ-006, REQ-007, REQ-008
- Acceptance: AC-006, AC-007, AC-008, AC-009, AC-010
- Files: agent-system/scripts/stop_gate.py, agent-system/scripts/hook.py, agent-system/scripts/record_event.py, agent-system/scripts/lib.py
- Depends on: TASK-001
- Verification: TEST-003, TEST-008
- Done when: TEST-003 and TEST-008 pass
- Gate: check_proofs TEST-003 TEST-008
- Status: done

### TASK-004: CI gate and installer flag
- Requirements: REQ-009
- Acceptance: AC-011
- Files: agent-system/scripts/ci_gate.py, agent-system/scripts/init_project.py, agent-system/templates/github/agent-workbench-gate.yml
- Depends on: none
- Verification: TEST-004
- Done when: TEST-004 passes
- Gate: check_proofs TEST-004
- Status: done

### TASK-005: Metrics
- Requirements: REQ-010
- Acceptance: AC-012
- Files: agent-system/scripts/metrics.py
- Depends on: TASK-001, TASK-002, TASK-003
- Verification: TEST-005
- Done when: TEST-005 passes
- Gate: check_proofs TEST-005
- Status: done

### TASK-006: Regression
- Requirements: REQ-001, REQ-005
- Acceptance: AC-001, AC-006
- Depends on: TASK-001, TASK-002, TASK-003, TASK-004, TASK-005
- Verification: TEST-006
- Done when: the whole suite passes
- Gate: check_proofs TEST-006
- Status: done

## Checks

### TEST-001: classification floor
- Acceptance: AC-001, AC-002, AC-003, AC-004
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_floor_"]
- Expected: exit 0; 5 passed

### TEST-002: skill events hold names only
- Acceptance: AC-005
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_skill_events_hold_names_only"]
- Expected: exit 0

### TEST-003: stop gate
- Acceptance: AC-006, AC-007, AC-008, AC-009, AC-010
- Task: TASK-003
- Command: ["python", "agent-system/scripts/test_system.py", "test_stop_"]
- Expected: exit 0; 7 passed

### TEST-004: CI gate and installer
- Acceptance: AC-011
- Task: TASK-004
- Command: ["python", "agent-system/scripts/test_system.py", "test_ci_gate_checks_changed_large_features", "test_init_with_ci_installs_workflow_once"]
- Expected: exit 0

### TEST-005: metrics
- Acceptance: AC-012
- Task: TASK-005
- Command: ["python", "agent-system/scripts/test_system.py", "test_metrics_report_skills_classifications_and_stop_gate"]
- Expected: exit 0

### TEST-006: full suite
- Acceptance: AC-001, AC-006
- Task: TASK-006
- Command: ["python", "agent-system/scripts/test_system.py"]
- Timeout: 900
- Expected: exit 0

### TEST-007: eval downgrade-refused
- Acceptance: AC-001, AC-004
- Task: TASK-001
- Command: ["python", "agent-system/scripts/run_evals.py", "downgrade-refused"]
- Expected: exit 0

### TEST-008: eval stop-gate-loop
- Acceptance: AC-006, AC-007
- Task: TASK-003
- Command: ["python", "agent-system/scripts/run_evals.py", "stop-gate-loop"]
- Expected: exit 0
