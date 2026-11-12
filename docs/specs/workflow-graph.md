---
status: approved
complexity: XL
security_risk: LOW
security_triggers: file_system
approved_by: brunoleocam
---

# Spec: grafo de workflow declarado (execução, contexto, métricas e memória global)

Problema: o fluxo do Workbench existe como prosa. A tabela adaptativa de `agents/orchestrator.md` e o diagrama de `agent-system/README.md` são interpretados por um LLM a cada pedido, então o caminho pode variar entre sessões, os pontos de decisão humana dependem de o agente lembrar deles, e o ciclo "gate falha → implementer → tester → reviewer" não tem limite. A timeline registra eventos, mas não liga um veredito aos artefatos e ao estado do código que o produziram. O custo por agente não é medido. As lições ficam só por projeto, então uma preferência que vale em todos os projetos precisa ser ensinada de novo em cada um.

Resultado: um grafo de workflow declarado em JSON, validado por script e por teste, com nós de agente, de script e de decisão humana, arestas condicionais, paralelismo explícito e teto de revisões. Um roteador determinístico diz o próximo nó a partir do estado. Um rastro de decisão por feature liga cada veredito aos artefatos lidos e ao fingerprint. Um relatório de métricas por nó mostra tempo, contagem e revisões. Uma camada opcional de lições globais, confirmadas só pelo usuário, complementa as lições do projeto.

Origem: conceitos de "graph engineering" (grafo de execução, grafo de contexto com rastros de decisão, procedimentos virando script, pontos humanos declarados, teto em loops). Nenhum texto de terceiros é copiado.

Fases de entrega (cada fase fecha com a suíte verde e pode ser revisada sozinha):

1. Grafo de execução: REQ-001 a REQ-012.
2. Grafo de contexto: REQ-013 a REQ-016.
3. Métricas por nó: REQ-017 a REQ-019.
4. Lições globais: REQ-020 a REQ-024.

## Requirements

### REQ-001: Arquivo do grafo
THE SYSTEM SHALL oferecer `agent-system/workflow.json` com `version`, `start`, uma lista `nodes`, uma lista `edges`, um objeto `limits` e um objeto `state_fields`. Cada nó tem `id`, `kind` (`agent`, `script` ou `human`) e `description`; um nó `agent` tem `agent`; um nó `script` tem `script`; um nó `human` tem `question`.

### REQ-002: Arestas condicionais
THE SYSTEM SHALL aceitar em cada aresta `from`, `to` e um `when` opcional com as chaves `class` (lista de classes da regra `01`), `complexity_min`, `complexity_max`, `security_min`, `security_max`, `interface` (`new`, `existing` ou `none`) e `design_approved` (booleano), e um `on` opcional (`pass`, `fail` ou `escalate`) fora do `when`. Uma aresta sem `when` vale para qualquer contexto; uma aresta sem `on` vale para qualquer resultado. Todas as chaves de um `when` precisam valer ao mesmo tempo. Quando várias arestas fora de grupo valem, a primeira na ordem do arquivo vence.

### REQ-003: Paralelismo explícito
WHERE várias arestas saem do mesmo nó com o mesmo `group`, THE SYSTEM SHALL tratá-las como fan-out: os destinos cujas condições valem rodam em paralelo, e o nó indicado em `join` só é alcançado quando todos eles terminaram.

### REQ-004: Teto de revisões
THE SYSTEM SHALL ler `limits.max_revisions` (inteiro de 1 a 10, padrão 3). WHEN o gate de uma feature falha `max_revisions` vezes, THE SYSTEM SHALL seguir a aresta `on: escalate` para um nó `human`, em vez de voltar ao implementer.

### REQ-005: Nós de decisão humana
THE SYSTEM SHALL declarar como nós `human` no mínimo: aprovação da spec, decisão de arquitetura (ADR), escolha da direção de design, aprovação do `DESIGN.md`, aceite de risco residual, escalonamento por teto de revisões e autorização de commit e push.

### REQ-006: Dono de cada campo do estado
THE SYSTEM SHALL declarar em `state_fields` cada chave de `default_state()` em `init_project.py` com a lista de escritores permitidos (nomes de script ou `hook`). Uma chave de `default_state()` ausente em `state_fields`, ou uma entrada em `state_fields` que não existe em `default_state()`, é erro.

