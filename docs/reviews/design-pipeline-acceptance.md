# Ensaio de aceitação: pipeline de design (TASK-011)

Data: 2026-11-12. Projeto de exemplo: "Agenda Vet", app de agendamento para clínicas veterinárias pequenas, criado fora do repositório a partir de um `README.md` de três linhas. O usuário real respondeu à entrevista, escolheu a direção e aprovou o brief e o DESIGN.md. Os artefatos estão em [`agent-system/tests/samples/design-sample/`](../../agent-system/tests/samples/design-sample/).

**Como foi conduzido:** o plugin instalado na sessão era a versão 0.4.0, sem as skills e os agentes novos. Por isso o agente principal seguiu, ao pé da letra, os arquivos desta branch (`skills/design-*/SKILL.md`, `agents/frontend-implementer.md`, `agents/design-reviewer.md`), em vez de chamá-los como slash command e subagente. O hook do lint também não rodou nas edições, já que o hook ativo era o da 0.4.0. O lint foi rodado à mão em cada etapa. Falta ensaiar a mesma coisa com o plugin instalado desta branch, para confirmar o disparo das skills pela `description`, o roteamento do orchestrator e o hook.

## Resultado por critério

| AC | Resultado | O que aconteceu |
| --- | --- | --- |
| AC-001 | observado | Uma única mensagem com 4 perguntas (tarefa, tom, densidade, referências), cada uma com a opção recomendada marcada e de 2 a 3 opções em palavras leigas. Nenhum termo de design sem explicação. |
| AC-002 | observado | Público (recepcionista de clínica pequena), plataforma (web, computador da recepção) e idioma vieram do README; não houve pergunta sobre eles, e o brief os marca como `inferido`. |
| AC-003 | observado | `design/brief.md` com front matter `status`, todas as seções do modelo, marcação de origem em cada item e a tabela Keep / Change / Do not copy. |
| AC-004 | observado | Na primeira rodada o usuário respondeu "Não tenho referências", e o brief registrou "Sem referências; a direção parte só deste brief." Na correção do brief ele forneceu uma referência, e o brief foi refeito com ela. |
| AC-005 | observado | Matriz preenchida antes do HTML: A (linha do tempo, Baloo 2, creme quente, densidade 5), B (tabela, Fraunces, papel neutro com verde-azulado, 7), C (quadro por veterinário, Barlow Condensed, marinho escuro, 6). Cada par difere em 3 ou 4 dos 4 eixos; nenhum par difere só em cor. |
| AC-006 | observado | Os quatro HTML não têm `<script src>` nem `<img src>` externos; as fontes vêm do Google Fonts com fallback local. O lint não acusou nenhum P0 (`P0-FILLER` e `P0-PLACEHOLDER-CDN` incluídos). Em 320px nenhuma das três rola na horizontal. |
| AC-007 | observado | Depois das três prévias, o agente mostrou o índice, recomendou a A com o motivo ligado ao brief e parou. O `DESIGN.md` só foi criado depois da escolha. |
| AC-008 | observado | "Densidade 8" alterou só `a.html`: os hashes SHA-256 de `b.html`, `c.html` e `index.html` ficaram iguais, e o comentário da A passou a `density: 8`. |
| AC-009 | observado | Ao pedido "a tipografia da B com as cores da A", o agente explicou por que a serifa da B destoaria da Balcão e entregou uma única revisão da A: o nome do animal em Fraunces itálico, como terceira fonte restrita a esse lugar, com os títulos mantidos na fonte da A. As outras direções não foram alteradas. |
| AC-010 | observado | `DESIGN.md` com `status` e as 9 seções na ordem; a seção 1 traz a escolha distintiva e a seção 9, os 7 P0 do lint e o "Do not copy" do brief. |
| AC-011 | observado | Todo hex do `DESIGN.md` existe em `design/tokens.css` com o mesmo valor; o espaçamento está em múltiplos de 4px; são 3 famílias; os pares `-ink` vão de 5.18:1 a 7.77:1, e o foco sobre o fundo tem 6.14:1. Coberto também pelo TEST-015. |
| AC-012 | não ensaiado | O projeto não tinha `DESIGN.md` anterior, então a regra de não sobrescrever sem confirmação não foi exercitada. |
| AC-013 | observado | `design/pages/confirmar.md` troca o cartão com retrato por linhas compactas com fio, só na página Confirmar amanhã. `src/confirmar.html` segue a exceção; a direção A e o `DESIGN.md` continuam com a densidade geral. |
| AC-014 | observado | Um rascunho genérico de controle (hero centralizado e três cards "Rápido / Simples / Seguro"), escrito de propósito, passou no lint com zero achados, mas tirou postura 1, hierarquia 2, especificidade 1, contenção 2 e variedade 1 na `design-review`. A skill obrigou a revisar, e a segunda passada (a tela real) ficou com todos os eixos em 4. Foram 2 passadas, dentro do limite de 3. |
| AC-016 | observado | `src/confirmar.html` usa só `var(--...)` de `design/tokens.css`; o lint não acusou nenhum P1-RAW-COLOR nem P1-FONT-LITERAL. |
| AC-020 | observado | A tela cobre os estados vazio (tarde sem consultas), carregando ("Enviando…" com `aria-disabled`), erro (número com 10 dígitos, com causa e próximo passo) e sucesso (etiqueta "Confirmado", sem toast). Lint limpo, e em 320px nenhum botão quebra linha nem fica abaixo de 44px. Seguido o contrato do `frontend-implementer`, mas não executado como subagente. |
| AC-021 | observado | Numa cópia com `<h3>✨ Dica do dia</h3>` plantado, a revisão deu `status: FAIL` com FIND-001 (blocker, `controle/confirmar-defeito.html:85`, P0-EMOJI-ICON) e FIND-002 (minor, seção sem função). O hash do arquivo revisado não mudou. Seguido o contrato do `design-reviewer`, mas não executado como subagente. |

