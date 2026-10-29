---
name: tarefa-em-etapas
description: Divide um pedido grande em etapas pequenas, cada uma com verificação, e executa uma por vez validando antes de seguir. Use quando o pedido toca vários arquivos ou componentes, tem várias partes ou o usuário pede para fazer por partes (etapas, dividir, por partes, passo a passo, fatiar).
---

# Tarefa em etapas

Se o trabalho segue o fluxo spec-driven (M ou maior na regra `01-request-classification`), as etapas são as tarefas da spec; esta skill só controla a execução. Não cria PRD, ADR nem plano detalhado (isso é `/implementation-plan`).

1. Plano: 3 a 7 etapas, uma linha cada, no formato `N. <entrega> — verificação: <teste, comando ou checagem>`. Cada etapa pode ser verificada sozinha e deixa o sistema funcionando.
2. Ordem: dependências primeiro; a etapa de maior risco o mais cedo possível.
3. Mostre o plano. Peça confirmação só se houver decisão do usuário (escopo, abordagem); senão, comece pela etapa 1.
4. Em cada etapa: edite só o necessário e rode a verificação dela com saída filtrada.
5. Verificação falhou: corrija dentro da etapa. Não avance com etapa vermelha. Se precisar mudar o plano, ajuste e avise em uma linha.
6. Fechou a etapa: uma linha `Etapa N ok: <evidência>`. Não repita o plano inteiro.
7. Pare e peça ao usuário quando a etapa exigir decisão dele ou validação que você não consegue fazer (visual, ambiente externo, credencial).
8. No fim: lista curta das etapas com status. Se a conversa ficou longa, ofereça `/resumo-de-contexto`.
