# Phase 3 report: simple round (Workbench 0.7.0 vs plain Claude Code)

Frozen inputs: tag `benchmark-frozen`. Model `claude-sonnet-5-5`, Claude Code 2.1.322, 3 rounds per arm, subscription auth (`total_cost_usd` is filled, list-price basis). Raw table: `benchmark/results/simple-report.md`. No blind review was run for this round: both arms pass 43/43 hidden tests, so there is little for it to separate; I can run it if you want it.

## Result

| metric | baseline | workbench | reading |
| --- | --- | --- | --- |
| hidden tests passing | 100% ± 0 | 100% ± 0 | tie |
| mutation score of own tests | 0.62 ± 0.10 | 0.72 ± 0.03 | Workbench higher, but the gap (0.10) equals the baseline spread: inconclusive |
| ruff / mypy | 9 ± 1 / 0 | 10 ± 2.6 / 0 | tie |
| cost (US$) | 0.106 ± 0.007 | 0.402 ± 0.015 | 3.8x, clear |
| wall time (min) | 0.8 ± 0.3 | 2.9 ± 0.6 | 3.6x, clear |
| first model call (tokens) | 17,227 | 26,108 | +8,900 tokens of choice space at session start, in every call |
| interventions | 0 | 0 | not comparable, see below |
| skills used | 0 | 0 | 42 skills loaded, none invoked |
| subagents | 0 | 1 (`reviewer`, 3/3) | the independent review ran |

Verdict for the simple task: same quality on every measured dimension (the mutation gap is inside the noise), at about 4x the cost and time. As expected, the round measures overhead, and the overhead is not small. It is acceptable only if you value the audit trail (spec, tasks, proofs, an independent review) for its own sake; it did not change the outcome here. Hypotheses H0/H1 are not decided by this round.

## What the logs show about the Workbench

1. **The classification expectation was wrong.** I expected XS or S. In 3 of 3 runs the measured floor was M (5 files, about 470 lines, tests included), so the full M flow ran. In r1 the agent declared S first and the floor corrected it to M (the floor worked as designed).
2. **Spec after code (retrofit).** In 3 of 3 runs the agent wrote the whole implementation first (about step 11 of the stream), and only the Stop gate ("unclassified change") made it classify, then write the spec and tasks, run proofs, and call the reviewer. The ceremony is a bolt-on after the fact, not a plan. Nothing checks the order. The rules did not change the model's habit; the hook did.
3. **Premature "no_progress" escalation, 3 of 3.** After the first block the agent writes spec, tasks, review. The progress check uses `workspace_fingerprint`, which excludes the harness docs on purpose (so a review does not invalidate itself). So writing those artifacts counts as no progress, and the gate escalates to the user ("stopped again without changing the code") while the agent was in fact advancing. In headless mode nobody answers and the agent carried on, so it cost nothing here; interactively it would interrupt the user for nothing.
4. **Self-approval and the intervention metric.** The agent treated "SPEC.md is final" as approval of the spec and set `status: approved` itself, so no human node fired and interventions are 0. That makes the metric uninformative for this round (it will matter on the medium one, where the policy may fire). The independent review, however, was real: a separate `reviewer` subagent wrote it in all three runs.
5. **Skills never used.** 0 of 42 skills in 3 runs, while their descriptions cost about 3,100 tokens of every call (and about 9,000 more tokens at session start in total, measured). The work went through rules and scripts, not skills. Strong candidate for the cut list, pending the medium round.
6. **"Stop hook error occurred" notice** appears in the stream when the gate blocks. Cosmetic, but it is not a failure; worth confirming that blocking uses the documented JSON decision rather than an error exit.
7. Workbench wrote fewer output tokens than the baseline (2.5k vs 5.5k) with a higher mutation score, probably because the extra checking replaced some of its own test writing. Not enough data to read into it.

## Proposed general fixes (not applied, waiting for your decision)

| # | Fix | Why it is general | Risk |
| --- | --- | --- | --- |
| P1 | Stop gate progress also hashes the harness artifacts the gate reads (spec, tasks, review, proof files), so writing them counts as progress | Any M+ feature does this; it is a bug in the progress measure, not a benchmark tweak | Low. Needs a regression test and an eval step |
| P2 | `validate_verification` warns (does not fail) when production files were edited before the spec was validated, from the timeline order | Makes the retrofit visible to the reviewer and the user | Low; warning only |
| P3 | Confirm the Stop block uses `{"decision":"block"}` with exit 0 and no error notice | Cleaner UX | Low |

Not proposed: lowering the M floor (for example counting tests less) to make this benchmark cheaper. That would be tuning to the spec. The floor question should wait for the medium round, where it matters in the other direction.

Not fixed on purpose: skills never used, the 3-4x overhead. Those are findings for the Phase 4 cut list.

## Costs

Pilot (2 runs, kept in `benchmark/runs-pilot`, not in the table): about US$ 0.38. Round: 6 runs, about US$ 1.5 list-price equivalent.