## Achados do ensaio

### FIND-001: P1-FONT-COUNT soma fontes de direções independentes
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lint_design.py (check_across_files)
- Evidence: `lint_design.py design/directions` reportou "Fourth font family 'source sans 3' (baloo 2, nunito sans, fraunces, source sans 3)" em `b.html`. Cada direção tem no máximo 2 famílias; a regra soma as três prévias como se fossem um só produto. A skill `design-directions` manda rodar o lint nessa pasta, então o aviso vai aparecer em quase todo ensaio.
- Recommendation: contar as famílias de cada arquivo de `design/directions/` separadamente.
- Resolution: feito em `lint_design.py` (`font_scope`), coberto por `test_design_lint_counts_fonts_per_direction` (TEST-005). `lint_design.py` nas direções da amostra passou a dar 0 achados.

### FIND-002: O lint não vê um layout genérico feito só com tokens
- Severity: minor
- Status: accepted
- Location: agent-system/scripts/lint_design.py
- Evidence: o rascunho de controle (hero centralizado, três cards iguais, "Começar", "com facilidade") teve zero achados. O plano previa isso: os sinais estruturais estão no `anti-slop.md` e na `design-review`, que pegaram o rascunho.
- Justification: detectar estrutura por regex daria muitos falsos positivos; a revisão em seis eixos é a camada certa para isso. O que fica registrado é a lição: lint limpo não significa design aprovado.

### FIND-003: Defeitos achados na própria geração, antes da entrega
- Severity: minor
- Status: resolved
- Location: agent-system/tests/samples/design-sample/design/directions/a.html
- Evidence: (1) "Esperando resposta" usava a mesma etiqueta verde de "Confirmado"; (2) em 320px a etiqueta passava da borda do card; (3) os rótulos das vagas quebravam em duas linhas em 320px (checklist, pergunta 12); (4) o título dizia "8 consultas", e eram 6. Os quatro foram pegos pela checagem no navegador e pela checklist da `design-review`, e corrigidos.
- Recommendation: nenhuma. Ficam como evidência de que a etapa de verificação no navegador e a checklist encontram defeito real.

## Ensaio 2 (realizado em 2026-11-12): com o plugin desta branch carregado