### REQ-007: Validador do grafo
THE SYSTEM SHALL oferecer `agent-system/scripts/validate_workflow.py`, só com stdlib, que termina com exit 0 quando o grafo é válido, 1 quando há erro de estrutura e 2 quando o arquivo falta ou não é JSON. Erros de estrutura: id de nó repetido; aresta para nó inexistente; `start` inexistente; nó inalcançável a partir de `start`; agente de `agents.json` com `scope: user` (exceto `orchestrator`) sem nó; nó `agent` cujo agente não está em `agents.json`; nó `script` cujo arquivo não existe em `agent-system/scripts/`; nó de gate (`validate_verification.py`) sem aresta `on: fail` ou sem aresta `on: escalate`; ciclo formado só por nós `agent` (todo ciclo precisa passar por um nó `script` ou `human`); destino de um `group` sem aresta para o `join`; `group` sem `join`; violação da REQ-006. Aceita `--json`.

### REQ-008: Visualização
WHEN `validate_workflow.py --mermaid` roda sobre um grafo válido, THE SYSTEM SHALL imprimir um diagrama Mermaid `flowchart` com um nó por nó do grafo (forma distinta para `agent`, `script` e `human`) e uma seta por aresta, com o `when` resumido no rótulo.

### REQ-009: Diagrama versionado sem deriva
THE SYSTEM SHALL manter em `agent-system/README.md`, entre os marcadores `<!-- workflow:begin -->` e `<!-- workflow:end -->`, o Mermaid gerado pela REQ-008. Um teste SHALL falhar quando o bloco diverge da saída atual de `--mermaid`.

### REQ-010: Roteador determinístico
THE SYSTEM SHALL oferecer `agent-system/scripts/next_step.py` que recebe `--from <nó>`, `--class`, `--complexity`, `--security`, opcionalmente `--feature <slug>`, `--interface` e `--design-approved`, e `--result pass|fail|escalate` (padrão `pass`), e imprime em JSON `next` (lista de ids de nó), `kind` de cada um, `parallel` (booleano), `join` quando houver, `reason` (as condições que valeram) e, para nó `human`, `status: needs_decision` e `question`. Um nó sem arestas de saída é terminal e devolve `next` vazio com `status: done`. Uma condição que depende de um argumento não informado é erro de argumento. Exit 0 com um próximo nó ou nó terminal, 1 quando o nó tem arestas mas nenhuma vale, 2 com argumento ou grafo inválido.

### REQ-011: Contador de revisões
WHEN `validate_verification.py` termina com exit 1 para uma feature, THE SYSTEM SHALL incrementar `state.json → revisions.<slug>`. WHEN termina com exit 0, THE SYSTEM SHALL zerar esse contador. `next_step.py --from gate --result fail --feature <slug>` SHALL ler o contador para decidir entre `on: fail` e `on: escalate`.

### REQ-012: Orquestrador segue o grafo
THE SYSTEM SHALL fazer o `orchestrator` (e o bloco gerenciado do `CLAUDE.md`) consultar `next_step.py` em trabalho M ou maior para decidir o próximo nó, parar em todo nó `human` e repassar a `question` ao usuário. A tabela adaptativa SHALL continuar em `orchestrator.md` como resumo, e um teste SHALL verificar que cada agente citado na tabela tem nó no grafo. `init_project.py` SHALL copiar `workflow.json`, `validate_workflow.py` e `next_step.py` para o projeto.

### REQ-013: Rastro de decisão nos vereditos
WHEN `validate_spec.py`, `validate_tasks.py`, `check_proofs.py` ou `validate_verification.py` grava seu evento de conclusão numa feature, THE SYSTEM SHALL incluir no evento `feature`, `inputs` (caminhos relativos dos artefatos lidos, sem conteúdo), `fingerprint` (o do workspace no momento da decisão) e `node` (id do nó no grafo).

### REQ-014: Rastro manual
THE SYSTEM SHALL aceitar em `record_event.py` as opções `--inputs` (lista separada por vírgula) e `--node`, para que revisões, ADRs e decisões humanas registrem o mesmo rastro. Caminhos de segredo SHALL virar `[redacted-path]`, como já acontece com `--files`.

### REQ-015: Vista por feature
WHEN `timeline_view.py --feature <slug>` roda, THE SYSTEM SHALL mostrar em ordem cronológica só os eventos dessa feature, com nó, agente, resultado, entradas e fingerprint abreviado, e marcar quando o fingerprint de um veredito difere do veredito anterior (o código mudou entre as decisões).

