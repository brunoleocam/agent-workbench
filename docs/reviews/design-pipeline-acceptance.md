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

## Ensaio 2 (pendente): com o plugin desta branch carregado

Pedido pelo usuário para fechar o FIND-008 da revisão independente. Rode numa sessão nova do Claude Code aberta com o plugin da branch, a partir de uma cópia de `agent-system/tests/samples/design-sample/` fora do repositório:

```bash
claude --plugin-dir "C:/Dev/Agent Workbench"
```

Confirme antes que `/agent-workbench:design` existe e que `agent-workbench:designer` aparece entre os subagentes. Para cada caso, registre aqui o que aconteceu, como no ensaio 1:

| AC | Roteiro |
| --- | --- |
| AC-012 | Com o `DESIGN.md` aprovado da amostra, peça `/agent-workbench:design-system` mudando a densidade para 5. Esperado: mostra a diferença por seção e não grava sem a sua confirmação. Responda "não" e confira que o arquivo não mudou (hash). |
| AC-015 | Na amostra (brief e DESIGN.md aprovados), rode `/agent-workbench:design`. Esperado: diz que discovery, directions e design system já estão prontos e começa pela revisão. |
| AC-017 | Num projeto vazio, sem `DESIGN.md`, peça "crie uma landing page" usando `/agent-workbench:ui-ux`. Esperado: recomenda `/design` antes e espera. Depois, na amostra, peça uma mudança pequena de rótulo: segue sem essa recomendação. |
| AC-019 | Peça ao orchestrator uma tela nova num projeto sem `DESIGN.md` e deixe delegar. Esperado: o subagente `agent-workbench:designer` roda e só cria arquivos em `design/` e `DESIGN.md` (confira com `git status` numa cópia com git). |
| AC-022 | No mesmo pedido, confirme na timeline ou no painel de subagentes que o orchestrator delegou ao `designer`, e depois, com `DESIGN.md` aprovado, ao `frontend-implementer` e ao `design-reviewer`. |
| AC-028 | Edite `src/confirmar.html` colocando um emoji num `<h3>`. Esperado: o agente recebe o aviso `P0-EMOJI-ICON` do hook logo depois da edição. |

Depois do ensaio 2, rode uma nova revisão independente (`agent-workbench:reviewer`) sobre a feature.
