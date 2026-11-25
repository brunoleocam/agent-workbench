# Medium round 2: effect of the PR 20 changes

Same medium spec, model, prompt, caps and policy as round 1. Arms `workbench` and `lean`, 3 runs each, Workbench at `main` after PR 20. The baseline was not re-run (it does not load the plugin). Raw runs are in `benchmark/runs-v2/` (gitignored); metrics from `benchmark/runner/process_metrics.py`. Valid arm proof in all 6 runs.

## Result

| run | first code write (tool call) | first spec write | spec-first denials | hidden tests | cost US$ | minutes |
| --- | --- | --- | --- | --- | --- | --- |
| round 1 workbench r1, r2, r3 | 2, 2, 2 | 9, 6, 6 | n/a | 47, 4, 47 | 0.29, 0.48, 0.29 | 1.6, 2.6, 1.5 |
| round 1 lean r1, r2, r3 | 2, 2, 2 | 10, 8, none | n/a | 4, 47, 47 | 0.31, 0.55, 0.56 | 2.1, 3.1, 3.3 |
| round 2 workbench r1, r2, r3 | 2, 2, 2 | 9, 7, 8 | 0, 0, 0 | 47, 47, 47 | 0.84, 0.29, 0.50 | 6.2, 1.7, 2.7 |
| round 2 lean r1, r2, r3 | 2, 2, 2 | none, 8, 6 | 0, 0, 0 | 2, 4, 47 | 0.19, 0.58, 0.27 | 1.2, 4.2, 1.6 |

## What the data say

- **Spec before code: no effect, and the reason is a defect in the PR 20 change.** The first code write is still tool call 2 in all 12 plugin runs, and the spec comes at 6 to 9. The new `PreToolUse` check never fired (0 denials in 6 runs). It matches `Edit`, `Write` and `MultiEdit`, but the agents create files with shell redirects (`cat > app/main.py <<'E'`) in the `Bash` tool, which the check does not see. The change as shipped cannot work for how these agents write.
- **Lean did not have the check at all**: the lean plugin copy keeps only the Stop hook by design, so in lean this round tested only the rule 03 text.
- **Shared-state rule: no visible effect.** The start race happened in 2 of 3 lean runs (2/47 and 4/47, `database is locked` and a refused connection), the same defect as round 1. The 3 workbench runs passed (round 1: 1 of 3 failed). With n = 3 that difference is inside the noise. Two of the passing workbench runs wrapped `PRAGMA journal_mode=WAL` in a retry, which the failing lean code lacked, but I cannot attribute that to the rule.
- **Cost and time**: no change beyond the dispersion (workbench US$ 0.29 to 0.84, lean US$ 0.19 to 0.58; one workbench run took 6.2 min).
- **Start race is still the one real quality defect.** It cost 2 of 6 plugin runs in round 2 and 2 of 6 in round 1.

## Verdict

The PR 20 changes were not shown to help. The spec-first check did not run, so this round neither confirms nor refutes the idea; it shows the implementation misses the `Bash` path. The multi-process rule did not stop the start race in lean. No difference here is outside the dispersion (n = 3).

## Next (proposed, not applied)

1. Make the spec-first check also look at `Bash` commands that write a production code file (`>`, `>>`, `tee`, `sed -i`), with the same limits (at most two denials, off switch, never after a classification or a spec). Add the hook to the lean copy so the arm tests it. Re-run workbench and lean, n = 3.
2. Do not conclude anything about the multi-process rule from this round. If the race matters, a deterministic check is more likely to work than a rule text: for example `check_proofs.py` starting the declared server with two workers.

# Round 3: spec-first check extended to Bash

Same task, model, prompt and caps. Workbench and lean, 3 runs each, commit `2055418` (the check reads `Bash` writes; lean now has the hook). Raw runs in `benchmark/runs-v3/` (gitignored). The hook denied the first production code write once in every run (6 of 6); the agent then recorded a classification (M in 5 runs, S then M in 1) and continued.

| run | first allowed code write | first spec write | hidden tests | cost US$ | minutes |
| --- | --- | --- | --- | --- | --- |
| workbench r1, r2, r3 | 6, 10, 5 | 14, 7, 4 | 47, 47, 47 | 0.64, 0.45, 0.65 | 3.9, 2.5, 3.5 |
| lean r1, r2, r3 | 5, 4, 6 | 4, 16, 5 | 47, 47, 47 | 0.42, 0.95, 0.67 | 2.5, 7.0, 3.9 |

Mean cost per run, US$: workbench 0.35 (round 1), 0.54 (round 2), 0.58 (round 3); lean 0.47, 0.35, 0.68; baseline 0.15.

## What the data say

- **The check works as a mechanism**: it fired in 6 of 6 runs and made the agent classify before writing code. Before it, the classification came at the end of the turn or never.
- **It only partly changes the order.** The spec came before the first allowed code write in 3 of 6 runs (lean r1, lean r3, workbench r3). In the other 3 the agent classified and wrote code first (code at 4, 6 or 10, spec at 7, 14 or 16). The check asks for a spec or a classification, so a classification satisfies it.
- **Hidden tests: 6 of 6 at 47/47**, against 4 of 6 in rounds 1 and 2 each (the start race failed 2 runs in each). This is the best round so far, but with n = 3 per arm it is inside the noise: 8 of 12 earlier runs against 6 of 6 now is not a result I would call significant. I cannot say whether the multi-process rule, the spec-first check or chance removed the start race.
- **Cost went up**, about +60% against round 1 for workbench (0.35 to 0.58) and +45% for lean. Part is the extra turn after the denial; part is the reviewer subagent (used in 4 of 6 runs here, 1 to 3 times in lean r2).
- Baseline remains 47/47 at US$ 0.15 and about 1 minute.

## Verdict

Mechanically the fix works and the medium task passed in all 6 runs. It does not change the H0 reading: the baseline is still 100% at a quarter to a fifth of the cost. The result is promising for reliability of the plugin arms, not evidence of a gain over the baseline.
