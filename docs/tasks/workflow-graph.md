# Tasks: grafo de workflow declarado

Spec: [workflow-graph](../specs/workflow-graph.md) (approved).

**Objetivo desta leva:** Fase 1, o grafo de execução (REQ-001 a REQ-012). As fases 2 a 4 entram neste arquivo como novas tasks quando a Fase 1 estiver verde; o gate (`validate_verification.py`) só roda no fim da Fase 4, porque antes disso os AC-011 a AC-019 não têm TEST.

**Abordagem:** primeiro o dado (`workflow.json`) e o validador, que são a base do resto. Depois o roteador e o contador de revisões. Por fim a integração: diagrama no README, orquestrador, bloco do `CLAUDE.md`, init e a eval de escalonamento.

**Stack:** Python stdlib (3.10 a 3.13) em `agent-system/scripts/`; testes são funções `test_*` em `agent-system/tests/test_*.py`, coletadas por `agent-system/scripts/test_system.py` (filtro por substring de `módulo.função`); helpers em `agent-system/tests/support.py`.

**Invariantes que continuam verdes:** `test_static` (lista exata de agentes), `test_registry_matches_agent_files`, `test_init_skill_list_matches_skills_folder`, as 8 evals atuais e o tamanho do bloco do `CLAUDE.md`.

---

### TASK-001: workflow.json e validate_workflow.py
- Requirements: REQ-001, REQ-002, REQ-003, REQ-005, REQ-006, REQ-007, REQ-008
- Acceptance: AC-001, AC-002, AC-003
- Files: agent-system/workflow.json, agent-system/scripts/validate_workflow.py, agent-system/scripts/workflow.py, agent-system/scripts/init_project.py, agent-system/tests/test_workflow_graph.py
- Out of scope: roteador (TASK-002), README e orquestrador (TASK-003)
- Stop if: `agent-system/workflow.json` já existir
- Depends on: none
- Verification: TEST-001
- Done when: TEST-001 passa, o grafo do plugin valida com exit 0 e cada erro da REQ-007 tem uma fixture que reprova
- Gate: check_proofs TEST-001
- Status: done

`workflow.py` concentra a leitura do grafo e a avaliação de condições, para o validador e o roteador não divergirem. `init_project.default_state()` ganha `revisions: {}` nesta task, porque a REQ-006 exige que `state_fields` e `default_state()` batam.

### TASK-002: next_step.py e contador de revisões
- Requirements: REQ-002, REQ-003, REQ-004, REQ-005, REQ-010, REQ-011
- Acceptance: AC-005, AC-006, AC-007, AC-008, AC-009
- Files: agent-system/scripts/next_step.py, agent-system/scripts/workflow.py, agent-system/scripts/lib.py, agent-system/tests/test_next_step.py
- Out of scope: integração com orquestrador e init (TASK-003)
- Stop if: `apply_semantic_state` deixar de ser chamado por `artifacts.record`
- Depends on: TASK-001
- Verification: TEST-002
- Done when: TEST-002 passa e um gate que falha três vezes leva ao nó de escalonamento
- Gate: check_proofs TEST-002
- Status: done

### TASK-003: diagrama, orquestrador, CLAUDE.md, init e eval
- Requirements: REQ-008, REQ-009, REQ-012, REQ-025
- Acceptance: AC-004, AC-010
- Files: agent-system/README.md, agents/orchestrator.md, agent-system/templates/CLAUDE.md, agent-system/scripts/init_project.py, agent-system/scripts/run_evals.py, agent-system/evals/fixtures/revision-escalation/expect.json, agent-system/docs/cli.md, agent-system/tests/test_workflow_integration.py
- Out of scope: docs de README.md, README.pt-BR.md e help (entram no fim da Fase 4, junto com os outros scripts)
- Stop if: o bloco do `CLAUDE.md` passar do limite de tamanho testado
- Depends on: TASK-002
- Verification: TEST-003, TEST-004
- Done when: TEST-003 e TEST-004 passam e a suíte inteira continua verde
- Gate: check_proofs TEST-003 TEST-004
- Status: done

## Checks

