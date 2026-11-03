# Formato dos artefatos rastreáveis

Decisão: [ADR-0001](../../docs/architecture/ADR/0001-formato-dos-artefatos-rastreaveis.md). Vale para trabalho M ou maior. XS e S não usam. Spec antiga sem IDs continua valendo como texto e não é migrada.

## Regras do parser

- Um item é um título `##` a `######` que começa com o ID: `### REQ-001: Título`. Também aceita `### [x] TASK-001 — Título`.
- O item vai até o próximo título de nível igual ou maior. Título mais profundo sem ID (`#### Evidence`) fica dentro do item.
- Campo é uma linha de lista `- Chave: valor` (ou `- **Chave:** valor`) com chave conhecida. Prosa com dois-pontos não vira campo.
- Valores `none`, `-`, `n/a`, `nenhum` contam como vazio. Listas de IDs separadas por vírgula.
- Títulos dentro de bloco de código (```) são ignorados.
- Front matter: bloco `---` no topo com linhas `chave: valor`. Não é YAML completo.
- IDs têm três dígitos ou mais e são únicos no arquivo: REQ, AC, ADR, TASK, TEST, PROOF, FIND, SEC.

Chaves (aliases em pt-BR aceitos): `Requirements` (Requisitos), `Acceptance` (Critérios), `Task`, `Files`, `Depends on` (Dependências), `Blocked by`, `Verification`, `Done when` (Pronto quando), `Gate`, `Status`, `Command`, `Shell`, `Timeout`, `Required`, `Expected`, `Cwd`, `Evidence`, `Severity`, `Confidence`, `Classification`, `Location`, `Justification`.

## Onde fica cada arquivo

Um slug por feature, o mesmo em todas as pastas. As pastas vêm de `.cursor/agent-system/layout.json`: primeiro `overrides`, depois o que o init descobriu, depois o padrão.

| Artefato | Chave do layout | Padrão |
| --- | --- | --- |
| Spec | `specs_dir` | `docs/specs/<slug>.md` |
| Tarefas e TESTs | `tasks_dir` | `docs/tasks/<slug>.md` |
| TESTs extras (opcional) | `tests_dir` | `docs/tests/<slug>.md` |
| Review | `reviews_dir` | `docs/reviews/<slug>.md` |
| Segurança | `security_dir` | `docs/security/<slug>.md` |
| ADR | `adr_dir` | `docs/architecture/ADR/` |
| Provas | fixo | `.cursor/agent-system/proofs/<slug>.json` e `.md` |

Exemplo de override, preservado quando o init roda de novo:

```json
{ "overrides": { "specs_dir": "product/specs", "reviews_dir": "qa/reviews" }, "proof_allow": ["bats"] }
```

## Spec

```markdown
---
status: draft            # draft | review | approved | superseded
complexity: M            # XS | S | M | L | XL
security_risk: HIGH      # NONE | LOW | MEDIUM | HIGH | CRITICAL
security_triggers: authentication, personal_data
---
# Spec: reset de senha

## Requirements

### REQ-001: Token de reset
WHEN the user requests a password reset
THE SYSTEM SHALL generate a unique reset token
WITH a maximum validity of 15 minutes.

## Acceptance Criteria

### AC-001: Token expira
- Requirements: REQ-001
Given a user requests password recovery
When the reset token is generated
Then the token must expire within 15 minutes.

## Assumptions
## Constraints
## Open Questions
- [ ] Pergunta ainda aberta
## Decisions
- ADR-0004: armazenamento do token
```

EARS é recomendado para requisito comportamental (`WHEN`, `WHILE`, `IF ... THEN`, `WHERE` + `SHALL`). Requisito técnico pode ser linguagem natural estruturada. O validador só conta quantos usam EARS; não reprova quem não usa.

## Tarefas e TESTs

```markdown
### TASK-001: Gerar token
- Requirements: REQ-001
- Acceptance: AC-001
- Files: src/reset.py, tests/test_reset.py
- Depends on: none
- Verification: TEST-001
- Done when: TEST-001 passa e o token tem 32 bytes
- Gate: check_proofs TEST-001
- Status: todo           # todo | in_progress | blocked | done | cancelled

### TEST-001: token expira em 15 minutos
- Acceptance: AC-001
- Task: TASK-001
- Command: python -m pytest tests/test_reset.py -q
- Timeout: 120           # segundos, opcional
- Required: yes          # no = informativo, não bloqueia o gate
- Expected: 3 passed
```

`Command` é dividido como argumentos, sem shell e sem escape por barra invertida (use `/` nos caminhos). Lista JSON também vale: `["python", "-m", "pytest"]`. `Shell: yes` só roda com `--allow-shell`. `Cwd` é relativo à raiz do projeto.

Tarefa `blocked` precisa de `Depends on` ou `Blocked by`. Tarefa `done` precisa de prova PASS de cada TEST obrigatório, ou de `Evidence` quando não tem TEST.

## Review

```markdown
---
status: PASS_WITH_WARNINGS   # PASS | PASS_WITH_WARNINGS | FAIL
reviewer: reviewer
fingerprint: <digest de check_proofs.py --fingerprint>
---
# Review: reset de senha
## Verification Audit
...
### FIND-001: Expiração não testada no limite
- Severity: major            # blocker | major | minor
- Status: open               # open | resolved | accepted
- Location: tests/test_reset.py:40
- Justification: obrigatória quando Status for accepted
```

## Relatório de segurança

Mesmo front matter. Achados `### SEC-NNN` com `Severity` (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL), `Confidence`, `Classification` (confirmed, likely, suspected, hardening, accepted-risk), `Status`, `Location`, `Verification` e `Justification`. Estrutura completa na skill `security-review`.

## Política do gate

Bloqueia: `blocker`, `CRITICAL` e `HIGH` abertos; qualquer `accepted` sem `Justification`; review ou segurança com status FAIL. `major` e `MEDIUM` abertos são aviso (bloqueiam com `--strict`). Review é exigida a partir de M; revisão de segurança, com `security_risk` HIGH ou CRITICAL.
