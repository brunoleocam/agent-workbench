---
name: change-request
description: Classifies a change discovered during implementation, analyzes impact, and updates the spec or creates a dependent task before resuming. Use when a new requirement, bug, idea, dependency, or scope change appears mid-implementation (change request, mudança de escopo, dependência, requisito novo no meio da tarefa).
---

# Change request

Surgiu algo novo enquanto `TASK-X` estava em andamento. Não altere o código de `TASK-X` para absorver isso sem classificar.

## Classifique

- Ajuste local de implementação
- Mudança de requisito
- Mudança de spec
- Mudança de arquitetura
- Dependência pré-requisito
- Tarefa nova independente
- Bug em comportamento existente

## Impacto

Liste o que é afetado: requisitos, specs, ADRs, testes/evals, tarefas, dependências, regressões possíveis.

## O que fazer

| Classe | Ação |
| --- | --- |
| Ajuste local pequeno | Atualize código e testes da tarefa atual |
| Requisito, spec ou arquitetura | Grave `docs/changes/CR-NNNN.md` e atualize os artefatos antes de continuar |
| Dependência ou tarefa nova | Crie a tarefa e registre `TASK-X` depende de `TASK-Z`. Não resolva a dependência dentro de trabalho alheio |
| Bug existente | Registre e use `bug-fix` se for bloqueante; senão deixe a tarefa separada |

`docs/changes/CR-NNNN.md`: o que apareceu, classe, impacto, decisão, artefatos atualizados, tarefa que pode retomar.

Retome `TASK-X` só depois dessa atualização. O próximo passo vem das dependências, não do impulso de seguir editando.
