# Benchmark: Claude Code with and without Agent Workbench

Status: harness built and tested with a stub (no paid run yet). Specs are frozen once approved.

## What is compared

| | baseline | workbench |
| --- | --- | --- |
| Claude Code | 2.1.322 (pinned in the image) | same |
| Model, permissions, prompt, caps | identical (`run.py`, `prompt.txt`) | identical |
| Plugin | none | working-tree copy of this repo via `--plugin-dir /opt/plugin` (commit recorded in `run.json`) |
| Project | git repo with `SPEC.md` | same, plus `init_project.py --claude` (what `/init-agent-system` runs) |
| User config | none: fresh container home, `--setting-sources project,local` | same |

Proof of arm, per run (`arm_proof.json`): the `init` message of the first stream. A baseline run that lists the plugin, any `agent-workbench:` skill or agent, is marked INVALID and excluded from the report. A workbench run that does not list the plugin from `/opt/plugin` is INVALID too.

## Arm D, `lean` (medium round only)

Same project init as `workbench`, but the plugin copy has only: rules 00 to 08 (no token-economy rule), the verification and gate scripts, the `reviewer` agent, and the `Stop` hook. No skills, no other agents, no other hooks. The arm proof requires zero plugin skills and exactly the reviewer agent. Limit: the rules text still mentions skills that do not exist in this arm.

## Projects (frozen)

- `specs/simple.md`: warehouse stock API (CRUD, in/out movements, no negative balance under concurrency, low-stock report). 
- `specs/medium.md`: event registration API (limited seats, waiting list, cancellation with promotion, admin auth shared across 2 workers, check-in codes, no overbooking under concurrency).
- Both run with `uvicorn --workers 2` on one SQLite file, so a lock held in process memory fails the concurrency tests. SQLite only: Postgres was dropped to keep the container simple and the tests deterministic.
- The medium domain is close to "ticketing", which you asked to avoid. I kept your spec; say if you want another domain (for example room booking) before freezing.

## Hidden acceptance tests (`hidden/`)

Black box over HTTP; the test process starts the project's server itself. 43 tests for simple, 47 for medium, with limits, negative cases, concurrency, restart persistence, auth before validation. Validated against reference implementations in `reference/` (all 43 and 47 pass); the references are only used for that and are never given to an agent.

Isolation: the agent container gets `SPEC.md`, and in the workbench arm the plugin copy (only `.claude-plugin agent-system agents hooks rules skills`). `hidden/`, `reference/` and `specs/` of other projects are never copied. A test (`test_harness.py`) asserts this. Scoring runs in a second, new container with no API token.

## Flow per run

1. `run.py`: fresh workspace, `docker create` + `docker cp` (no bind mount), non-root user, 2 CPU / 4 GB.
2. `claude -p` with `stream-json`, `--dangerously-skip-permissions` (safe inside the container), `--max-budget-usd` set to what remains of the cap, wall-clock cap.
3. If the final message ends on a question, the harness answers from `policy.json` through `--resume` (same rule for both arms). Each answer is an intervention (max 6), logged with node and question.
4. `score.py`: hidden tests (pass rate), ruff issues, mypy errors, mutation score of the agent's own tests (`mutation.py`, the same tool for both arms, 60 seeded mutants), written to `score.json`.
5. `blind.py`: pairs baseline and workbench of a round as A and B (random), strips arm markers, a fresh reviewer applies a fixed rubric (correctness, security, maintainability, edge coverage, 0 to 5, plus a defect list); the key is only read at `unseal`.
6. `report.py`: mean ± standard deviation per metric and arm, flags a difference as "within dispersion" when it is smaller than the larger standard deviation or n is below 2; cost per quality point; failure taxonomy from `runs/failures.json` that I fill by reading the logs.

Choice-space cost: `choice_space.py` (static: 42 skills, 10 agents, about 12,400 characters of descriptions, about 3,100 tokens, plus 20.8 KB of rules) and `first_call_tokens` in each `run.json` (measured difference of the first model call between arms). Wrong skill or agent choices are scored by hand from `skills_used` and `agents_used` plus the streams.

## Caps and cost

Per run: simple US$ 8 and 45 minutes, medium US$ 20 and 100 minutes (the lower cap you chose, to be confirmed). 2 arms × 3 rounds × 2 projects = 12 runs, worst case US$ 168 plus 6 blind reviews (US$ 3 cap each). Those are caps; I expect well below them for the baseline.

## Authentication risk (you chose `setup-token`)

`setup-token` uses the subscription. Open points I can only verify with a first paid call:
1. Whether `--max-budget-usd` is enforced for subscription auth, and whether `total_cost_usd` is filled. If not, `run.json` still has tokens and time, and the cap becomes the wall-clock cap.
2. The plan quota may run out in the middle of a round and bias against the arm that runs later. The runner alternates nothing by itself: I run the two arms of a round back to back, baseline first in odd rounds and workbench first in even rounds.
3. Rate limits turn a run into `error:*` in `stop_reason`; such a run is repeated, never scored as a failure.

## Commands (after approval)

```powershell
docker build -t agent-workbench-bench:1 benchmark/docker
$env:CLAUDE_CODE_OAUTH_TOKEN = "<from claude setup-token>"
python benchmark/runner/run.py --project simple --arm baseline --round 1
python benchmark/runner/score.py --run benchmark/runs/simple-baseline-r1
python benchmark/runner/report.py --project simple
```

Harness self-test, no network and no cost: `python benchmark/runner/test_harness.py`.

## Known limits of this design

- Specs, tests and the rubric reviewer are written by AI; the blind reviewer is the same model family as the agents.
- One model, one domain family, n = 3.
- Arm markers can still leak into code (comments, test names); stripping removes the files, not the style.
- The intervention policy is a text rule; a question without a question mark is not caught, in both arms.
