---
name: feature-development
description: Develops a feature in an existing system from impact analysis through spec, tests, implementation, and independent review. Use for a feature or meaningful behavior change (feature, funcionalidade, comportamento novo).
---

# Feature

Precondition: the request is a FEATURE, complexity S or larger. XS does not use this skill.

## Procedure

1. Inspect the existing code and docs. Do not rebuild documentation that will not be changed.
2. Delegate to the `planner`, or do it yourself if delegation is unavailable: impact, spec delta, ADR only if the architecture changes, tasks. Do not create the whole tree in an old repo.
   - problem and outcome
   - functional and non-functional requirements where they fit
   - constraints, assumptions, and existing behavior affected
   - acceptance criteria
   - spec of what the system must do
   For M or larger, in the traceable format (`agent-system/docs/artifacts.md`): REQ in EARS, AC, TASK, and TEST. Gate: `validate_spec.py --feature <slug> --require-approval`, the user's approval, then `validate_tasks.py --feature <slug>`.
3. Each task goes to the `implementer`, with the test before or alongside the change. Sensitive surface: `security-best-practices` skill.
4. Verification goes to the `tester`, who runs `check_proofs.py --feature <slug>`.
5. HIGH or CRITICAL risk: `security-reviewer` writes `<security_dir>/<slug>.md`.
6. Review goes to the `reviewer`, with a Verification Audit, in `<reviews_dir>/<slug>.md`. FAIL goes back to fix, test, and a new review.
7. `validate_verification.py --feature <slug>` exits 0. Without that, it is not done.
8. Write the checkpoint. The next step comes from the tasks and dependencies. New scope in the middle uses `change-request`.

For S: a short spec and the test that proves the change, with no IDs and no mandatory gates.

## Artifacts

Spec of the changed behavior, tests that prove acceptance, checkpoint. PRD only if the feature is big enough. ADR only if there is an architecture decision.

## Done

Acceptance met, relevant tests green, review PASS or findings documented, state updated. For M or larger, `validate_verification.py` exiting 0.

## Handoff

The planner does not implement. The implementer stops when it discovers a scope change and returns to the orchestrator for `change-request`. The reviewer does not fix on its own.
