# ADR-0003: Verification and security roles

Status: accepted
Date: 2026-11-03

## Context

TLC has a separate Verifier. The Workbench already has an independent `reviewer` that compares requirement, spec, criterion, test, and code. Security today is a generic item in the review. Cursor has a built-in subagent called `security-review`.

## Decision

- Do not create a Verifier. The `reviewer` gains the Verification Audit: it questions whether each test proves the criterion and looks for how the code could be wrong with the tests green. Independence remains: the reviewer does not fix and the implementer does not do the final review.
- Create `security-reviewer`, because security requires stack references and its own report (`SEC-NNN`, severity CRITICAL to INFORMATIONAL, confidence, classification). It is called only when the request's risk calls for it, or by `/security-review`.
- The name `security-reviewer` avoids a conflict with the built-in `security-review`. The `/security-review` skill belongs to the plugin and delegates to `security-reviewer`.
- Code review and security review are complementary; neither replaces the other.

## Consequences

- One new agent in the registry and in `--for-cloud`.
- An XS or S change without a sensitive surface does not call the `security-reviewer`.
