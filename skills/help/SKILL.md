---
name: help
description: Explains each profile slash command, when to use it, and what it refuses to do. Use only when the user invokes /help.
disable-model-invocation: true
---

# /help

Responda só com o guia abaixo, em pt-BR. Não inicie nenhum fluxo.

## Como usar

Chame pelo nome numa conversa nova. Um comando faz uma fase. O próximo não começa sozinho, salvo a própria skill dizer qual é o seguinte.

Ordem típica de algo novo: `/brainstorm` → spec aprovada → `/implementation-plan` → `/git-worktree` se quiser isolar → `/tdd` ou `/implementation` → `/test-hygiene` se os testes ficarem fracos → `/code-review` → `/update-docs` → `/commit-push` só se você pedir.

Defeito: `/debug` → `/root-cause` → `/tdd` ou `/bug-fix`.

Interface: `/brainstorm` ou `/ui-ux-experiment` → você escolhe → `/ui-ux`.

Mudança trivial não precisa de comando. Repositório antigo não é migrado inteiro.

## Comandos

- `/brainstorm` — ideia ainda crua. Uma pergunta por vez, alternativas, design aprovado por você. Não escreve código nem plano.
- `/new-project` — repositório novo. PRD, arquitetura, spec, tarefas e progresso. Não cria `AGENTS.md`.
- `/feature` — o mesmo fluxo de `/feature-development`.
- `/feature-development` — feature em sistema existente: impacto, spec, tasks, implementação, teste e review.
- `/init-agent-system` — instala o sistema neste projeto sem apagar config existente e sem criar docs vazios.
- `/create-agent` — cria um subagent especializado e registra a delegação no orchestrator.
- `/agent-status` — agentes, skills, rules, hooks e o estado do workflow.
- `/timeline` — eventos append-only do projeto inicializado.
- `/investigation` — entender o sistema. Não implementa.
- `/implementation-plan` — design já aprovado. Plano com path real, exemplo de código e comando de verificação, para quem não conhece o repo.
- `/git-worktree` — cópia isolada do repositório. Pede concordância. Não faz push.
- `/implementation` — um passo do plano, ligado a um requisito.
- `/tdd` — teste falha pelo motivo certo, código mínimo, refactor. Sem código de produção antes do vermelho.
- `/test-hygiene` — o teste prova comportamento, é determinístico e falha pelo motivo certo.
- `/ui-ux-experiment` — 2 ou 3 interfaces para comparar. Não implementa todas.
- `/ui-ux` — constrói a interface escolhida, com vazio, erro, loading e sucesso, e verifica o fluxo.
- `/apple-design` — motion interativo estilo Apple na web: drag, swipe, sheets, springs, momentum, interrupção e reduced motion; também revisa interações. Não cuida de layout nem dos estados da tela.
- `/bug-fix` — correção mínima depois da causa confirmada, com regressão.
- `/debug` — reproduz e acha a causa com evidência. Não chuta patch.
- `/root-cause` — registra sintoma, mecanismo, evidência e o teste que faltou. Só com causa confirmada.
- `/refactoring` — muda estrutura. Comportamento permanece, coberto por teste.
- `/change-request` — escopo novo no meio da tarefa. Atualiza spec ou cria dependência antes de continuar.
- `/code-review` — confronta requisitos, spec, critérios, testes e código. Achado tem severidade e evidência.
- `/update-docs` — alinha spec, ADR novo ou progresso ao que mudou. Não reescreve ADR aceito.
- `/commit-push` — branch antes de editar; com testes verdes, uma única aprovação sua para commit, push, PR e merge. Sem aprovação, nada sai da máquina.
- `/roadmap` — mostra em que fase e tarefa você está, o que falta e o que está bloqueado. Também cria, atualiza ou gera a visão em Canvas (`/roadmap visual`). Só em projeto com `/init-agent-system`.
- `/resumo-de-contexto` — resumo de até 10 linhas (objetivo, decisões, arquivos, próximos passos) para colar num chat novo. Não relê arquivos nem grava nada.
- `/investigacao-enxuta` — acha a causa de um bug lendo o mínimo, uma hipótese por vez. Não corrige.
- `/tarefa-em-etapas` — divide pedido grande em 3 a 7 etapas verificáveis e executa uma por vez. Não cria PRD, ADR nem plano detalhado.
- `/create-skill` — cria uma skill nova no perfil e inclui o comando neste guia. Não cria skill dentro do repositório, a menos que você peça.
- `/help` — mostra este guia.