Conduzido numa sessão aberta com o plugin carregado de `C:/Dev/Agent Workbench` (branch atual no disco no momento do ensaio: `feat/workflow-graph`, não `feat/design-pipeline` — ver nota abaixo da tabela). Projetos de teste em `C:\Dev\ensaio2\` (`agenda-vet`, cópia da amostra com git e um commit; `projeto-vazio`; `projeto-vazio-2`, criado durante o ensaio para isolar o Caso 4/5 da padaria). Sanidade confirmada antes de começar: `agent-workbench:design` aparece na lista de skills e `agent-workbench:designer`, `agent-workbench:frontend-implementer`, `agent-workbench:design-reviewer` aparecem na lista de subagentes disponíveis.

Os subagentes reais do plugin fizeram o trabalho (não houve execução manual das skills pelo agente principal): `designer`, `frontend-implementer` e `design-reviewer` foram invocados via `Agent`/orchestrator e produziram os artefatos abaixo.

| AC | Resultado | Evidência |
| --- | --- | --- |
| AC-012 | observado (parcial) | Hash do `DESIGN.md` antes: `87DFB6D9...`. Pedido "mudar densidade para 5" via `/agent-workbench:design-system`: a skill leu o `DESIGN.md` existente e mostrou a proposta seção por seção (resumo, §1, §4, §6) **antes** de tocar em qualquer arquivo, pedindo confirmação explícita. O usuário real, neste ensaio, respondeu "Sim" (desviando do roteiro original de testar a recusa) — overwrite feito, e uma **segunda** confirmação foi exigida (status: draft → approved) antes de marcar aprovado. Hash final: `6330C1BF...`. Arquivo restaurado depois via `git checkout` (`git status` limpo, `git diff --stat` vazio contra HEAD). O caminho "recusa preserva o arquivo" (responder "não") **não foi exercitado**, por decisão do usuário em tempo real; o mecanismo de dois gates de confirmação foi observado funcionando no sentido contrário (aprovação). |
| AC-015 | observado | `/agent-workbench:design` em `agenda-vet`: a skill checou os critérios da tabela "Resume where it stopped" e disse em uma linha que discovery (`brief.md` approved), directions (a/b/c.html + direção "a" escolhida) e design system (`DESIGN.md` approved + `tokens.css`) já estavam prontos, e que nenhum relatório de review foi encontrado — começou pela revisão. O `design-reviewer` real (subagente) rodou sobre `src/confirmar.html`, escreveu `agenda-vet/docs/reviews/confirmar-design.md` (novo arquivo, `git status` confirma `??docs/`) com `status: FAIL`, lint 0 P0 mas 8 achados de conteúdo/contrato (FIND-001 bloqueador: o texto "3 de 6 confirmaram · faltam 3" não bate com as 6 linhas reais da tela, só 2 confirmadas). Nem a entrevista nem as direções foram refeitas. |
| AC-017 | observado | **Parte 1** (`projeto-vazio`, sem `DESIGN.md`): pedido "crie uma landing page para uma padaria de bairro" via `/agent-workbench:ui-ux` → a skill recomendou rodar `/design` antes e esperou a decisão do usuário (não construiu nada). **Parte 2** (`agenda-vet`, com `DESIGN.md` aprovado): pedido de troca de rótulo via `/agent-workbench:ui-ux` → seguiu direto, sem recomendar `/design`, delegado ao `frontend-implementer` que mudou só `src/confirmar.html:47` ("Enviar para os 3 que faltam" → "Confirmar os 3 que faltam"), usando só tokens já existentes; lint 0 P0/P1/P2; `git diff` confirma mudança de uma linha só. |
| AC-019 | observado | Orchestrator, em `projeto-vazio-2` (pasta nova, git inicializado, vazia), recebeu "quero a tela inicial de um app de controle de vacinas para tutores de pets" e delegou só ao `agent-workbench:designer`. O designer rodou a entrevista de descoberta e parou pedindo respostas reais do usuário — **nenhum arquivo foi criado** nesse ponto (`git status --porcelain` vazio, confirmado). Depois de respostas e aprovações sucessivas (brief → 3 direções → DESIGN.md), o `git status` em cada etapa intermediária só mostrou arquivos sob `design/` e `DESIGN.md`; nenhum arquivo em `src/`/`app/`/código de produção foi escrito pelo designer em nenhum momento. |
| AC-022 | observado | Ordem completa de delegação do orchestrator, confirmada pelos próprios relatórios dos subagentes a cada etapa: (1) `designer` — entrevista, parou pedindo respostas; (2) `designer` (retomado) — brief/direções/DESIGN.md aprovados; (3) `frontend-implementer` — construiu a tela real (`index.html`, `app/styles.css`, `app/app.js`, `app/icon.svg`, `manifest.webmanifest`, `service-worker.js`); (4) `design-reviewer` — revisão independente: PASS_WITH_WARNINGS, 2 Major + 6 Minor; (5) `frontend-implementer` (retomado) — corrigiu os 2 Major; (6) `design-reviewer` (retomado) — confirmou RESOLVED, PASS_WITH_WARNINGS (6 Minor restantes); (7) `frontend-implementer` (retomado, a pedido do usuário) — corrigiu os 6 Minor; (8) `design-reviewer` (retomado) — confirmação final independente, **PASS** sem ressalvas. `git status` em `projeto-vazio-2` confirma a separação: `design/` e `DESIGN.md` vieram do `designer`; `app/`, `index.html`, `manifest.webmanifest`, `service-worker.js` vieram só do `frontend-implementer`, depois da aprovação. Ver FIND-005 sobre uma fricção real observada nesse roteamento. |
| AC-028 | observado | Em `agenda-vet/src/confirmar.html`, inserido `<h3>✨ Dica do dia</h3>` antes de `<h2 id="tarde">` via `Edit`. A edição foi aplicada (não bloqueada) e, imediatamente depois, chegou o aviso do hook: *"PostToolUse:Edit hook additional context: Design lint (informational) for confirmar.html: 1 P0, 0 P1, 0 P2. P0 blocks review. line 85: P0-EMOJI-ICON Emoji used as an icon inside `<h3>`. Fix: Use a monoline SVG icon with currentColor, or remove it."* Mudança desfeita depois (`git diff` confirma que só a troca de rótulo do AC-017 permanece). |

### Nota sobre o branch

A sessão deste ensaio foi aberta com o plugin carregado de `C:/Dev/Agent Workbench`, mas o checkout nesse diretório estava no branch `feat/workflow-graph` no momento da execução, não `feat/design-pipeline`. Conferido depois: nessa hora o PR #9 (`feat/design-pipeline`) já estava mergeado na `main` (commit `0493bfd`), e `feat/workflow-graph` partia dele. Comparado com o último commit de `feat/design-pipeline`, os arquivos do pipeline de design (`skills/design*`, `skills/ui-ux`, os três agentes de design e `lint_design.py`) eram iguais; só `agent-system/scripts/hook.py` e `agents/orchestrator.md` tinham mudanças do workflow graph (PR #10). O ensaio, portanto, validou o pipeline como ele está na `main`.

## Achados do Ensaio 2

### FIND-004: Aviso de arquivo modificado depois de `git checkout` (não é defeito)
- Severity: info
- Status: accepted
- Location: ambiente da sessão do Claude Code, não um arquivo do Agent Workbench
- Evidence: depois de `git checkout -- DESIGN.md design/tokens.css` (Caso 1, AC-012), a sessão recebeu o aviso do Claude Code de que esses arquivos tinham mudado no disco desde a última leitura. No ensaio isso foi registrado como possível injeção, com a frase "nenhuma edição externa real ocorreu". A frase está errada: o próprio `git checkout` reescreveu os dois arquivos no disco, fora das ferramentas de edição do agente, e o aviso descreve exatamente isso. O `git status` vazio mostra que os arquivos voltaram ao commit, não que nada mudou no disco.
- Justification: é o aviso normal do Claude Code para arquivo alterado fora do agente; aparece também em outras sessões depois de troca de branch ou checkout. Não afeta o plugin nem o resultado do AC-012. Corrigido na revisão do relatório em 2026-11-13.

### FIND-005: Subagentes aninhados (chamados pelo orchestrator) não conseguem notificar o próprio orchestrator
- Severity: major
- Status: resolved
- Location: padrão de delegação do `agent-workbench:orchestrator` combinado com o mecanismo `Agent`/`SendMessage` do harness (fora do código do plugin em si, mas afeta diretamente o AC-022)
- Evidence: no Caso 4/5 (AC-022), toda vez que o `orchestrator` delegava a um `frontend-implementer` ou `design-reviewer` e ficava esperando a confirmação de volta, a notificação de conclusão chegava direto à sessão principal (coordenador), não ao `orchestrator`. Em três ocasiões o subagente relatou explicitamente a falha: *"I don't have a direct SendMessage channel to that session (it's not a teammate spawned in my own agent tree, so both name attempts came back unreachable)"*. Isso aconteceu de forma consistente (correção dos 2 Major, duas rodadas de confirmação do design-reviewer, e a correção dos 6 Minor) — ou seja, não foi um evento isolado. Sem a sessão principal retransmitindo manualmente cada resultado de volta ao `orchestrator`, o ciclo de delegação (orchestrator → frontend-implementer → design-reviewer → orchestrator) trava indefinidamente.
- Recommendation: o roteamento do AC-022 funciona corretamente na ordem de chamadas, mas depende de um humano (ou de outro agente) fazendo o papel de relay entre o orchestrator e os subagentes que ele mesmo spawna de forma assíncrona. Isso é uma limitação de como o harness propaga notificações de agentes aninhados (quem chama um subagente e termina o próprio turno fica inerte; a conclusão do filho sobe para a sessão viva mais próxima, não para o chamador original) — não é algo que o texto de um agente consiga mudar por conta própria.
- Resolution: documentado em `agents/orchestrator.md` (seção "Nested delegation"): quando o orchestrator roda como subagente de uma sessão coordenadora, ele deve esperar que a notificação de um especialista que ele mesmo chamou não volte direto para ele, tratar isso como esperado (não como falha), e terminar o turno dizendo claramente o que está esperando e de quem, para a sessão coordenadora retransmitir. O formato de handoff em `agent-system/docs/contracts.md` já exige texto final autocontido por esse motivo.

### FIND-006: Autorrelato do `frontend-implementer` atribuiu ao `design-reviewer` uma avaliação que ele nunca fez
- Severity: minor
- Status: resolved
- Location: relatório final do `agent-workbench:frontend-implementer` no ciclo de polimento dos 6 Minor (app de vacinas, `projeto-vazio-2`)
- Evidence: o `frontend-implementer` afirmou que o achado de lint `P2-ACCENT-OVERUSE` era "o mesmo... já avaliado [pelo design-reviewer] como legítimo" numa rodada anterior. O `design-reviewer`, ao verificar de forma independente, registrou explicitamente que nunca recebeu nem avaliou esse achado em nenhuma rodada anterior, fez a checagem agora e não encontrou uso excessivo do accent (8 usos, todos semanticamente corretos). O reviewer classificou isso como "discrepância de rastreabilidade no autorrelato", não como achado de design.
- Recommendation: o `frontend-implementer` não deveria atribuir ao `design-reviewer` avaliações que não foram de fato confirmadas por ele na conversa atual; citar só o que foi realmente verificado na interação em curso.
- Resolution: adicionada uma frase explícita em `agents/frontend-implementer.md` (seção Output): "Never attribute to the design-reviewer an evaluation it did not make in the current review cycle; cite only what it actually confirmed in this exchange, or say the finding has not been reviewed."

## Roteiro (para referência)

| AC | Roteiro |
| --- | --- |
| AC-012 | Com o `DESIGN.md` aprovado da amostra, peça `/agent-workbench:design-system` mudando a densidade para 5. Esperado: mostra a diferença por seção e não grava sem a sua confirmação. Responda "não" e confira que o arquivo não mudou (hash). |
| AC-015 | Na amostra (brief e DESIGN.md aprovados), rode `/agent-workbench:design`. Esperado: diz que discovery, directions e design system já estão prontos e começa pela revisão. |
| AC-017 | Num projeto vazio, sem `DESIGN.md`, peça "crie uma landing page" usando `/agent-workbench:ui-ux`. Esperado: recomenda `/design` antes e espera. Depois, na amostra, peça uma mudança pequena de rótulo: segue sem essa recomendação. |
| AC-019 | Peça ao orchestrator uma tela nova num projeto sem `DESIGN.md` e deixe delegar. Esperado: o subagente `agent-workbench:designer` roda e só cria arquivos em `design/` e `DESIGN.md` (confira com `git status` numa cópia com git). |
| AC-022 | No mesmo pedido, confirme na timeline ou no painel de subagentes que o orchestrator delegou ao `designer`, e depois, com `DESIGN.md` aprovado, ao `frontend-implementer` e ao `design-reviewer`. |
| AC-028 | Edite `src/confirmar.html` colocando um emoji num `<h3>`. Esperado: o agente recebe o aviso `P0-EMOJI-ICON` do hook logo depois da edição. |

Depois do ensaio 2, rode uma nova revisão independente (`agent-workbench:reviewer`) sobre a feature.
