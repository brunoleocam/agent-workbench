---
name: feature-development
description: Develops a feature in an existing system from impact analysis through spec, tests, implementation, and independent review. Use for a feature or meaningful behavior change (feature, funcionalidade, comportamento novo).
---

# Feature

Pré-condição: o pedido é FEATURE, complexidade S ou maior. XS não usa esta skill.

## Procedimento

1. Inspecione o código e a doc existentes. Não reconstrua documentação que não será alterada.
2. Delegue ao `planner`, ou faça você mesmo se a delegação não estiver disponível: impacto, delta de spec, ADR só se a arquitetura mudar, tasks. Não crie a árvore inteira num repo antigo.
   - problema e resultado
   - requisitos funcionais e não funcionais quando couberem
   - restrições, premissas e comportamento existente afetado
   - critérios de aceite
   - spec do que o sistema deve fazer
3. Cada task vai ao `implementer`, com teste antes ou junto da mudança.
4. Verificação vai ao `tester`.
5. Revisão vai ao `reviewer`. FAIL volta para correção, teste e nova revisão.
6. Grave o checkpoint. A próxima etapa sai das tasks e dependências. Escopo novo no meio usa `change-request`.

## Artefatos

Spec do comportamento alterado, testes que provam o aceite, checkpoint. PRD só se a feature for grande o bastante. ADR só se houver decisão de arquitetura.

## Pronto

Aceite atendido, testes relevantes verdes, review PASS ou achados documentados, estado atualizado.

## Handoff

Planner não implementa. Implementer para na descoberta de mudança de escopo e devolve ao orchestrator para `change-request`. Reviewer não corrige sozinho.
