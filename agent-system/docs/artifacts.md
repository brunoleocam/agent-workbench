# Traceable artifact format

Decision: [ADR-0001](../../docs/architecture/ADR/0001-formato-dos-artefatos-rastreaveis.md). Applies to M or larger work. XS and S do not use it. An old spec without IDs remains valid as text and is not migrated.

## Parser rules

- An item is a `##` to `######` heading that starts with the ID: `### REQ-001: Title`. It also accepts `### [x] TASK-001 — Title`.
- The item runs to the next heading of equal or higher level. A deeper heading without an ID (`#### Evidence`) stays inside the item.
- A field is a list line `- Key: value` (or `- **Key:** value`) with a known key. Prose with a colon does not become a field.
- The values `none`, `-`, `n/a`, `nenhum` count as empty. ID lists are comma-separated.
- Headings inside a code block (```) are ignored.
- Front matter: a `---` block at the top with `key: value` lines. It is not full YAML.
- IDs have three or more digits and are unique in the file: REQ, AC, ADR, TASK, TEST, PROOF, FIND, SEC.

Keys (Portuguese aliases such as `Requisitos`, `Critérios`, `Dependências`, and `Pronto quando` are still accepted for existing projects): `Requirements`, `Acceptance`, `Task`, `Files`, `Depends on`, `Blocked by`, `Verification`, `Done when`, `Gate`, `Status`, `Command`, `Shell`, `Timeout`, `Required`, `Expected`, `Cwd`, `Evidence`, `Severity`, `Confidence`, `Classification`, `Location`, `Justification`.

## Where each file lives

One slug per feature, the same in every folder. The folders come from `.cursor/agent-system/layout.json`: first `overrides`, then what the init discovered, then the default.

| Artifact | Layout key | Default |
| --- | --- | --- |
| Spec | `specs_dir` | `docs/specs/<slug>.md` |
| Tasks and TESTs | `tasks_dir` | `docs/tasks/<slug>.md` |
| Extra TESTs (optional) | `tests_dir` | `docs/tests/<slug>.md` |
| Review | `reviews_dir` | `docs/reviews/<slug>.md` |
| Security | `security_dir` | `docs/security/<slug>.md` |
| ADR | `adr_dir` | `docs/architecture/ADR/` |
| Proofs | fixed | `.cursor/agent-system/proofs/<slug>.json` and `.md` |

Override example, preserved when the init runs again:

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
# Spec: password reset

## Requirements

### REQ-001: Reset token
WHEN the user requests a password reset
THE SYSTEM SHALL generate a unique reset token
WITH a maximum validity of 15 minutes.

## Acceptance Criteria

### AC-001: Token expires
- Requirements: REQ-001
Given a user requests password recovery
When the reset token is generated
Then the token must expire within 15 minutes.

## Assumptions
## Constraints
## Open Questions
- [ ] A question still open
## Decisions
- ADR-0004: token storage
```

EARS is recommended for behavioral requirements (`WHEN`, `WHILE`, `IF ... THEN`, `WHERE` + `SHALL`). A technical requirement can be structured natural language. The validator only counts how many use EARS; it does not fail those that do not.

## Tasks and TESTs

```markdown
### TASK-001: Generate token
- Requirements: REQ-001
- Acceptance: AC-001
- Files: src/reset.py, tests/test_reset.py
- Depends on: none
- Verification: TEST-001
- Done when: TEST-001 passes and the token has 32 bytes
- Gate: check_proofs TEST-001
- Status: todo           # todo | in_progress | blocked | done | cancelled

### TEST-001: token expires in 15 minutes
- Acceptance: AC-001
- Task: TASK-001
- Command: python -m pytest tests/test_reset.py -q
- Timeout: 120           # seconds, optional
- Required: yes          # no = informational, does not block the gate
- Expected: 3 passed
```

`Command` is split into arguments, without a shell and without backslash escaping (use `/` in paths). A JSON list also works: `["python", "-m", "pytest"]`. `Shell: yes` only runs with `--allow-shell`. `Cwd` is relative to the project root.

A `blocked` task needs `Depends on` or `Blocked by`. A `done` task needs a PASS proof for each required TEST, or `Evidence` when it has no TEST.

## Review

```markdown
---
status: PASS_WITH_WARNINGS   # PASS | PASS_WITH_WARNINGS | FAIL
reviewer: reviewer
fingerprint: <digest from check_proofs.py --fingerprint>
---
# Review: password reset
## Verification Audit
...
### FIND-001: Expiry not tested at the boundary
- Severity: major            # blocker | major | minor
- Status: open               # open | resolved | accepted
- Location: tests/test_reset.py:40
- Justification: required when Status is accepted
```

## Security report

Same front matter. `### SEC-NNN` findings with `Severity` (CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL), `Confidence`, `Classification` (confirmed, likely, suspected, hardening, accepted-risk), `Status`, `Location`, `Verification`, and `Justification`. Full structure in the `security-review` skill.

## Gate policy

Blocks: open `blocker`, `CRITICAL`, and `HIGH`; any `accepted` without `Justification`; a review or security report with status FAIL. Open `major` and `MEDIUM` are a warning (they block with `--strict`). A review is required from M; a security review, with `security_risk` HIGH or CRITICAL.
