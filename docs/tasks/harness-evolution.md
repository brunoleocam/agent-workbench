# Tasks: evolução do harness

Spec: [harness-evolution](../specs/harness-evolution.md). Testes rodam pela suíte do plugin com filtro por nome.

### TASK-001: Núcleo de artefatos e validadores de spec e tarefas
- Requirements: REQ-001, REQ-002, REQ-003, REQ-008, REQ-009, REQ-010
- Acceptance: AC-001, AC-002, AC-003, AC-008, AC-009
- Files: agent-system/scripts/artifacts.py, agent-system/scripts/validate_spec.py, agent-system/scripts/validate_tasks.py, agents/planner.md, rules/02-spec-driven-development.mdc
- Depends on: none
- Verification: TEST-001, TEST-002, TEST-003, TEST-007
- Done when: TEST-001, TEST-002, TEST-003 e TEST-007 passam
- Gate: check_proofs TEST-001 TEST-002 TEST-003
- Status: done

### TASK-002: Provas, fingerprint e gate de verificação
- Requirements: REQ-004, REQ-005, REQ-006, REQ-007
- Acceptance: AC-004, AC-005, AC-006, AC-007
- Files: agent-system/scripts/check_proofs.py, agent-system/scripts/validate_verification.py, agent-system/scripts/artifacts.py
- Depends on: TASK-001
- Verification: TEST-004, TEST-005, TEST-006
- Done when: TEST-004, TEST-005 e TEST-006 passam
- Gate: check_proofs TEST-004 TEST-005 TEST-006
- Status: done

### TASK-003: Camada de segurança
- Requirements: REQ-011, REQ-012
- Acceptance: AC-010, AC-011
- Files: rules/08-security-engineering.mdc, skills/security-best-practices/, skills/security-review/SKILL.md, agents/security-reviewer.md, agent-system/scripts/init_project.py
- Depends on: TASK-001
- Verification: TEST-007, TEST-008
- Done when: TEST-007 e TEST-008 passam
- Gate: check_proofs TEST-007 TEST-008
- Status: done

### TASK-004: Verificação independente e contratos de handoff
- Requirements: REQ-013, REQ-020
- Acceptance: AC-012, AC-019
- Files: agents/tester.md, agents/reviewer.md, skills/code-review/SKILL.md, agent-system/docs/contracts.md
- Depends on: TASK-002
- Verification: TEST-007
- Done when: TEST-007 passa
- Gate: check_proofs TEST-007
- Status: done

### TASK-005: Lições e evals
- Requirements: REQ-014, REQ-016
- Acceptance: AC-013, AC-015
- Files: agent-system/scripts/lessons.py, agent-system/scripts/run_evals.py, agent-system/evals/fixtures/
- Depends on: TASK-002
- Verification: TEST-009, TEST-011
- Done when: TEST-009 e TEST-011 passam
- Gate: check_proofs TEST-009 TEST-011
- Status: done

### TASK-006: Eventos, hooks e init compatível
- Requirements: REQ-017, REQ-018, REQ-019
- Acceptance: AC-016, AC-017, AC-018
- Files: agent-system/scripts/lib.py, agent-system/scripts/hook.py, agent-system/scripts/record_event.py, agent-system/scripts/init_project.py
- Depends on: TASK-002
- Verification: TEST-008, TEST-012, TEST-013
- Done when: TEST-008, TEST-012 e TEST-013 passam
- Gate: check_proofs TEST-008 TEST-012 TEST-013
- Status: done

### TASK-007: Documentação e versão
- Requirements: REQ-021
- Acceptance: AC-020
- Files: README.md, agent-system/README.md, agent-system/docs/, skills/help/SKILL.md, skills/init-agent-system/SKILL.md, .cursor-plugin/plugin.json
- Depends on: TASK-003, TASK-004, TASK-005, TASK-006
- Verification: TEST-007, TEST-014, TEST-015
- Done when: TEST-007, TEST-014 e TEST-015 passam
- Gate: check_proofs TEST-014 TEST-015
- Status: done

## Checks

### TEST-001: parser de artefatos
- Acceptance: AC-001
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_artifacts_parse"]
- Expected result: exit 0; blocos, tipos, linhas e campos canônicos corretos

