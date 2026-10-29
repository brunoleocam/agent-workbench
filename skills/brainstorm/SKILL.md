---
name: brainstorm
description: Refines a rough idea into an approved design through structured Socratic questioning, alternative exploration, and incremental validation. Use immediately when creating or developing anything, before writing code or an implementation plan (brainstorm, ideia, desenhar, antes de codar, antes do plano).
---

# Brainstorm

Use antes de criar ou desenvolver comportamento, produto ou interface, e antes de escrever código ou plano de implementação, quando ainda não houver design aprovado.

Não use quando o usuário mandou executar spec ou plano já aprovados, quando o pedido é só investigação, review, commit, push ou correção trivial.

Não escreva código, não scaffolde projeto e não chame `implementation-plan` nem `implementation` até o usuário aprovar o design.

## Fluxo

1. Leia o contexto do repositório (código, spec, commits recentes) antes da primeira pergunta.
2. Se a ideia couber em vários sistemas independentes, pare e proponha quebrar em partes. Brainstorm só da primeira.
3. Faça uma pergunta por mensagem. Prefira escolha fechada. Objetivo, restrição e critério de sucesso.
4. Proponha 2 ou 3 abordagens, com trade-off e uma recomendação.
5. Apresente o design em partes curtas. Peça aprovação de cada parte antes da próxima.
6. Com o design aprovado, grave a spec no lugar canônico do repo, ou em `docs/specs/` se essa for a árvore. Sem placeholder. Sem contradição com o que foi aprovado.
7. Peça para o usuário revisar a spec. Ajuste se ele pedir.
8. O próximo passo é `implementation-plan`. Não implemente neste turno.
