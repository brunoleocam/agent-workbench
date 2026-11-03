# ADR-0003: Papéis de verificação e segurança

Status: aceito
Data: 2026-11-03

## Contexto

O TLC tem um Verifier separado. O Workbench já tem um `reviewer` independente que compara requisito, spec, critério, teste e código. Segurança hoje é um item genérico da review. O Cursor tem um subagent built-in chamado `security-review`.

## Decisão

- Não criar Verifier. O `reviewer` ganha a Verification Audit: questiona se cada teste prova o critério e procura como o código poderia estar errado com os testes verdes. A independência continua: o reviewer não corrige e o implementer não faz a revisão final.
- Criar `security-reviewer`, porque segurança exige referências por stack e um relatório próprio (`SEC-NNN`, severidade CRITICAL a INFORMATIONAL, confiança, classificação). Ele é chamado só quando o risco do pedido pede, ou por `/security-review`.
- O nome `security-reviewer` evita conflito com o built-in `security-review`. A skill `/security-review` é do plugin e delega ao `security-reviewer`.
- Code review e security review são complementares; nenhum substitui o outro.

## Consequências

- Um agente novo no registro e no `--for-cloud`.
- Mudança XS e S sem superfície sensível não chama o `security-reviewer`.
