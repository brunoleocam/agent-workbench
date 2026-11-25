# Phase 4 report: medium round, arm D, final verdict

Branch `phase-2`. Workbench frozen at tag `workbench-frozen`, harness at `benchmark-frozen`. Nothing pushed.
Model `claude-sonnet-5-5`, Claude Code 2.1.322, same prompt, permissions, caps and auto-answer policy in every arm.
Raw numbers: `benchmark/results/simple-report.md` and `benchmark/results/medium-report.md`.

## Arms

- **baseline**: Claude Code only, `SPEC.md` in a git repo.
- **workbench**: the full plugin (42 skills, 10 agents, rules, hooks) plus `init_project.py --claude`.
- **lean (arm D)**: rules 00-08, `check_proofs.py`, `validate_verification.py`, the `reviewer` agent and the Stop hook. No skills.

Every run carries an `arm_proof.json` from the first `init` message; all 18 runs of the two rounds (plus pilot) are valid.

## Results

### Simple round (3 runs per arm: baseline and workbench)

| metric | baseline | workbench |
| --- | --- | --- |
| hidden tests | 43/43 in all runs | 43/43 in all runs |
| cost | about 1x | about 3.8x |
| time | about 1x | about 3.6x |
| mutation score | within dispersion | within dispersion |
| skills used | 0 | 0 of 42 |

### Medium round (3 runs per arm)

| metric | baseline | workbench | lean |
| --- | --- | --- | --- |
| hidden pass, first attempt | 1.00, 1.00, 1.00 | 1.00, **0.09**, 1.00 | **0.09**, 1.00, 1.00 |
| hidden pass, after re-scoring the 2 flaky runs | 1.00 x3 | 1.00 x3 | 1.00 x3 |
| mutation score (mean ± sd) | 0.73 ± 0.04 | 0.76 ± 0.07 | 0.71 ± 0.04 |
| ruff issues | 7.7 ± 0.6 | 5.7 ± 1.5 | 9.3 ± 3.2 |
| mypy errors | 0.7 ± 0.6 | 0.7 ± 0.6 | 1.0 ± 0 |
| cost per run, US$ | 0.15 ± 0.01 | 0.35 ± 0.11 | 0.47 ± 0.14 |
| time per run, min | 1.05 ± 0.29 | 1.92 ± 0.62 | 2.82 ± 0.66 |
| first-call tokens | 17.2k | 26.1k | 21.6k |
| blind review, correctness (0-5) | 4.0 ± 0 | 4.3 ± 0.6 | 4.3 ± 0.6 |
| blind review, security | 3.7 ± 1.2 | 4.7 ± 0.6 | 4.0 ± 0 |
| blind review, maintainability | 4.0 ± 0 | 4.0 ± 0 | 3.7 ± 0.6 |
| blind review, edge coverage | 3.0 ± 1.0 | 3.3 ± 0.6 | 3.3 ± 0.6 |
| interventions | 0 | 0 | 0 |
| skills used | 0 | 0 | 0 |
| reviewer subagent used | 0/3 | 1/3 | 2/3 |

Only cost, time and first-call tokens differ beyond the dispersion (workbench and lean higher). Everything else, including the blind review, is inside the dispersion.

### The two 4/47 runs

`medium-workbench-r2` and `medium-lean-r1` failed 43 of 47 hidden tests on the first attempt. The cause is an intermittent start failure of the agent's server with 2 workers: `PRAGMA journal_mode=WAL` in `init_db` runs in both processes at startup and sometimes raises `database is locked`, and uvicorn then stops the whole server. A repeat scoring of the same code gave 47/47 for both. A start check of 20 starts for each of the 9 medium runs gave 20/20 everywhere; an earlier 10-start check had one 9/10 (workbench-r1). So the defect is real but rare, and it sits in the agent's code, not in the hidden tests, which were not changed.

Both numbers are reported above and neither is hidden. The first-attempt row is what a user would have got; the re-scored row is what the code does when the race does not trigger. Either way the baseline is not worse, and it did not hit the race in the 3 runs.

## Failure taxonomy (medium round)

| type | baseline | workbench | lean |
| --- | --- | --- | --- |
| interpretation (spec misread) | 0 | 0 | 0 |
| execution (code that fails at run time) | 0 | 1 (WAL start race) | 1 (WAL start race) |
| consistency (spec, code and tests disagree) | n/a | spec written after the code in 3/3 | spec written after the code in 3/3 |
| propagation (a gate or proof that does not carry over) | n/a | 1 `no_progress` escalation | 2 `no_progress` escalations |

The dominant failure is execution under concurrency, and the Workbench did not catch it: neither the Stop gate nor the reviewer ran two workers against one file. The proof that `check_proofs.py` runs was a 1-check, in-process test.

## Findings about the Workbench itself

