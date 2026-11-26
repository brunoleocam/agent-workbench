# Phase 7 report: the long task (three sessions)

Plan and design: `docs/progress/phase-7-plan.md`. Inputs frozen at tag `long-frozen` (hashes in `benchmark/FROZEN-LONG.md`, unchanged through all runs). 9 runs: baseline, workbench and lean, 3 rounds each, 3 sessions per run, model Sonnet 5.5, Claude Code 2.1.322. All 9 runs valid and `finished`; no intervention was needed in any session. Raw data in `benchmark/runs-long/` (gitignored); table from `benchmark/runner/report_long.py`.

## Results

Hidden tests per stage (47, 75 and 96 tests):

| arm | stage 1 | stage 2 | stage 3 | regressions (old tests failing later) |
| --- | --- | --- | --- | --- |
| baseline | 47/47 x3 | 75/75 x3 | 96/96 x3 | 0 |
| workbench | 47/47 x3 | 75/75 x3 | 96/96 x3 | 0 |
| lean | 47/47 x3 | 75/75 x3 | 96/96 x3 | 0 |

Per run, all three sessions (mean ± sd, n = 3):

| metric | baseline | workbench | lean |
| --- | --- | --- | --- |
| cost US$ | 0.37 ± 0.00 | 1.10 ± 0.28 | 0.78 ± 0.19 |
| minutes | 1.9 ± 0.1 | 8.2 ± 4.7 | 6.3 ± 3.4 |
| cost of session 1 / 2 / 3 | 0.14 / 0.09 / 0.14 | 0.79 / 0.14 / 0.17 | 0.52 / 0.12 / 0.14 |
| tool calls before the first write, session 2 / 3 | 3.0 / 4.7 | 4.3 / 5.0 | 4.0 / 4.7 |
| mutation score of the agent's tests, stage 3 | 0.61 ± 0.07 | 0.79 ± 0.09 | 0.79 ± 0.05 |
| ruff issues, stage 3 | 12.7 ± 3.5 | 14.3 ± 3.5 | 9.7 ± 4.2 |
| mypy errors, stage 3 | 2.7 ± 4.6 | 1.7 ± 0.6 | 1.0 ± 1.7 |

The blind review was not run for this task.

## What the data say

1. **No difference in what the hidden tests measure.** Every arm passed every stage, including both traps: the stage 3 outbox records the promotions of the stage 2 `PATCH`, and the reversed check-in rule was applied everywhere. No regression in 27 sessions. The task hit a ceiling: three sessions of about 500 to 700 lines are within what this model does reliably with nothing but the repository.
2. **Context came from the repository, in every arm.** At the start of sessions 2 and 3 every agent read `SPEC.md` and the code and wrote within 3 to 5 tool calls. The plugin arms did not read `.agent-system/` or `docs/` in sessions 2 and 3 (0 or 1 reference in 12 sessions). So the Workbench's memory did not carry the context; the code did.
3. **The Workbench was idle after session 1.** In sessions 2 and 3 there was no spec-first denial (a spec already existed), no Stop gate block, and no classification. In 4 of 6 plugin runs the feature had been closed in session 1 (gate passed); in 2 it stayed open after an escalation. Either way the gate did not treat the new spec version as new work.
4. **The Workbench's own documents drifted.** In 6 of 6 plugin runs `docs/specs/` still describes version 1 after session 3: no `PATCH`, no outbox, the old check-in rule. The code is right and the Workbench's spec is wrong. This is the failure the Workbench exists to prevent, produced by the Workbench.
5. **Cost.** Session 1 carries almost all the extra cost (workbench 0.79 against 0.14), with Stop gate rounds (2 to 5 blocks) and the reviewer subagent. Sessions 2 and 3 cost about what the baseline costs, because nothing of the plugin runs. Total: workbench 3.0x, lean 2.1x the baseline.
6. **Mutation score is the one quality signal.** The plugin arms' own tests kill more mutants at stage 3: 0.79 against 0.61. The difference (0.18) is larger than the largest standard deviation (0.09), so by the rule set before the benchmark it is outside the dispersion, with n = 3. It did not appear in the medium rounds (0.73, 0.76, 0.71), so I read it as a signal worth re-testing, not a result. A plausible cause is the session 1 gate and reviewer pushing for more tests; the hidden tests did not need them.

## Hypotheses

- **H3** (over three sessions the Workbench arms regress less and contradict fewer earlier decisions): **not supported.** Nobody regressed or contradicted a decision, and the plugin arms did not use their memory to resume.
- **H0'** (Claude Code carries enough context by reading the repository; the plugin adds cost): **the data fit it** for this task size. The one counter-signal is the mutation score.
- Overall verdict of Phase 4 unchanged: at these sizes, with this model, the Workbench adds cost and time without a measurable gain in what users get, and now also shows that its documents go stale across sessions.

## Problems found in the Workbench (proposals, not applied)

1. **No re-entry after a closed feature.** When a later session changes behaviour that a closed feature covers, nothing asks for the spec to be updated. Proposal: the Stop gate reopens a closed feature when the workspace fingerprint changes beyond the files recorded at close and the change is above the floor, and asks for the spec, tasks and proofs to be updated (or for a new feature). Same if the project's requirements file (`SPEC.md` or a declared requirements path) changed since the feature was classified.
2. **Spec drift is not checked across sessions.** `check_drift.py` exists but no hook runs it at session start. Proposal: at `SessionStart`, run the drift check for open and recently closed features and put a one-line warning in the session context.
3. Escalation in session 1 (`max_blocks` in 1 of 6 runs) still costs the most; the gate rounds are where the extra cost goes.

## Limits

n = 3 per arm. One model, one domain. Specs, hidden tests and reference written by AI of the same family. The task turned out too easy to separate the arms on correctness (ceiling); a harder task (more sessions, a larger codebase, conflicting requirements) is needed to test the claim, and would need a new freeze. The session boundary is a new `claude -p` in the same directory, and the prompt says the spec changed, which helps every arm equally. Subscription auth: costs are list-price figures.

## Applied after approval

Problems 1 and 2 are fixed together in `agent-system/scripts/reentry.py`, used by `stop_gate.py` and `hook.py`. When a feature's gate passes, the classification records a git tree of the working tree (written through a temporary index; the user's index and history do not change) and a digest of the feature's spec. On a later `Stop` with no open feature, if the code moved at least to the S floor since that tree and the spec did not, the gate blocks once per workspace state and asks to update the spec, tasks and proofs (or start a new feature) and reclassify, which reopens the gate. `SessionStart` adds the same warning to the session context. An XS change does not trigger it, and a spec that moved with the code does not either. `check_drift.py` was not used: it detects plan drift for pending tasks, not spec drift. Tests: `test_closed_feature_reopens_when_code_moves_and_its_spec_does_not`, `test_small_change_after_close_does_not_reopen`. Suite 214/214, evals 14/14, harness test OK. Not measured by a new long round; the long task's frozen inputs are unchanged.
