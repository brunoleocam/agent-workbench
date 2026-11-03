---
status: approved
complexity: XL
security_risk: MEDIUM
security_triggers: command_execution, file_system, secrets_in_logs
approved_by: brunoleocam
---

# Spec: evolução do harness (0.2.0)

Problema: as garantias do fluxo spec-driven vivem só em instruções Markdown. Nada verifica de forma objetiva se requisito tem critério, se critério tem teste, se o teste rodou contra o código atual e se a revisão terminou.

Resultado: validadores determinísticos (stdlib), camada de segurança proporcional ao risco, auditoria de verificação no reviewer, lições confirmadas pelo usuário e evals reproduzíveis dos gates. Tudo isso sem burocracia para XS e S e sem quebrar projetos já inicializados.

Formato dos artefatos: [`agent-system/docs/artifacts.md`](../../agent-system/docs/artifacts.md). CLI: [`agent-system/docs/cli.md`](../../agent-system/docs/cli.md).

## Requirements

### REQ-001: Identificadores rastreáveis
THE SYSTEM SHALL reconhecer os identificadores REQ, AC, ADR, TASK, TEST, PROOF, FIND e SEC em artefatos Markdown, cada um com três ou mais dígitos, definidos por um título que começa com o ID.

### REQ-002: Validação estrutural da spec
WHEN `validate_spec.py` roda sobre uma spec, THE SYSTEM SHALL reportar PASS, WARN e FAIL para campos obrigatórios, IDs duplicados, AC sem REQ, AC com REQ inexistente, REQ sem AC, premissas e restrições ausentes, ambiguidades em aberto, ADR citado sem arquivo e aprovação exigida.

### REQ-003: Validação estrutural das tarefas
WHEN `validate_tasks.py` roda, THE SYSTEM SHALL reprovar tarefa duplicada, sem requisito ou critério, sem verificação, sem critério de conclusão, com dependência inexistente ou circular, bloqueada sem dependência e concluída sem evidência.

### REQ-004: Execução de provas
WHEN `check_proofs.py` executa os TEST de uma feature, THE SYSTEM SHALL gravar, por TEST, stdout, stderr, exit code real, horário, tarefa, critérios, status e fingerprint do workspace, sem `shell=True` por padrão, com timeout e sem instalar dependências.

### REQ-005: Política de comandos
IF o executável de um TEST não está na lista permitida, ou o comando usa um subcomando conhecido de instalação, publicação ou remoção de pacotes (melhor esforço, por nome; não é sandbox), ou executa código inline (`python -c`, `node -e` e equivalentes, também atrás de wrappers como `uv run`; melhor esforço por análise de argumentos), ou passa metacaractere do `cmd.exe` para um `.cmd`/`.bat` no Windows, THEN THE SYSTEM SHALL recusar a execução e marcar REFUSED. Código inline só roda com `--allow-inline` na CLI, por autorização do usuário. Shell só roda com `Shell: yes` no artefato e `--allow-shell` na CLI.

### REQ-006: Fingerprint do workspace
THE SYSTEM SHALL calcular um fingerprint com HEAD, arquivos modificados e não rastreados (conteúdo), excluindo `.cursor/`, caches e os diretórios de documentação do harness, sem exigir commit.

### REQ-007: Gate de verificação
WHEN `validate_verification.py` roda, THE SYSTEM SHALL reprovar a conclusão se faltar TEST para AC, prova para TEST obrigatório, prova PASS, prova do fingerprint atual, review aprovada (M ou maior), revisão de segurança quando o risco for HIGH ou CRITICAL, fingerprint de relatório obrigatório igual ao workspace atual (comparação exata; ausente reprova), ou se houver achado bloqueante aberto ou risco aceito sem justificativa.

### REQ-008: Respeito ao layout
THE SYSTEM SHALL resolver os caminhos de spec, tasks, testes, reviews e segurança a partir de `.cursor/agent-system/layout.json` (com `overrides`), caindo para `docs/...` só quando o layout não informa, e recusar caminho fora da raiz do projeto.