1. **Spec follows code.** In all 6 plugin runs the first code write is tool call 2 and the spec comes at call 6-10. The rules ask for the opposite order. The `classify_floor` and Stop gate fire only at the end of the turn, so they force documents after the fact. P2 (already applied) warns about it; it does not prevent it.
2. **Skills are never used.** 0 of 42 in simple, 0 of 42 in medium (0 in lean by construction). The choice-space cost is paid anyway: about +9k tokens at the first call for workbench, +4k for lean, measured.
3. **Stop gate blocks 2-4 times per run and most runs fail the gate at least once** before passing. It adds minutes and dollars; in these runs it did not change a test result.
4. **`no_progress` still escalates early after P1.** In `medium-workbench-r2` the gate blocked twice and escalated at the second stop: between the two stops the agent only replied and a `reviewer` subagent was running, so the document digest did not change yet. The reviewer's output landed after the escalation, and the gate later passed. Reading: the progress check treats "a subagent is running" as "no progress". This is a general defect (a subagent in flight is progress), not a benchmark artifact. **Proposed fix, not applied:** do not escalate with `no_progress` while a `SUBAGENT_STARTED` has no matching `SUBAGENT_STOPPED` in the timeline.
5. **Self-approval of the spec** (seen in the simple round) was not repeated in a way that changed anything in the medium round.

## Hypotheses

- **H1** (the Workbench improves quality on the medium project): **not supported.** Baseline got 100% on every run. The Workbench arms match it after re-scoring and are worse on first attempt. The blind review leans slightly to workbench on security (4.7 vs 3.7) but the standard deviation of the baseline is 1.2: inside the dispersion.
- **H0** (with a frontier model and Claude Code as the baseline, the Workbench only adds cost and time): **the data fit it.** Cost is 2.4x (workbench) and 3.2x (lean); time 1.8x and 2.7x, with no measurable quality gain. This is for a frontier model on two small, well-specified API projects.
- **H2** (arm D, the verification core, delivers most of the gain): **not supported.** There is no gain to deliver at this size, and arm D cost more than the full Workbench (more reviewer calls and gate rounds), not less.
- **M-level ceremony** (IDs, EARS + Given/When/Then, a router with 6 flags): in the medium round the work ran as M by floor in every plugin run. The ceremony did not change the hidden or mutation results; it added the documents, which came after the code. No outcome effect is visible.

## Cost per quality point

Not meaningful. Quality (hidden pass rate) is 1.00 for every arm once the race run is re-scored, so extra cost buys 0 points; on first attempt the extra arms lost points. The report script prints a negative number for that reason and the report says "not meaningful".

## Verdict

- **Dimensions.** On hidden tests, mutation score, lint and typecheck there is no measurable gain. On the blind review there is a small, not significant, security lead for workbench.
- **Cost-benefit.** Negative at this task size and with this model: 2.4x to 3.2x the cost and 1.8x to 2.7x the time for the same hidden-test result.
- **Task size.** The projects were small (about 500 lines, 1-2 minutes for the baseline). The Workbench is built for work that outlives a session, has several people, or needs an audit trail. This benchmark does not test that, and says nothing for or against it.

## What to cut, what to reinforce

Cut or make opt-in:
- The skill catalogue as always-loaded text (about +9k first-call tokens, 0 uses).
- The M-level ceremony for work that fits in one session.
- The Stop gate's classification block when the change is already covered by the tests the agent just ran.

Reinforce:
- **Concurrency proof.** The one real failure was a race the agent could not see. A rule that asks for a multi-process test of any shared-state code (WAL pragma, locks, token stores) is the only change the data points to.
- **Spec before code.** Make the first code write blocked until `docs/specs/<feature>.md` exists for M, by a PreToolUse check, not by an end-of-turn gate.
- **`no_progress` with a subagent in flight** (finding 4): fixed after approval, see below.

## Limits

n = 3 per arm and project. One model (Sonnet 5.5), one domain family (HTTP API on FastAPI and SQLite). Specs, hidden tests and the blind reviewer are written by AI of the same family. Subscription auth: `total_cost_usd` is a list-price figure and the cost cap was never reached, so enforcement is untested. Two of nine medium runs had a start race, so the pass rate has a coarse floor; with n = 3 one run moves the mean by 0.3. No arm was run on a long, multi-session or multi-person task, which is where the Workbench claims its value.

## Not done

- No push or merge. Branches: `phase-2` holds Phases 2-4. The medium report and `.gitignore` change are committed together with this file.
- The fix in finding 4 is a proposal. Nothing was changed in the Workbench after the freeze (`workbench-frozen`).

## Applied after approval

Finding 4 is fixed in `agent-system/scripts/stop_gate.py`: `no_progress` no longer escalates while a `SUBAGENT_STARTED` has no matching `SUBAGENT_STOPPED` since the gate item began. `max_blocks` still caps the loop. New test `test_stop_does_not_escalate_while_a_subagent_runs`. Suite 210/210, evals 14/14. This changes the Workbench after the `workbench-frozen` tag, so the medium-round numbers above were taken without it and were not re-run.
