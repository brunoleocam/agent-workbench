---
name: code-review
description: Independently reviews an implementation against requirements, specification, acceptance criteria, and tests, and returns findings with severity and evidence. Use when the user asks for a code review, or after a meaningful change has been implemented and verified (revisão, code review, conformidade com a spec).
---

# Independent review

Review the change. Passing tests do not close the review.

Compare in this order:

1. Requirements
2. Spec
3. Acceptance criteria
4. Tests and evals
5. Implementation

## Look for

Conformance to requirement and spec, missing functionality, incorrect behavior, architecture violations, security, error handling, maintainability, complexity, performance, test gaps, unintended behavior, unnecessary changes.

## Verification Audit

Do not assume the tester's work is correct. For each acceptance criterion and its TESTs:

1. Does the test match the criterion?
2. Does it verify the expected behavior or only that the code runs?
3. Would it fail if the requirement were implemented wrong? Say which mutation would slip through.
4. Is there a negative case?
5. Is there a relevant boundary case?
6. Are the assertions specific?
7. Does it check the result or an implementation detail?
8. Is any important condition untested?
9. Is the proof from the current code? (`validate_verification.py` flags a stale proof.)

Look for a way the implementation could be wrong with every test green. A test that would not fail with the wrong requirement is a `major` or `blocker` finding, even with the gate green.

## Output

For each finding:

- severity: `blocker`, `major`, or `minor`
- evidence: file, behavior, or criterion violated
- what is missing to be correct

If there is no finding, say so and cite what was compared (requirement, spec, tests run).

For M or larger, write `<reviews_dir>/<slug>.md` (default `docs/reviews/`): front matter `status`, `reviewer`, and `fingerprint` (from `check_proofs.py --fingerprint`), the Verification Audit section, and one `### FIND-NNN` per finding with `- Severity:`, `- Status:` (open, resolved, accepted) and, if accepted, `- Justification:`. Format in `agent-system/docs/artifacts.md`. `validate_verification.py` reads this file.

A valid finding is not closed with an "acknowledged". Fix it, test it, run the regression, and review again. Dismiss a finding only with the reason written in the checkpoint or the review note.

Do not replace this review with Bugbot, Cursor's built-in `security-review` subagent, or the plugin's `/security-review` skill. Specialized security is complementary (`security-reviewer`). This skill is the requirement → code comparison.

## Handoff

The `reviewer` subagent does this review. It does not implement the fix. FAIL goes back to the `implementer` and `tester`, then to the reviewer again.
