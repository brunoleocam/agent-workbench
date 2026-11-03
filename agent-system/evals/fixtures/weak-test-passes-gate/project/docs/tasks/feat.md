# Tasks: desconto por cupom

### TASK-001: Aplicar cupom válido
- Requirements: REQ-001
- Acceptance: AC-001
- Verification: TEST-001
- Done when: TEST-001 passes
- Gate: check_proofs TEST-001
- Status: done

### TASK-002: Rejeitar cupom expirado
- Requirements: REQ-002
- Acceptance: AC-002
- Depends on: TASK-001
- Verification: TEST-002
- Done when: TEST-002 passes
- Gate: check_proofs TEST-002
- Status: done

### TEST-001: total com desconto
- Acceptance: AC-001
- Task: TASK-001
- Command: ["__PYTHON__", "checks/smoke_apply.py"]

### TEST-002: cupom expirado
- Acceptance: AC-002
- Task: TASK-002
- Command: ["__PYTHON__", "checks/smoke_expired.py"]
