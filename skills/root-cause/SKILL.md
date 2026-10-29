---
name: root-cause
description: Writes a root-cause record with symptom, evidence, mechanism, and the regression test. Use after a defect cause is confirmed and must be documented (causa raiz, root cause, postmortem curto, por que o bug passou).
---

# Causa raiz

Escreva só depois que `debug` (ou evidência equivalente) confirmou a causa. Sem evidência, volte para `debug`. Não invente mecanismo.

Grave no lugar de changes ou bugs do repo. Se não houver, use `docs/changes/` apenas quando o projeto já usa essa árvore; senão, deixe o registro na resposta e no checkpoint da frente.

## Registro

- Sintoma
- Impacto
- Como reproduzir
- Causa: o mecanismo, não só o nome do arquivo
- Evidência: teste, log, trecho lido
- Por que os testes existentes não pegaram
- Correção
- Teste de regressão que falha sem a correção

Não reescreva um registro antigo para ficar mais bonito. Se a causa mudou, escreva o que a evidência nova mostrou.
