# Contratos de handoff

Todo handoff entre agentes usa um bloco `handoff` em YAML simples (chave: valor e listas). Sem relatório livre. O que já está em arquivo é citado pelo caminho, não copiado.

Entrada (o orchestrator envia):

```yaml
handoff: in
agent: implementer
feature: reset-password        # slug comum a spec, tasks, reviews e security
task: TASK-001
requirements: [REQ-001]
acceptance: [AC-001]
verification: [TEST-001]
risk: {complexity: M, security: LOW}
artifacts: [docs/specs/reset-password.md, docs/tasks/reset-password.md]
files_allowed: [src/reset.py, tests/test_reset.py]
constraints: [no new dependency]
```

Saída (o agente devolve):

```yaml
handoff: out
agent: implementer
status: completed              # completed | blocked | failed | needs_decision
task: TASK-001
changed_files: [src/reset.py, tests/test_reset.py]
tests: [TEST-001]
evidence: [.cursor/agent-system/proofs/reset-password.json]
findings: []                   # IDs (FIND-NNN, SEC-NNN) ou "nenhum"
blockers: []
next_step: tester
```

Campos sem valor ficam como lista vazia. `needs_decision` nomeia a decisão em `blockers`.

## Por agente

### orchestrator
Entrada: pedido do usuário, `state.json`, `layout.json`. Saída para o usuário: classe, complexidade, risco, próximo agente e gate. Não recebe handoff de outro orchestrator.

### planner
Entrada: intenção, classificação, risco, caminhos do layout. Saída: `artifacts` (spec, ADR, tasks), lista de TASK com dependências, resultado de `validate_spec.py` e `validate_tasks.py`, decisões pendentes em `blockers`.

### implementer
Entrada: uma `task` com `requirements`, `acceptance`, `verification` e `files_allowed`. Saída: `changed_files`, `tests` rodados, comandos e resultado; escopo novo vai em `blockers` com `status: needs_decision`.

### tester
Entrada: `feature`, `task` ou lista de TEST. Saída: um relatório por TEST (formato em `agents/tester.md`), `evidence` com o JSON do `check_proofs.py`, e a classificação de cada falha: aplicação, teste ou ambiente.

### reviewer
Entrada: `feature`, `artifacts`, `evidence`, diff. Saída: `status` PASS, PASS_WITH_WARNINGS ou FAIL; caminho de `<reviews_dir>/<slug>.md`; `findings` com FIND-NNN; resultado da Verification Audit.

### debugger
Entrada: sintoma, comando ou passos, log. Saída: reprodução, causa com evidência, correção aplicada ou proposta, teste de regressão (TEST-NNN quando houver plano).

### security-reviewer
Entrada: escopo (feature ou repositório), `changed_files`, `risk`, gatilhos. Saída: caminho do relatório, `status`, `findings` com SEC-NNN e contagem por severidade. Não corrige.