### REQ-016: Rastro sem conteúdo
THE SYSTEM SHALL nunca gravar no rastro o conteúdo de arquivos, saída de testes além do que já é gravado hoje, ou texto de prompt.

### REQ-017: Relatório de métricas
THE SYSTEM SHALL oferecer `agent-system/scripts/metrics.py` que lê `.cursor/timeline/events.jsonl` e imprime por agente (nó `agent`): quantas execuções, duração total e mediana (pares `SUBAGENT_STARTED`/`SUBAGENT_STOPPED` da mesma sessão), caracteres de resposta, e por feature: revisões até o gate passar e quantos gates falharam. Aceita `--feature`, `--since <data ISO>` e `--json`.

### REQ-018: Tokens quando disponíveis
WHERE o payload do hook traz contagem de tokens de uso, THE SYSTEM SHALL gravar só os números (entrada, saída, cache) no evento `SUBAGENT_STOPPED` ou `AGENT_RESPONSE`, e `metrics.py` SHALL somá-los por agente. IF nenhum evento tem tokens, THEN o relatório SHALL mostrar `tokens: unavailable` em vez de zero.

### REQ-019: Métricas sem efeito no fluxo
THE SYSTEM SHALL tratar as métricas como leitura: `metrics.py` não altera `state.json`, a timeline nem nenhum artefato, e um evento malformado é ignorado e contado em `skipped`.

### REQ-020: Armazenamento global opcional
THE SYSTEM SHALL guardar lições globais em `~/.agent-workbench/lessons.json` (caminho sobrescrito por `AGENT_WORKBENCH_HOME`), com o mesmo formato das lições do projeto mais `scope: global`. O arquivo só é criado no primeiro uso de `--scope global`.

### REQ-021: Promoção só pelo usuário
THE SYSTEM SHALL criar lição global apenas por `lessons.py promote --id LESSON-NNN`, que copia uma lição confirmada do projeto para o arquivo global, ou por `lessons.py add --scope global` seguido de `confirm --scope global`. Um agente pode propor (`candidate`), mas só o usuário confirma ou promove.

### REQ-022: Sem vazamento entre projetos
WHEN uma lição é promovida ou confirmada como global, THE SYSTEM SHALL recusá-la (exit 1) se o texto contiver o caminho absoluto do projeto, o nome da pasta do projeto, um caminho absoluto qualquer, uma URL ou algo que pareça segredo.

### REQ-023: Injeção na sessão
WHEN a sessão começa num projeto inicializado, THE SYSTEM SHALL injetar até cinco títulos de lições confirmadas do projeto e até três globais, nessa ordem, dentro do limite de contexto atual do hook. WHERE uma lição global e uma do projeto têm o mesmo título normalizado, a do projeto vence.

### REQ-024: Desligar a camada global
WHERE `layout.json` tem `"global_lessons": false`, THE SYSTEM SHALL não ler nem injetar lições globais nesse projeto.

### REQ-025: Testes, evals e documentação
THE SYSTEM SHALL ter testes em `agent-system/tests` para cada script novo, uma fixture de eval que prova o escalonamento após `max_revisions`, e documentação em `agent-system/docs/cli.md`, `agent-system/README.md`, `README.md`, `README.pt-BR.md` e na skill `help`.

## Acceptance Criteria

### AC-001: Grafo do plugin é válido
- Requirements: REQ-001, REQ-005, REQ-006, REQ-007
Given o `agent-system/workflow.json` do plugin
When `validate_workflow.py` roda
Then o exit code é 0, cada agente de `agents.json` exceto `orchestrator` tem nó, e os sete nós `human` da REQ-005 existem.

### AC-002: Cada erro de estrutura reprova
- Requirements: REQ-007
Given uma fixture para cada erro listado na REQ-007
When `validate_workflow.py --json` roda em cada uma
Then o exit code é 1 e a saída nomeia o erro e o id envolvido; com o arquivo ausente ou JSON inválido o exit code é 2.

### AC-003: Dono de campo
- Requirements: REQ-006
Given um `state_fields` sem a chave `verification`, e outro com uma chave `foo` inexistente
When o validador roda
Then os dois casos reprovam citando a chave.

### AC-004: Mermaid e deriva
- Requirements: REQ-008, REQ-009
Given o grafo do plugin
When `validate_workflow.py --mermaid` roda e o bloco de `agent-system/README.md` é comparado
Then a saída começa com `flowchart`, tem um nó por nó do grafo e é idêntica ao bloco; alterar uma aresta sem regerar o bloco faz o teste falhar.