### REQ-009: Contrato de CLI
THE SYSTEM SHALL oferecer em todos os validadores `--root`, `--feature` ou caminhos explícitos, `--json`, `--strict` e exit codes 0 (sucesso), 1 (gate reprovado) e 2 (erro de configuração, argumento ou execução).

### REQ-010: EARS no planner
THE SYSTEM SHALL recomendar EARS para requisito comportamental no planner e na rule `02`, aceitando linguagem natural estruturada para requisito técnico, sem tratar a gramática como prova de correção.

### REQ-011: Segurança no ciclo
THE SYSTEM SHALL oferecer a rule `08-security-engineering`, a skill `security-best-practices` com referências por stack carregadas sob demanda, a skill `/security-review` que gera relatório antes de qualquer correção, e o agente `security-reviewer` registrado.

### REQ-012: Classificação de risco
WHEN o orchestrator classifica um pedido, THE SYSTEM SHALL avaliar risco de segurança (NONE, LOW, MEDIUM, HIGH, CRITICAL) separado da complexidade, com gatilhos documentados, e o init SHALL detectar frameworks e superfícies de ataque.

### REQ-013: Auditoria de verificação
THE SYSTEM SHALL exigir do reviewer uma Verification Audit que questiona se cada teste prova o critério, e do tester o relatório por TEST com REQ, AC, comando, resultado esperado e real, exit code e status.

### REQ-014: Lições aprendidas
THE SYSTEM SHALL manter lições em `lessons.json` (fonte de verdade) com `add`, `list`, `confirm`, `reject` e `render`, recusar duplicata e texto com segredo, e injetar no início da sessão apenas lições confirmadas.

### REQ-016: Evals
THE SYSTEM SHALL oferecer fixtures em `agent-system/evals/fixtures/` com runner determinístico que prova o comportamento dos gates, sem API paga e sem avaliar comportamento do modelo.

### REQ-017: Eventos e estado
THE SYSTEM SHALL aceitar os eventos de validação, prova, verificação, segurança e lição na timeline e atualizar o estado sem apagar campos existentes.

### REQ-018: Hooks honestos
WHEN o hook classifica um comando de teste pelo texto da saída, THE SYSTEM SHALL marcar o evento como inferido, nunca como resultado determinístico, e continuar fail-open sem gravar segredos.

### REQ-019: Init compatível
WHEN `/init-agent-system` roda em projeto novo, existente ou Cloud, THE SYSTEM SHALL copiar os scripts novos, preservar arquivos, estado e overrides do usuário, completar campos novos do estado e não criar documento vazio.

### REQ-020: Contratos de handoff
THE SYSTEM SHALL definir um bloco de handoff padronizado de entrada e saída para cada agente.

### REQ-021: Documentação fiel
THE SYSTEM SHALL documentar arquitetura, camadas, agentes, skills, comandos, validadores, segurança, lições, evals, hooks e limitações, sem declarar o que não está implementado e testado.

## Acceptance Criteria

### AC-001: IDs e blocos
- Requirements: REQ-001
Dado um Markdown com títulos `### REQ-001: x` e campos `- Requirements: REQ-001`, o parser devolve os blocos com ID, tipo, linha e campos canônicos.

### AC-002: Spec válida e inválida
- Requirements: REQ-002, REQ-009
Spec válida sai com 0. ID duplicado ou AC apontando REQ inexistente sai com 1 e mensagem `[FAIL]`. REQ sem AC gera `[WARN]` e vira FAIL com `--strict`.

### AC-003: Tarefas inválidas
- Requirements: REQ-003
Tarefa sem critério, com dependência inexistente, com ciclo, bloqueada sem dependência ou concluída sem prova sai com 1 e nomeia a tarefa.

### AC-004: Provas reais
- Requirements: REQ-004
Comando com exit 0 vira PASS, exit diferente de 0 vira FAIL, timeout vira TIMEOUT e executável ausente vira ERROR, sempre com o exit code real e o JSON de provas gravado.

### AC-005: Comandos recusados
- Requirements: REQ-005
Executável fora da lista, `npm install`, `python -m pip install`, `python -c` e `uv run python -c` viram REFUSED sem executar; `pytest`, `python -m pytest` e `python tests/x.py` continuam permitidos; com `--allow-inline`, código inline roda.

