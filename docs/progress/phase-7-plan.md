# Phase 7 plan: the long task (three sessions)

Status: approved and frozen by the user. Nothing paid has run yet; the pilot comes first.

## What it measures that the medium task did not

The medium task is one session of about 500 lines. The Workbench claims value for work that outlives a session. This task runs three sessions on one project. Each session is a new Claude Code session in the same workspace, with the conversation gone. What survives is the repository and, for the plugin arms, `.agent-system/` (state, timeline, specs, tasks, reviews, lessons).

| session | SPEC.md | what the agent must do |
| --- | --- | --- |
| 1 | `specs/long-1.md` (the frozen medium spec, byte for byte) | build the event registration API |
| 2 | `specs/long-2.md` | add `PATCH /events/{id}` (rename, change capacity; raising capacity promotes the waiting list in order; lowering below seats taken is 409) and `GET /events/{id}/waitlist` |
| 3 | `specs/long-3.md` | add `GET /admin/outbox` (exactly one notification per transition, atomic, no duplicates under concurrency) and change a v1 rule: an admin may cancel a `checked_in` registration |

Prompts: session 1 uses the frozen `prompt.txt`; sessions 2 and 3 use `prompt-long-update.txt` (the spec was updated, the code is the previous version, keep everything else working). Same text for every arm. The agent never sees a later spec or any hidden test.

Two traps are built on purpose, both general software-engineering problems, not Workbench features:

- **Propagation across stages.** The outbox in session 3 must also record the promotions that session 2's `PATCH` performs. A session-3 agent that only reads the cancellation code misses them.
- **A reversed decision.** v1 said a checked-in registration can never be cancelled. v3 allows it for an admin, keeps 409 for no header, and makes an invalid header 401 for every registration. The agent must find every place that encoded the old rule.

## Hidden tests

Validated against `reference/long/app/main.py` (never given to an agent), in the Linux image, stable over repeated runs:

| suite | tests | reference at the matching stage | reference one stage behind |
| --- | --- | --- | --- |
| medium (stage 1 contract, run at every stage) | 47 | 47 pass | n/a |
| `test_stage2.py` | 28 | 28 pass | 27 fail, 1 pass |
| `test_stage3.py` | 21 | 21 pass | 19 fail, 2 pass |
| stage 3 total | 96 | 96 pass | n/a |

Each session's snapshot is scored on its own (`score.py`, projects `long-s1`, `long-s2`, `long-s3`): stage 1 runs the 47; stage 2 runs 47 + 28; stage 3 runs 47 + 28 + 21. A failure in an old test at a later stage is a regression. Concurrency tests (two workers, one SQLite file) are in each stage.

## Arms and runs

`baseline`, `workbench`, `lean` (with the spec-first check), same model (Sonnet 5.5), Claude Code 2.1.322, permissions, prompts and policy. 3 rounds per arm, so 9 runs of 3 sessions. Pilot first: round 1 of baseline and workbench only, to calibrate cost and time before the rest.

## Metrics

Per stage: hidden pass rate, regression (old-suite failures), new-feature failures, cost, time, tool calls before the first file write (a proxy for rebuilding context), interventions. At stage 3: ruff, mypy, mutation score. Afterwards, by reading the logs: whether session 2 or 3 contradicted a decision recorded earlier, what each arm read first, and whether the plugin arms used `.agent-system/` to resume. The blind review and the failure taxonomy as before.

## Caps and cost

Per run (all three sessions): US$ 12 and 90 minutes. Worst case 9 × 12 = US$ 108 at list price, which I do not expect. Estimate from the medium round (US$ 0.15 baseline, 0.35 to 0.7 plugin arms per session): about US$ 0.5 to 1.5 for a baseline run and 1.5 to 4 for a plugin arm, so roughly US$ 15 to 30 for all nine. The pilot (2 runs) shows whether that holds. On subscription auth the figure is a list-price basis, and what it uses from the plan is the open question from before.

## Hypotheses

- **H3**: over three sessions the Workbench arms regress less and contradict fewer earlier decisions than the baseline, because the specs, tasks and reviews in `.agent-system/` carry the context.
- **H0'**: Claude Code's own habits (reading the repo, running the existing tests) carry enough context, and the plugin only adds cost.
A result inside the dispersion is reported as inside the dispersion.

## Known limits

n = 3 per arm. One model, one domain. The specs, the tests and the reference are written by AI of the same family. The session boundary is simulated: a new `claude -p` in the same directory, which is what a returning user gets, but the prompt tells the agent to implement a new spec version, which is easier than "continue". There is no human in the loop except the fixed auto-answer policy. The stage 3 spec is the hardest; stage 1 and 2 results are the cleanest.

## Files

`benchmark/specs/long-{1,2,3}.md`, `prompt-long-update.txt`, `hidden/long/`, `reference/long/`, `runner/run_long.py`, `runner/report_long.py`, `roundlong.ps1`, hashes in `FROZEN-LONG.md`. Harness test: `python benchmark/runner/test_harness.py` (stub, includes a three-session pipeline and a check that no session sees a later spec).

## To approve

1. The three specs and the two traps.
2. The hidden tests and the scoring (regression counted per stage).
3. Caps US$ 12 and 90 minutes per run, and pilot first.
