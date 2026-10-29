---
name: bug-fix
description: Diagnoses a defect, reproduces it with a failing test, applies the smallest fix, and checks regressions. Use when the user reports a bug, regression, incorrect behavior, or asks to fix a defect (bug, defeito, correção, regressão).
---

# Correção de defeito

## Fluxo

1. Siga `debug` até a causa ter evidência. Registre com `root-cause`. Só então escreva o menor teste que falha pelo motivo certo, via `tdd`.
2. Localize a causa no código existente. Não reescreva o módulo para "aproveitar".
3. Se a correção mudar comportamento aceito, requisito ou arquitetura, pare e use `change-request`. Correção local segue nesta skill.
4. Implemente o mínimo para o teste passar. Depois refatore só se o comportamento pretendido permanecer.
5. Rode o teste alvo e a regressão relevante.
6. Não declare corrigido com teste obrigatório falhando.
7. Para defeito não trivial, revise com `code-review` (o teste passar não basta) e atualize `docs/progress/CURRENT.md` se o projeto tiver progresso spec-driven.

Informe: causa, teste que prova a correção, resultado da regressão, risco residual.

## Handoff

`debugger` confirma a causa. `tester` traz a evidência. `reviewer` revisa sem corrigir. Escopo novo volta ao orchestrator via `change-request`.