### TEST-002: validate_spec, válido, inválido, strict e layout
- Acceptance: AC-002, AC-008
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_validate_spec", "test_layout_ignores_code_folders"]
- Expected result: exit 0; spec válida sai 0, duplicata e AC órfão saem 1, `--strict` promove WARN, layout respeitado, path traversal sai 2

### TEST-003: validate_tasks
- Acceptance: AC-003
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_validate_tasks"]
- Expected result: exit 0; dependência inexistente, ciclo, bloqueio sem dependência e done sem prova saem 1

### TEST-004: check_proofs, exit codes, timeout e política
- Acceptance: AC-004, AC-005
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_check_proofs", "test_policy_subcommands", "test_inline_code_refused_by_default", "test_timeout_kills_grandchildren"]
- Expected result: exit 0; PASS, FAIL, TIMEOUT, ERROR e REFUSED com o exit code real; subcomandos que instalam e código inline recusados também em shell e atrás de wrappers, arquivo de teste permitido; neto morto no timeout

### TEST-005: fingerprint
- Acceptance: AC-006
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_fingerprint", "test_proofs_keep_fingerprint_from_before_the_run"]
- Expected result: exit 0; código muda o fingerprint, doc do harness não, também em subpasta de repositório git; prova guarda o fingerprint de antes da execução

### TEST-006: gate de verificação
- Acceptance: AC-007
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_validate_verification_gate", "test_small_change_needs_no_review"]
- Expected result: exit 0; prova ausente ou obsoleta, review ausente e achado aberto reprovam; caso completo passa

### TEST-007: camadas registradas e ligadas
- Acceptance: AC-009, AC-010, AC-012, AC-019, AC-020
- Task: TASK-003
- Command: ["python", "agent-system/scripts/test_system.py", "test_registry_and_new_layers_are_wired", "test_static"]
- Expected result: exit 0; rule 08, skills, referências, security-reviewer, EARS, Verification Audit, contratos e versão 0.2.0 presentes

### TEST-008: init com stack, superfícies, migração e cloud
- Acceptance: AC-011, AC-018
- Task: TASK-003
- Command: ["python", "agent-system/scripts/test_system.py", "test_init_stack_detection_migration_and_cloud", "test_workflows"]
- Expected result: exit 0; frameworks e superfícies detectados, estado migrado sem perda, overrides preservados, `--for-cloud` copia rule 08 e security-reviewer

### TEST-009: ciclo de lições
- Acceptance: AC-013
- Task: TASK-005
- Command: ["python", "agent-system/scripts/test_system.py", "test_lessons_lifecycle", "test_lessons_edited_by_hand_stay_redacted"]
- Expected result: exit 0; duplicata e segredo saem 1, só confirmadas no sessionStart

### TEST-011: evals determinísticas
- Acceptance: AC-015
- Task: TASK-005
- Command: ["python", "agent-system/scripts/run_evals.py"]
- Expected result: exit 0; todas as fixtures com o resultado esperado

### TEST-012: hook marca inferido e redige segredo
- Acceptance: AC-017
- Task: TASK-006
- Command: ["python", "agent-system/scripts/test_system.py", "test_hook_marks_inferred_and_redacts"]
- Expected result: exit 0; evento com `inferred: true`, token ausente da timeline

### TEST-013: eventos semânticos novos
- Acceptance: AC-016
- Task: TASK-006
- Command: ["python", "agent-system/scripts/test_system.py", "test_new_semantic_events_update_state"]
- Expected result: exit 0; `verification.<slug>` atualizado sem perder chaves

### TEST-014: READMEs citam só o que existe
- Acceptance: AC-020
- Task: TASK-007
- Command: ["python", "agent-system/scripts/test_system.py", "test_readmes_cite_only_existing"]
- Expected result: exit 0; todo `/comando` e script citado existe

### TEST-015: suíte completa
- Acceptance: AC-020
- Task: TASK-007
- Command: ["python", "agent-system/scripts/test_system.py"]
- Timeout: 900
- Expected result: exit 0; nenhum teste falha