### AC-006: Fingerprint muda com o código
- Requirements: REQ-006
Editar um arquivo de código depois da prova muda o fingerprint; editar a doc do harness não muda.

### AC-007: Gate de verificação
- Requirements: REQ-007
Prova ausente, prova obsoleta, review ausente, achado bloqueante aberto ou risco aceito sem justificativa reprovam; o caso completo passa e grava VERIFICATION_COMPLETED.

### AC-008: Layout e path traversal
- Requirements: REQ-008
Com `layout.json` apontando outra pasta, os validadores leem dali. `--feature ../x` e caminho fora da raiz saem com 2.

### AC-009: Planner e rule 02 citam EARS
- Requirements: REQ-010
`agents/planner.md` e `rules/02-spec-driven-development.mdc` descrevem EARS, IDs e quando não usar.

### AC-010: Camada de segurança presente e registrada
- Requirements: REQ-011
Existem a rule 08, as duas skills com frontmatter válido, as dez referências com fontes e data de revisão, e o agente `security-reviewer` no registro e no orchestrator.

### AC-011: Risco e stack
- Requirements: REQ-012
O init detecta FastAPI, Express, Laravel, ASP.NET Core e Spring nas fixtures e lista superfícies como auth, upload e pagamento. `security_risk` inválido na spec reprova; HIGH exige revisão de segurança no gate.

### AC-012: Tester e reviewer atualizados
- Requirements: REQ-013
`agents/tester.md`, `agents/reviewer.md` e `skills/code-review/SKILL.md` contêm o relatório por TEST e a Verification Audit.

### AC-013: Lições
- Requirements: REQ-014
`add` cria candidata, duplicata e segredo saem com 1, `confirm` muda o status, `render` gera LESSONS.md e o sessionStart cita só confirmadas.

### AC-015: Evals determinísticas
- Requirements: REQ-016
`run_evals.py` roda todas as fixtures com resultado esperado e sai com 0; os TESTs das fixtures usam arquivos de teste, não código inline.

### AC-016: Eventos novos
- Requirements: REQ-017
`record_event.py` aceita os eventos novos e o estado ganha `verification` sem perder chaves antigas.

### AC-017: Hook inferido
- Requirements: REQ-018
Saída de teste capturada pelo hook gera evento com `inferred: true` e segredo na linha de comando não aparece na timeline.

### AC-018: Init sem sobrescrita
- Requirements: REQ-019
Reexecutar o init preserva estado, overrides e hooks; o estado antigo ganha as chaves novas; `--for-cloud` copia a rule 08 e o `security-reviewer`.

### AC-019: Handoff padronizado
- Requirements: REQ-020
`agent-system/docs/contracts.md` define o bloco e cada agente aponta para ele.

### AC-020: Docs batem com o código
- Requirements: REQ-021
README e `agent-system/README.md` listam só comandos e scripts que existem; a versão do manifest é 0.2.0.

## Assumptions

- Python 3.10 ou maior no `PATH`, como já exigido.
- Git é opcional. Sem git, o fingerprint usa o hash do conteúdo dos arquivos do projeto.
- O formato novo vale para specs novas. Specs antigas sem IDs não são validadas nem migradas.

## Constraints

- Só biblioteca padrão.
- Nenhum script faz push, commit, instalação ou chamada de rede.
- Hooks continuam fail-open.
- Nada de score de qualidade inventado.

## Deferred

Reconciliação com Minimum Effective Engineering (2026-11-03): adiados por não terem consumidor concreto nesta entrega, preservados fora do repositório e fáceis de reintroduzir.

- Métricas agregadas da timeline (`metrics.py`).
- Avaliação manual de agentes por cenários e rubricas (skill `/agent-evaluation`).

## Open Questions

- [x] Nome do agente de segurança: `security-reviewer`, porque `security-review` é subagent built-in do Cursor.
- [x] Verifier separado: não. O reviewer absorve a Verification Audit (ADR-0003).

## Decisions

- ADR-0001: formato dos artefatos rastreáveis.
- ADR-0002: provas, fingerprint e política de comandos.
- ADR-0003: papéis de verificação e segurança.