### TEST-001: grafo e validador
- Acceptance: AC-001, AC-002, AC-003
- Task: TASK-001
- Command: python agent-system/scripts/test_system.py test_workflow_graph
- Timeout: 300

### TEST-002: roteador e revisões
- Acceptance: AC-005, AC-006, AC-007, AC-008, AC-009
- Task: TASK-002
- Command: python agent-system/scripts/test_system.py test_next_step
- Timeout: 300

### TEST-003: integração e deriva do diagrama
- Acceptance: AC-004, AC-010
- Task: TASK-003
- Command: python agent-system/scripts/test_system.py test_workflow_integration
- Timeout: 300

### TEST-004: eval de escalonamento
- Acceptance: AC-009
- Task: TASK-003
- Command: python agent-system/scripts/run_evals.py revision-escalation
- Timeout: 300

---

## Fase 2: grafo de contexto (rastro de decisão)

### TASK-004: rastro nos vereditos e no record_event
- Requirements: REQ-013, REQ-014, REQ-016
- Acceptance: AC-011, AC-012
- Files: agent-system/scripts/artifacts.py, agent-system/scripts/validate_spec.py, agent-system/scripts/validate_tasks.py, agent-system/scripts/check_proofs.py, agent-system/scripts/validate_verification.py, agent-system/scripts/record_event.py, agent-system/tests/test_decision_trace.py
- Out of scope: a vista por feature (TASK-005)
- Stop if: `artifacts.record` passar a ser chamado fora dos quatro validadores
- Depends on: TASK-001
- Verification: TEST-005
- Done when: TEST-005 passa e o evento de cada validador tem `feature`, `node`, `inputs` e `fingerprint`, sem conteúdo de arquivo
- Gate: check_proofs TEST-005
- Status: done

`record()` só calcula o fingerprint quando o projeto tem opt-in e o chamador não passou um, para não custar nada fora de um projeto inicializado. `check_proofs.py` grava o fingerprint de antes da execução, o mesmo das provas. `record_event.py --node` recusa (exit 2) um id que não existe no `workflow.json`.

### TASK-005: timeline_view --feature
- Requirements: REQ-015, REQ-016
- Acceptance: AC-013
- Files: agent-system/scripts/timeline_view.py, agent-system/docs/cli.md, agent-system/tests/test_decision_trace.py
- Out of scope: métricas (Fase 3)
- Stop if: o formato atual de `timeline_view.py` sem `--feature` precisar mudar
- Depends on: TASK-004
- Verification: TEST-006
- Done when: TEST-006 passa e a saída sem `--feature` continua igual
- Gate: check_proofs TEST-006
- Status: done

### TEST-005: rastro dos vereditos
- Acceptance: AC-011, AC-012
- Task: TASK-004
- Command: python agent-system/scripts/test_system.py test_decision_trace.test_verdict test_decision_trace.test_manual
- Timeout: 300

### TEST-006: vista por feature
- Acceptance: AC-013
- Task: TASK-005
- Command: python agent-system/scripts/test_system.py test_decision_trace.test_feature_view
- Timeout: 300

---

## Fase 3: métricas por nó

Resposta à pergunta aberta sobre tokens: o `SubagentStop` do Claude Code traz `agent_transcript_path`, o transcript do próprio subagente. As linhas `assistant` desse JSONL têm `message.usage` com `input_tokens`, `output_tokens`, `cache_read_input_tokens` e `cache_creation_input_tokens`, e a mesma mensagem aparece em várias linhas com o mesmo `message.id` (conferido num transcript local, só nomes de campo). O hook soma o último `usage` de cada `id`. O formato do transcript não é documentado como contrato, então a leitura é best-effort: qualquer erro, arquivo acima de 50 MB ou caminho fora de uma pasta `subagents/` deixa o evento sem tokens, e o relatório mostra `unavailable`. O Cursor não traz uso no payload e fica sempre `unavailable`. O `tool_response` do `PostToolUse` do Agent tem `usage`, mas só da última requisição, então não serve como total.

