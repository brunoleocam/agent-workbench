# Tasks: desconto por cupom

### TASK-001: Aplicar cupom e rejeitar expirado
- Requirements: REQ-001, REQ-002
- Acceptance: AC-001, AC-002
- Files: src/coupon.py
- Verification: TEST-001
- Done when: TEST-001 passes
- Gate: check_proofs TEST-001
- Status: done

### TEST-001: total com desconto
- Acceptance: AC-001
- Task: TASK-001
- Command: ["__PYTHON__", "checks/test_apply.py"]
