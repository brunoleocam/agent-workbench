---
name: tdd
description: Implements behavior by writing a failing test, making it pass, then refactoring. Use when implementing a feature, bugfix, or behavior change before production code (TDD, teste primeiro, red green refactor).
---

# TDD

Nenhum código de produção sem um teste falhando antes, pelo motivo certo.

## Ciclo

1. Red. Escreva o menor teste que expressa o critério de aceite. Rode. Confirme que falha pelo motivo esperado, não por erro de setup.
2. Green. Escreva o mínimo para passar. Rode o teste alvo.
3. Refactor. Melhore o código sem mudar o comportamento. A suíte relevante continua verde.

Se o código de produção foi escrito antes do teste, apague esse código e recomece pelo teste. Não adapte o teste para caber no código já feito.

Bug: o teste vermelho é a reprodução. Correção vem depois.

Não use quando o usuário pedir protótipo descartável, ou quando não existir runner. Nesse caso, diga o que não foi verificado. Dúvida de "só desta vez" em código que vai ficar: faça o ciclo.

Higiene do teste: skill `test-hygiene`.
