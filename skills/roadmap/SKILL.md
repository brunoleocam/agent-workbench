---
name: roadmap
description: Cria, mostra e atualiza o roadmap do projeto em docs/progress/ROADMAP.md, com fases, tarefas, status e a posição atual; opcionalmente gera uma visão em Canvas. Use quando o usuário quer saber em que etapa está, o que foi feito e o que falta, ou ao planejar trabalho grande em projeto com /init-agent-system (roadmap, em que etapa estou, o que falta, progresso do plano).
---

# Roadmap

Arquivo único: `docs/progress/ROADMAP.md`, na raiz do projeto. Vale só em projeto com `.cursor/agent-system/state.json`. Sem ele, diga para rodar `/init-agent-system` e pare.

## Formato

```markdown
# Roadmap — <projeto ou frente>

> Você está aqui: Fase 2 — API · TASK-008

Legenda: [x] feito · [~] em andamento · [ ] pendente · [!] bloqueado

## Fase 1 — Dados
- [x] TASK-001 Modelo de pedido — spec: docs/specs/pedido.md
- [x] TASK-002 Migração

## Fase 2 — API
- [~] TASK-008 Reserva de estoque — depende de TASK-002
- [!] TASK-009 Pagamento — bloqueado: credencial do gateway
- [ ] TASK-010 Webhook — depende de TASK-009
```

- Uma linha por tarefa: status, ID, título curto, dependência ou bloqueio, link para spec ou task se houver.
- Fases em ordem de dependência. Os IDs são os mesmos de `docs/tasks/`.
- A linha "Você está aqui" aponta a fase e a tarefa em andamento. O hook de início de chat e o `/agent-status` leem essa linha e contam os `[x]`, `[~]`, `[ ]` e `[!]`.

## Modos

Sem argumento: mostrar. Com "criar", "atualizar" ou "visual": o modo pedido.

- **Mostrar**: leia só o `ROADMAP.md`. Responda com a linha "Você está aqui", a contagem por status, as tarefas em andamento e bloqueadas e as próximas 3 pendentes cujas dependências já estão feitas. Não liste as tarefas feitas.
- **Criar**: a partir do plano aprovado ou das tarefas em `docs/tasks/`. Se não houver plano, use `/tarefa-em-etapas` ou o `planner` antes. Se já existe roadmap, estenda; não reescreva itens feitos.
- **Atualizar**: edite só as linhas que mudaram e a linha "Você está aqui". Status `[x]` só com evidência (teste, comando ou review). Tarefa nova de change request entra na fase certa, com a dependência.
- **Visual**: leia a skill `canvas` e gere um canvas a partir do `ROADMAP.md`, com fases como colunas ou trilhas, tarefas coloridas por status, dependências e a posição atual em destaque. O arquivo continua sendo a fonte de verdade; o canvas é só a visão.