### TASK-006: tokens do subagente no hook
- Requirements: REQ-018, REQ-016
- Acceptance: AC-015
- Files: agent-system/scripts/hook.py, agent-system/tests/test_metrics.py
- Out of scope: o relatório (TASK-007)
- Stop if: o hook passar de 20 s com um transcript grande no teste
- Depends on: none
- Verification: TEST-007
- Done when: TEST-007 passa e o evento `SUBAGENT_STOPPED` tem só números de tokens, sem texto do transcript
- Gate: check_proofs TEST-007
- Status: done

### TASK-007: metrics.py
- Requirements: REQ-017, REQ-018, REQ-019
- Acceptance: AC-014, AC-015
- Files: agent-system/scripts/metrics.py, agent-system/scripts/init_project.py, agent-system/docs/cli.md, agent-system/tests/test_metrics.py
- Out of scope: custo em dinheiro, gráficos
- Stop if: o relatório precisar de dado que a timeline não tem
- Depends on: TASK-006
- Verification: TEST-008
- Done when: TEST-008 passa e `metrics.py` não altera nenhum arquivo
- Gate: check_proofs TEST-008
- Status: done

`--feature` filtra a seção de features e limita os agentes ao intervalo entre o primeiro e o último evento daquela feature, porque os eventos de subagente não carregam o slug.

### TEST-007: tokens no hook
- Acceptance: AC-015
- Task: TASK-006
- Command: python agent-system/scripts/test_system.py test_metrics.test_hook
- Timeout: 300

### TEST-008: relatório de métricas
- Acceptance: AC-014, AC-015
- Task: TASK-007
- Command: python agent-system/scripts/test_system.py test_metrics.test_report
- Timeout: 300

---

## Fase 4: lições globais

### TASK-008: escopo global no lessons.py
- Requirements: REQ-020, REQ-021, REQ-022, REQ-024
- Acceptance: AC-016, AC-017
- Files: agent-system/scripts/lessons.py, agent-system/scripts/lib.py, agent-system/scripts/init_project.py, agent-system/tests/test_global_lessons.py
- Out of scope: injeção na sessão (TASK-009)
- Stop if: o formato de `lessons.json` do projeto precisar mudar
- Depends on: none
- Verification: TEST-009
- Done when: TEST-009 passa e o ciclo de vida das lições do projeto continua igual
- Gate: check_proofs TEST-009
- Status: done

O arquivo global guarda só o texto da lição, sem o nome ou o caminho do projeto de origem. `global_lessons` entra em `USER_LAYOUT_KEYS` para sobreviver a um novo init. Com `"global_lessons": false`, toda operação `--scope global` e o `promote` terminam com exit 2.

### TASK-009: injeção na sessão e skill lessons
- Requirements: REQ-023, REQ-024
- Acceptance: AC-018
- Files: agent-system/scripts/lib.py, agent-system/scripts/hook.py, skills/lessons/SKILL.md, agent-system/tests/test_global_lessons.py
- Out of scope: sincronização entre máquinas
- Stop if: o contexto da sessão passar do limite de 900 caracteres do hook
- Depends on: TASK-008
- Verification: TEST-010
- Done when: TEST-010 passa
- Gate: check_proofs TEST-010
- Status: done

### TASK-010: documentação de usuário
- Requirements: REQ-025
- Acceptance: AC-019
- Files: README.md, README.pt-BR.md, skills/help/SKILL.md, agent-system/README.md, agent-system/docs/cli.md, agent-system/tests/test_workflow_integration.py
- Out of scope: tradução das docs técnicas
- Stop if: nenhum
- Depends on: TASK-009
- Verification: TEST-011
- Done when: TEST-011 passa, a suíte inteira e as evals passam
- Gate: check_proofs TEST-011
- Status: done

### TEST-009: escopo global e filtro de vazamento
- Acceptance: AC-016, AC-017
- Task: TASK-008
- Command: python agent-system/scripts/test_system.py test_global_lessons.test_promote test_global_lessons.test_leak
- Timeout: 300

### TEST-010: injeção e precedência
- Acceptance: AC-018
- Task: TASK-009
- Command: python agent-system/scripts/test_system.py test_global_lessons.test_session
- Timeout: 300

### TEST-011: docs citam os scripts novos
- Acceptance: AC-019
- Task: TASK-010
- Command: python agent-system/scripts/test_system.py test_workflow_integration.test_docs
- Timeout: 300
