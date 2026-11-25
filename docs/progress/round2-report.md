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
