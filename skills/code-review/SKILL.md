---
name: code-review
description: Independently reviews an implementation against requirements, specification, acceptance criteria, and tests, and returns findings with severity and evidence. Use when the user asks for a code review, or after a meaningful change has been implemented and verified (revisão, code review, conformidade com a spec).
---

# Revisão independente

Revise a mudança. Testes passando não fecham a revisão.

Compare nesta ordem:

1. Requisitos
2. Spec
3. Critérios de aceite
4. Testes e evals
5. Implementação

## Procure

Conformidade com requisito e spec, funcionalidade faltante, comportamento incorreto, violação de arquitetura, segurança, tratamento de erro, manutenibilidade, complexidade, performance, lacuna de teste, comportamento não intencional, mudança desnecessária.

## Saída

Para cada achado:

- severidade: `blocker`, `major` ou `minor`
- evidência: arquivo, comportamento ou critério violado
- o que falta para ficar correto

Se não houver achado, diga isso e cite o que foi comparado (requisito, spec, testes executados).

Achado válido não se encerra com um "ciente". Corrija, teste, rode regressão e revise de novo. Só dispense um achado com o motivo escrito no checkpoint ou na nota de review.

Não substitua esta revisão por Bugbot nem por security-review, a menos que o usuário peça esses fluxos. Esta skill é o confronto requisito → código.

## Handoff

O subagent `reviewer` faz esta revisão. Ele não implementa a correção. FAIL volta ao `implementer` e ao `tester`, depois ao reviewer de novo.
