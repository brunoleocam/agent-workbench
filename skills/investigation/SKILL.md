---
name: investigation
description: Explores an existing system and records findings without implementing. Use when the user asks to investigate, understand, explore, spike, or explain how the current system works before changing it (investigar, entender, explorar, spike, como funciona).
---

# Investigação

Não implemente. Não "aproveite" para corrigir ou refatorar. Achado que exija mudança vira tarefa, bug ou change request separado.

## Fluxo

1. Declare a pergunta que a investigação responde.
2. Leia código, testes, specs e ADRs existentes. O chat não substitui esses artefatos.
3. Responda com evidência (arquivo, símbolo, teste), não com suposição.
4. Grave o resultado onde o projeto já documenta descobertas, ou em `docs/progress/CURRENT.md` / uma nota em `docs/specs/` se essa for a árvore do repo. Inclua:
   - pergunta
   - o que o sistema faz hoje
   - restrições e riscos
   - o que não foi verificado
   - próximo passo recomendado (especificar, corrigir, refatorar ou parar)
5. Se o usuário quiser agir em seguida, classifique de novo e troque de skill. Não continue codando a partir da investigação sem spec quando o comportamento for não trivial.
