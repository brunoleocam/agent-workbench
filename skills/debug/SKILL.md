---
name: debug
description: Finds the root cause of a bug, test failure, or unexpected behavior with evidence before any fix. Use when something fails, a test is red, or behavior is wrong, before proposing a patch (debug, depurar, teste falhando, comportamento inesperado).
---

# Debug

Não proponha correção antes da causa ter evidência. Patch no sintoma não encerra o debug.

1. Escreva o sintoma: o que aconteceu, o que era esperado, desde quando.
2. Reproduza. Se não reproduzir, diga o que falta. Não chute um fix.
3. Leia o caminho que falha (teste, stack, código). Uma hipótese por vez.
4. Teste a hipótese com evidência: teste, log, leitura de estado, entrada mínima. Descarte ou confirme.
5. A causa explica o sintoma. Se não explica, continue. Não empilhe tentativas.
6. Com a causa confirmada, registre com `root-cause` e corrija com `tdd` ou `bug-fix`.

Pare se a correção mudar requisito ou arquitetura e use `change-request`.
