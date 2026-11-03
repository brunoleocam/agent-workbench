# Tasks: desconto por cupom

### TASK-001: Aplicar cupom
- Requirements: REQ-001
- Acceptance: AC-001
- Depends on: TASK-002
- Verification: TEST-001
- Done when: TEST-001 passes
- Gate: check_proofs TEST-001
- Status: todo

### TASK-002: Rejeitar expirado
- Requirements: REQ-002
- Acceptance: AC-002
- Depends on: TASK-001
- Verification: TEST-002
- Done when: TEST-002 passes
- Gate: check_proofs TEST-002
- Status: todo

### TASK-003: Limite por cliente (CR-001)
- Requirements: REQ-001
- Acceptance: AC-001
- Depends on: TASK-404
- Verification: TEST-001
- Done when: TEST-001 passes
- Gate: check_proofs TEST-001
- Status: todo

### TASK-004: Auditoria de cupom
- Requirements: REQ-002
- Acceptance: AC-002
- Verification: TEST-002
- Done when: TEST-002 passes
- Gate: check_proofs TEST-002
- Status: blocked

### TEST-001: total com desconto
- Acceptance: AC-001
- Command: ["__PYTHON__", "checks/test_apply.py"]

### TEST-002: cupom expirado
- Acceptance: AC-002
- Command: ["__PYTHON__", "checks/test_apply.py"]
