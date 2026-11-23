# Phase 1 report (0.7.0, branch `phase-1`)

Base: `466f2c6` (0.6.1). 74 files, about 3,600 lines added. Not pushed or merged.

## Verification

- `test_system.py`: 207 passed. `run_evals.py`: 14/14 (four new evals).
- Workbench flow for the two M+ features: approved specs, validated tasks, PASS proofs on the current workspace (enforcement 8/8, mutation-proof 3/3), and an independent review.
- Four review rounds. Round 1 found 2 blockers and 9 majors. Round 2 found 1 blocker and 2 majors. Round 3 found 1 major. Every finding came with a reproduction, and each fix has a regression test that fails on the code before it.
- Final reviews: both PASS_WITH_WARNINGS. `validate_verification.py` exits 0 for `enforcement` and `mutation-proof`.

## What changed, per item of the plan

| Item | Result |
| --- | --- |
| 1.2 + N1 | `classify_floor.py`: a floor for the declared complexity, measured from the git diff (files, lines, attack surfaces). It counts renames, measures against the merge base with the default branch, and keeps one classification per feature. Skill and classification events reach the timeline and `metrics.py`. |
| 1.1 + addendum A | A Claude Code `Stop` hook goal loop: an M+ feature cannot end the session while its gate fails. It blocks at most once per workspace state and escalates after `max_revisions` blocks, at a cost budget (US$ 25 by default), or with no progress. Escapes: an env switch and a recorded waiver. `ci_gate.py` and `init_project.py --with-ci` run the gate on pull requests and refuse a pull request that lowers, removes, or supersedes its own M+ spec. |
| 2.1 | `check_mutation.py`, standard library only: mutates the Python files listed in `Mutate:`. A minimum score in the spec becomes a gate criterion. Runs use a PID lock, never leave stale bytecode, and the gate refuses partial runs. The weak test of `weak-test-passes-gate` now fails the gate (score 0.0) in `mutation-catches-weak-test`. |
| 3.2 | One orchestrator model in Claude Code: the main session orchestrates. The `orchestrator` agent is no longer "use proactively". |
| 3.1 | `feature-development` merged into `feature`, `lean-investigation` into `debug` (42 skills). Skill descriptions cut from about 12,400 to about 9,100 characters. The inventory of the remaining overlaps is in `docs/progress/skill-inventory.md`. |
| 3.3 | MCP rules removed (your decision). Token economy condensed into the `CLAUDE.md` block. |
| 2.2 | ADR-0004 (a test runner declared once), proposed; nothing rewritten. |
| 4.1, 4.2 | ADR-0005 (queue and issue-to-PR flow) and ADR-0006 (isolation), design only. The minimal headless runner moves to Phase 2, where the harness is approved before it runs. |
| Found in passing | `layout.json` `proof_allow` never reached `check_proofs.py` (a bug from before 0.7.0); fixed and tested. |

Docs: README and README.pt-BR, `/help`, `agent-system/docs/cli.md`, the evals README, `CHANGELOG.md`, and version 0.7.0.

## Open (minor, for the user's decision)

- enforcement FIND-011: the agent can record `STOP_GATE_WAIVED` itself. Only an instruction says a waiver is the user's decision, and a waiver ends when the feature is classified again.
- enforcement FIND-015: commits made directly on the default branch reset the floor to XS, because there is no merge base to measure from. Documented.
- mutation-proof FIND-011: a narrow race remains when two runs take over the same dead lock at the same moment right after a crash. Fix when needed: an OS-level file lock.

## Pending by design

- ADR-0004, ADR-0005, and ADR-0006 wait for your decision.
- Further skill consolidation waits for the benchmark's `SKILL_USED` data.
- Phase 2: the benchmark harness, with its specs, hidden tests, and run plan, goes to you before anything runs.
