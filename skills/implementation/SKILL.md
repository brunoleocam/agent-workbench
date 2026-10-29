---
name: implementation
description: Executes one independently verifiable implementation step tied to a requirement and its tests. Use when implementing a specified task, continuing planned work, or applying Red-Green-Refactor to a single slice (implementar tarefa, próximo passo, TDD).
---

# Implementação

Um passo. Não implemente fatias grandes nem partes sem relação com o requisito deste passo.

## Por passo

1. Aponte o requisito ou critério de aceite exato. Se não existir para comportamento não trivial, volte para `feature` ou `new-project` e escreva a spec antes.
2. Aponte os testes ou evals que provam esse requisito.
3. Siga `tdd`: o menor teste útil falha pelo motivo certo antes de código de produção.
4. Green: a menor mudança coerente faz o teste passar.
5. Rode a verificação alvo e a regressão relevante.
6. Refatore sem mudar o comportamento pretendido.
7. Atualize o status da tarefa e os artefatos do projeto.

Não declare o passo completo com teste exigido falhando.

## Handoff

Quem executa é o `implementer`. Verificação vai ao `tester`. Review independente vai ao `reviewer`. Mudança de escopo para no orchestrator.

Se aparecer ideia, bug, requisito ou dependência nova, pare e use `change-request`.

Ao fechar o passo, grave o checkpoint (regra `06-checkpoint-and-progress`): o que entrou, spec atendida, testes e resultados, review, achados, correções, restante, bloqueios, próximo passo. O próximo passo sai do grafo de tarefas.

Mudança significativa: depois deste passo verde e da regressão, use `code-review` antes de chamar o trabalho de pronto.