### AC-005: Roteamento por complexidade
- Requirements: REQ-002, REQ-010
Given uma FEATURE M com segurança LOW
When `next_step.py --from classify --class FEATURE --complexity M --security LOW` roda
Then `next` é o nó do planner; com `--complexity S` o próximo é o implementer direto.

### AC-006: Segurança alta entra no fan-out
- Requirements: REQ-003, REQ-010
Given uma FEATURE M com segurança HIGH depois do tester
When `next_step.py --from proofs --result pass ...` roda
Then `parallel` é verdadeiro, `next` contém reviewer e security-reviewer, e `join` é o gate; com segurança LOW, `next` contém só o reviewer.

### AC-007: Interface nova vai ao designer
- Requirements: REQ-002, REQ-010
Given uma FEATURE M com `--interface new` e sem `--design-approved`
When o roteador roda a partir do planner
Then o próximo nó é o designer, seguido do nó `human` de escolha de direção.

### AC-008: Nó humano para o fluxo
- Requirements: REQ-005, REQ-010
Given o próximo nó é a aprovação da spec
When `next_step.py` responde
Then a saída tem `status: needs_decision` e uma `question` não vazia.

### AC-009: Escalonamento após o teto
- Requirements: REQ-004, REQ-011
Given `max_revisions` 3 e uma feature cujo gate falhou três vezes
When `next_step.py --from gate --result fail --feature <slug>` roda
Then o próximo nó é o nó `human` de escalonamento; depois de duas falhas, o próximo é o implementer; depois de um gate que passa, `revisions.<slug>` volta a 0.

### AC-010: Orquestrador e init
- Requirements: REQ-012
Given o plugin e um projeto inicializado
When `orchestrator.md`, o bloco do `CLAUDE.md` e `.cursor/agent-system/scripts/` são lidos
Then os dois textos mandam consultar `next_step.py` em M ou maior e parar em nó `human`, cada agente da tabela tem nó no grafo, e `workflow.json`, `validate_workflow.py` e `next_step.py` estão no projeto.

### AC-011: Veredito com rastro
- Requirements: REQ-013, REQ-016
Given uma feature com spec, tasks e proofs
When `validate_verification.py --feature <slug>` roda
Then o evento gravado tem `feature`, `node`, `inputs` com os caminhos da spec, tasks, review e proofs, e `fingerprint`, e nenhum campo tem conteúdo de arquivo.

### AC-012: Rastro manual com redação
- Requirements: REQ-014
Given `record_event.py --event REVIEW_COMPLETED --feature x --node review --inputs docs/reviews/x.md,.env`
When o evento é gravado
Then `inputs` contém `docs/reviews/x.md` e `[redacted-path]`.

### AC-013: Vista por feature marca mudança de código
- Requirements: REQ-015
Given dois vereditos da mesma feature com fingerprints diferentes e um evento de outra feature
When `timeline_view.py --feature <slug>` roda
Then só aparecem os eventos da feature, em ordem, e o segundo veredito está marcado como "code changed".

### AC-014: Métricas por agente e feature
- Requirements: REQ-017, REQ-019
Given uma timeline de fixture com dois pares start/stop do implementer, um do reviewer, uma linha malformada e duas falhas de gate antes de um gate que passa
When `metrics.py --json` roda
Then o implementer tem 2 execuções com a duração somada correta, a feature tem 2 revisões, `skipped` é 1, e `state.json` e a timeline não mudam.

### AC-015: Tokens ausentes e presentes
- Requirements: REQ-018
Given uma timeline sem tokens e outra com tokens em `SUBAGENT_STOPPED`
When `metrics.py` roda em cada uma
Then a primeira mostra `tokens: unavailable` e a segunda mostra as somas por agente.

### AC-016: Promoção global
- Requirements: REQ-020, REQ-021
Given `AGENT_WORKBENCH_HOME` apontando para uma pasta temporária vazia e uma lição confirmada no projeto
When `lessons.py promote --id LESSON-001` roda
Then `lessons.json` global é criado com a lição e `scope: global`; promover uma lição `candidate` falha com exit 1.

### AC-017: Recusa de vazamento
- Requirements: REQ-022
Given lições que citam o caminho do projeto, o nome da pasta do projeto, `C:/x/y`, `https://exemplo.com` e `token=abc123`
When cada uma é promovida
Then todas são recusadas com exit 1 e o arquivo global não muda.

