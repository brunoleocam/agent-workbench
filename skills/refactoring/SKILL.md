---
name: refactoring
description: Restructures code without changing intended behavior, guarded by existing or characterization tests. Use when the user asks to refactor, clean up, simplify, or restructure without adding behavior (refatorar, limpar, reestruturar, sem mudar comportamento).
---

# Refatoração

O comportamento pretendido não muda. Se precisar mudar comportamento, pare e use `feature` ou `change-request`.

## Fluxo

1. Nomeie o que melhora (limites, duplicação, complexidade) e o que deve permanecer igual.
2. Garanta testes que caracterizam o comportamento atual. Se não existirem, escreva-os antes de mover código e veja-os passar no código antigo.
3. Decisão de arquitetura nova vira ADR. Não decida estrutura relevante só no diff.
4. Faça o menor passo coerente. Rode os testes de caracterização e a regressão após cada passo.
5. Não misture feature, bugfix ou formatação em massa no mesmo passo.
6. Revise com `code-review` olhando mudança desnecessária e comportamento não intencional.
7. Atualize o checkpoint se o trabalho for relevante: o que mudou na estrutura, quais testes provaram que o comportamento ficou igual.
