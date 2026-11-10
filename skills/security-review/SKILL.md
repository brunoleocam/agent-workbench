---
name: security-review
description: Audits a feature or the whole repository for security issues using stack-specific references and writes a structured report with SEC findings, severity, confidence, and classification. Does not fix anything. Use only when the user invokes /security-review.
disable-model-invocation: true
---

# /security-review

The plugin's security audit. It produces a report; it does not fix. A fix depends on the user's authorization and follows the normal flow (`/change-request` or `/bug-fix`).

Delegate to the `security-reviewer` subagent when available. Without it, follow this procedure in the current conversation.

Not to be confused with Cursor's built-in subagent called `security-review`: that one reviews the local diff. This skill audits a feature or the repository and writes a report in the format below. It also does not replace `/code-review`; the two complement each other.

## Procedure

1. Scope. Feature: use the spec slug (`docs/specs/<slug>.md`). No feature given: the whole repository.
2. Start event, only if `.cursor/agent-system/state.json` exists:

   ```bash
   python .cursor/agent-system/scripts/record_event.py --event SECURITY_REVIEW_STARTED --summary "<scope>" --agent security-reviewer
   ```

3. Stack and architecture. Read `.cursor/agent-system/layout.json` (`frameworks`, `security_references`) when it exists; otherwise the manifests. Map inputs, layers, storage, and integrations.
4. Attack surfaces: authentication, authorization, session, upload, payment, webhooks, admin, public APIs, calls to external URLs, deserialization, command execution, secrets, and production configuration.
5. Load only the stack's references from `../security-best-practices/references/`. Never all of them.
6. Analyze the surfaces' code. Follow the data from the input to the sensitive point. Also record the controls that already exist.
7. Classify each finding (fields below). Do not invent a path, line, or exploit scenario. A missing recommendation with no exploitation path is `hardening`, not a vulnerability.
8. Fingerprint of the reviewed state:

   ```bash
   python .cursor/agent-system/scripts/check_proofs.py --root . --fingerprint
   ```

   Without the script (project not initialized), leave the fingerprint blank and say in the Executive Summary that the report is not tied to a code state. HEAD alone does not work: it ignores modified files.
9. Write the report (see Output) and recommend next steps.
10. End event, only if `.cursor/agent-system/state.json` exists:

    ```bash
    python .cursor/agent-system/scripts/record_event.py --event SECURITY_REVIEW_COMPLETED --result "<STATUS> findings=<N>" --agent security-reviewer
    ```

## Output

Directory: `overrides.security_dir` or `security_dir` from `.cursor/agent-system/layout.json`; default `docs/security`.

- Feature: `<security_dir>/<slug>.md`
- Repository: `<security_dir>/security_assessment.md`

Status:

- `FAIL`: any CRITICAL or HIGH finding with `Status: open`.
- `PASS_WITH_WARNINGS`: no open CRITICAL/HIGH and some MEDIUM or LOW open.
- `PASS`: otherwise.

## Report format

Read by a deterministic parser. Keep the front matter, headings, and keys exactly as shown, with every section present even if empty (write `None.`).

```markdown
---
status: PASS | PASS_WITH_WARNINGS | FAIL
scope: <slug or repository>
reviewer: security-reviewer
fingerprint: <digest>
---
# Security Assessment
## Executive Summary
## Scope and Methodology
## Findings Summary
## Critical Findings
## High Findings
## Medium Findings
## Low Findings
## Informational Findings
## Existing Security Controls
## Residual Risks
## Recommendations
```

`status` takes a single value. Each finding is a `### SEC-NNN: <title>` inside the section of its severity, numbered in sequence across the report. Right below the title, the field lines:

- `Severity`: CRITICAL, HIGH, MEDIUM, LOW, or INFORMATIONAL (same as the section)
- `Confidence`: high, medium, or low
- `Classification`: confirmed, likely, suspected, hardening, or accepted-risk
- `Status`: open, resolved, or accepted
- `Location`: real `path:line`
- `Verification`: how to verify that the fix works
- `Justification`: required when `Status: accepted`

After the field lines, free text: Evidence, Description, Impact, Exploit scenario (only if demonstrable), Recommendation.

In Findings Summary, count findings by severity and by status.

## Example finding

Illustrative; the path, line, and snippet in a real report come from the code read.

```markdown
## High Findings

### SEC-001: Another user's order reachable by ID
- Severity: HIGH
- Confidence: high
- Classification: confirmed
- Status: open
- Location: app/Http/Controllers/OrderController.php:42
- Verification: a feature test where user B requests GET /orders/{id} for user A's order and gets 403 or 404

Evidence: `Order::findOrFail($id)` with no owner filter and no policy; the route is only under the `auth` middleware.

Description: any authenticated user reads other people's orders by changing the ID (IDOR).

Impact: exposure of the address, items, and amounts of every customer.

Exploit scenario: authenticated as B, iterate `GET /orders/1..N` and receive 200 with A's data.

Recommendation: fetch through the user's relation (`$request->user()->orders()->findOrFail($id)`) or apply the `OrderPolicy@view` policy with `Gate::authorize('view', $order)`.
```

## When done

Reply with: the report path, status, count by severity, and the CRITICAL/HIGH findings in one line each. Ask whether the user authorizes opening the fix. Do not edit code.