### AC-018: Injeção e precedência
- Requirements: REQ-023, REQ-024
Given seis lições confirmadas no projeto, quatro globais e uma global com o mesmo título de uma do projeto
When o hook `sessionStart` roda
Then o contexto tem cinco do projeto e até três globais, sem repetir o título duplicado; com `"global_lessons": false` no `layout.json`, nenhuma global aparece.

### AC-019: Suíte, eval e docs
- Requirements: REQ-025
Given a implementação completa
When `python agent-system/scripts/test_system.py` e `python agent-system/scripts/run_evals.py` rodam
Then os dois passam, a eval de escalonamento existe, e os cinco documentos da REQ-025 citam os três scripts novos.

## Assumptions

- O orquestrador continua sendo um LLM. O grafo e o roteador tornam o caminho determinístico e verificável, mas não impedem o agente de ignorá-los; o que impede é o gate (`validate_verification.py`), como hoje.
- `next_step.py` não executa nós. Ele só diz qual é o próximo; quem executa é o orquestrador.
- O fingerprint usado no rastro é o de `check_proofs.py --fingerprint`, já existente.
- O Claude Code entrega números de uso de tokens em algum payload de hook ou transcript acessível ao hook; o Cursor provavelmente não. A REQ-018 cobre os dois casos.
- `~/.agent-workbench/` é gravável no Windows e no Linux; os testes usam `AGENT_WORKBENCH_HOME` e nunca o home real.

## Constraints

- Só stdlib Python, 3.10 a 3.13, Windows e Linux.
- Nenhum framework de grafo (LangGraph ou similar). O grafo é um JSON lido pelos scripts do harness.
- Projetos já inicializados continuam funcionando sem rodar o init de novo; `revisions` entra em `default_state()` e chega pelo `migrate_state` existente.
- Hooks continuam fail-open e dentro do timeout de 20 s.
- O conteúdo de arquivos e prompts nunca vai para a timeline, o rastro ou as métricas.

Fora de escopo: execução automática do grafo (um runner que chama agentes sozinho), editor visual do grafo, grafos diferentes por projeto (o projeto usa o do plugin; sobrescrita por projeto fica para depois), métricas de custo em dinheiro, sincronização de lições globais entre máquinas.

## Open Questions

- [x] Tokens no Claude Code: o `SubagentStop` traz `agent_transcript_path`; as linhas `assistant` desse transcript têm `message.usage`. O hook soma o último uso de cada `message.id` (best-effort, porque o formato do transcript não é contrato). O `usage` do `PostToolUse` do Agent cobre só a última requisição e não serve como total. Cursor: `unavailable`.
- [x] Grafo por projeto: fica fora de escopo nesta entrega (spec aprovada sem pedir a inclusão).

## Decisions

- Escopo completo em quatro fases (escolha do usuário em 2026-11-12), complexidade XL.
- O grafo é dado (JSON) e não prosa, para ser validado por script e desenhado; a prosa do orquestrador passa a apontar para ele.
- O roteador só recomenda o próximo nó; o gate continua sendo a única barreira dura.
- Esclarecimentos de desenho (2026-11-12, antes das tasks, sem mudar o escopo aprovado): `complexity_max` e `security_max` para os caminhos XS/S sem depender da ordem; primeira aresta válida vence fora de grupo; `--result escalate` para o agente sinalizar decisão humana (por exemplo, o planner com uma decisão de arquitetura); ciclos exigem um nó `script` ou `human`, porque aprovações rejeitadas voltam ao planner sem passar pelo gate; só agentes `scope: user` são obrigatórios no grafo, para que agentes criados por `/create-agent` no projeto não reprovem o validador.
- Ajustes pela revisão independente (2026-11-12, FIND-001 a FIND-006 de `docs/reviews/workflow-graph.md`), sem mudar o escopo: `--interface` não tem padrão, e uma aresta que depende dele sem o argumento é erro (REQ-010), para que um UI novo não pule o design por omissão; o contador de revisões só muda com o evento do gate (`node: gate`, que `record_event.py` não pode gravar) e volta a zero quando o usuário responde ao escalonamento (evento com `--node escalate`); `design_review` ganhou a aresta `escalate` para `accept_risk`, e `accept_risk` e `escalate` levam UI nova ao `frontend_implement`; o filtro de vazamento passou a recusar `~/`, caminho UNC, `www.`, domínio com caminho e variações do nome do projeto.
- Lições globais são opt-out por projeto, só criadas por ação do usuário, e passam por um filtro de vazamento mais estrito que o das lições do projeto.
