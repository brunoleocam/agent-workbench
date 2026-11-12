# Handoff contracts

Every handoff between agents uses a `handoff` block in simple YAML (key: value and lists). No free-form report. What is already in a file is cited by path, not copied.

Input (the orchestrator sends):

```yaml
handoff: in
agent: implementer
feature: reset-password        # slug shared by spec, tasks, reviews, and security
task: TASK-001
requirements: [REQ-001]
acceptance: [AC-001]
verification: [TEST-001]
risk: {complexity: M, security: LOW}
artifacts: [docs/specs/reset-password.md, docs/tasks/reset-password.md]
files_allowed: [src/reset.py, tests/test_reset.py]
constraints: [no new dependency]
```

Output (the agent returns):

```yaml
handoff: out
agent: implementer
status: completed              # completed | blocked | failed | needs_decision
task: TASK-001
changed_files: [src/reset.py, tests/test_reset.py]
tests: [TEST-001]
evidence: [.cursor/agent-system/proofs/reset-password.json]
findings: []                   # IDs (FIND-NNN, SEC-NNN) or "none"
blockers: []
next_step: tester
```

Fields without a value stay as an empty list. `needs_decision` names the decision in `blockers`.

## Per agent

### orchestrator
Input: the user's request, `state.json`, `layout.json`. Output to the user: class, complexity, risk, next agent, and gate. It does not receive a handoff from another orchestrator.

### planner
Input: intent, classification, risk, layout paths. Output: `artifacts` (spec, ADR, tasks), a list of TASKs with dependencies, the result of `validate_spec.py` and `validate_tasks.py`, pending decisions in `blockers`.

### implementer
Input: one `task` with `requirements`, `acceptance`, `verification`, and `files_allowed`. Output: `changed_files`, `tests` run, commands and results; new scope goes in `blockers` with `status: needs_decision`.

### tester
Input: `feature`, `task`, or a list of TESTs. Output: one report per TEST (format in `agents/tester.md`), `evidence` with the JSON from `check_proofs.py`, and the classification of each failure: application, test, or environment.

### reviewer
Input: `feature`, `artifacts`, `evidence`, diff. Output: `status` PASS, PASS_WITH_WARNINGS, or FAIL; the path of `<reviews_dir>/<slug>.md`; `findings` with FIND-NNN; the Verification Audit result.

### debugger
Input: symptom, command or steps, log. Output: reproduction, cause with evidence, fix applied or proposed, regression test (TEST-NNN when there is a plan).

### security-reviewer
Input: scope (feature or repository), `changed_files`, `risk`, triggers. Output: the report path, `status`, `findings` with SEC-NNN and a count by severity. It does not fix.

Refutation mode: input adds `mode: refute` and one `claim` (location, attacker-controlled input, sensitive point, impact), without the finder's reasoning. Output: `verdict` (`confirmed`, `refuted`, or `unresolved`) with `path:line` evidence, or the exact missing fact for `unresolved`. No report is written. Run it in a fresh context so the finder never confirms its own finding.

### designer
Input: the product or screen, `design/brief.md` if any, and the paths of existing design artifacts. Output: `changed_files` limited to `design/` and `DESIGN.md`; `status: needs_decision` with the question in `blockers` while waiting for the user's answers, choice of direction, or approval; `status: completed` once `design/brief.md` and `DESIGN.md` are approved.

### frontend-implementer
Input: one `task` with `requirements`, `acceptance`, `verification`, `files_allowed`, and the page name. Output: `changed_files`, `tests` run with results, the `lint_design.py` output for the changed UI files, and the `design-review` scores; `status: blocked` with an open lint P0; a needed change to the design contract goes in `blockers` with `status: needs_decision`.

### design-reviewer
Input: `feature`, `task`, `changed_files`, and the page name. Output: `status` PASS, PASS_WITH_WARNINGS, or FAIL (FAIL with any open lint P0); the path of `<reviews_dir>/<slug>-design.md` (with `fingerprint`); `findings` with FIND-NNN. It does not fix. The design report is a separate artifact that `validate_verification.py` does not read; the orchestrator blocks the screen while it is FAIL, and the `reviewer`'s `<slug>.md` stays the gate.
