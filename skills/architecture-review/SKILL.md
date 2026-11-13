---
name: architecture-review
description: Reviews code and infrastructure against ARCHITECTURE.md and its ADRs, using a fixed checklist (components outside the contract, module dependency violations, async flows without idempotency, logs without structure or correlation id, secrets, ports, or permissions outside section 8, stage triggers reached without a recorded change) plus the infrastructure lint, and reports findings with severity and evidence without fixing them. Use after a change that touches infrastructure files or adds a database, cache, queue, external service, or deploy unit (revisão de arquitetura, conferir com o ARCHITECTURE.md, revisar infraestrutura, revisar Dockerfile, revisar docker-compose).
---

# Architecture review

Last step of `architecture`, and the check run after a change that touches infrastructure or adds a component. It compares what exists with what the contract says. It reports; it does not fix.

Inputs: `ARCHITECTURE.md`, the ADRs it cites (in `adr_dir` of `.cursor/agent-system/layout.json`, or `docs/architecture/ADR/` by default), and the code and infrastructure files in scope (the changed files, or the whole project on a full review). Without an approved `ARCHITECTURE.md`, stop and say to run `architecture` first; there is nothing to compare against.

## 1. Run the infrastructure lint

Run the lint from the plugin, or from the copy the init puts in the project:

```bash
python <plugin>/agent-system/scripts/lint_infra.py <files or directories> --format text
# or, after the init: python .cursor/agent-system/scripts/lint_infra.py <files or directories>
```

Every P0 is a blocking finding. P1 and P2 are reported with their severity. If neither path has `lint_infra.py` in this installation, say so in the report and check the P0 items listed under item 11 of the checklist by reading the files.

## 2. Walk the checklist

Answer every item in [references/review-checklist.md](references/review-checklist.md) against the files in scope. For each problem, record:

- **Severity**: `blocker` (contract violated, data at risk, or a lint P0), `major` (contract incomplete or likely to break at the next stage), `minor` (inconsistency without immediate risk).
- **Evidence**: file and line, or the exact snippet, and the section of `ARCHITECTURE.md` or the ADR it contradicts.
- **Suggestion**: the smallest change that resolves it, or "update the contract through `change-request`" when the code is right and the contract is outdated.

Do not mark a finding without evidence. Do not edit files.

## 3. Report

Report in the user's language:

1. Verdict: `approved`, `approved with warnings`, or `not approved`. Never `approved` while a lint P0 or a `blocker` is open.
2. The findings, most severe first, each with severity, evidence, and suggestion.
3. What was checked and what was not (files out of scope, the lint missing).

Changes that touch authentication, authorization, tenant isolation, or secrets also go to the `security-review` skill and the `security-reviewer` agent; this review does not replace them.

## Done when

Every checklist item was answered for the files in scope, the lint ran or its absence was reported, and the verdict follows the rule above.
