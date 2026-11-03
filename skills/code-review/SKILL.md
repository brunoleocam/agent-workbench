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

## Verification Audit

Não assuma que o trabalho do tester está correto. Para cada critério de aceite e seus TESTs:

1. O teste corresponde ao critério?
2. Verifica o comportamento esperado ou só que o código roda?
3. Falharia se o requisito estivesse implementado errado? Diga qual mutação passaria.
4. Há caso negativo?
5. Há caso-limite relevante?
6. As assertions são específicas?
7. Verifica resultado ou detalhe de implementação?
8. Alguma condição importante está sem teste?
9. A prova é do código atual? (`validate_verification.py` aponta prova obsoleta.)

Procure uma forma de a implementação estar errada com todos os testes verdes. Teste que não falharia com o requisito errado é achado `major` ou `blocker`, mesmo com o gate verde.

## Saída

Para cada achado:

- severidade: `blocker`, `major` ou `minor`
- evidência: arquivo, comportamento ou critério violado
- o que falta para ficar correto

Se não houver achado, diga isso e cite o que foi comparado (requisito, spec, testes executados).

Em M ou maior, grave `<reviews_dir>/<slug>.md` (padrão `docs/reviews/`): front matter `status`, `reviewer` e `fingerprint` (de `check_proofs.py --fingerprint`), a seção Verification Audit e um `### FIND-NNN` por achado com `- Severity:`, `- Status:` (open, resolved, accepted) e, se aceito, `- Justification:`. Formato em `agent-system/docs/artifacts.md`. `validate_verification.py` lê esse arquivo.

Achado válido não se encerra com um "ciente". Corrija, teste, rode regressão e revise de novo. Só dispense um achado com o motivo escrito no checkpoint ou na nota de review.

Não substitua esta revisão por Bugbot, pelo subagent built-in `security-review` do Cursor nem pela skill `/security-review` do plugin. Segurança especializada é complementar (`security-reviewer`). Esta skill é o confronto requisito → código.

## Handoff

O subagent `reviewer` faz esta revisão. Ele não implementa a correção. FAIL volta ao `implementer` e ao `tester`, depois ao reviewer de novo.
