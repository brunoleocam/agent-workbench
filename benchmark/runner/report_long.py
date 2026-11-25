#!/usr/bin/env python3
"""Report for the long task: per arm and stage, hidden pass rate, regression, cost, time, context rebuilt.

  python benchmark/runner/report_long.py [--runs-dir benchmark/runs-long]

Regression of stage k = hidden tests of earlier stages that fail at stage k (the medium suite is the stage 1 contract and
stage 2 tests are run again at stage 3). New-feature failures are the tests that belong to stage k only.
"""
import argparse
import json
import statistics as st
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]

def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def split(score, k):
    """(failed old-suite tests, failed new tests, passed, total) for stage k."""
    hidden = score["hidden"]
    failed = hidden.get("failed_names") or []
    new_names = NEW_TESTS.get(k, set())
    old_failed = [n for n in failed if n.split("[")[0] not in new_names]
    new_failed = [n for n in failed if n.split("[")[0] in new_names]
    return len(old_failed), len(new_failed), hidden["passed"], hidden.get("expected_total") or hidden["total"]


def names_of(path):
    import re
    return {m for m in re.findall(r"^def (test_\w+)", Path(path).read_text(encoding="utf-8"), re.M)}


NEW_TESTS = {2: names_of(BENCH / "hidden/long/test_stage2.py"),
             3: names_of(BENCH / "hidden/long/test_stage3.py")}


def cell(values, fmt="{:.2f}"):
    values = [v for v in values if v is not None]
    if not values:
        return "n/a"
    if len(values) == 1:
        return fmt.format(values[0])
    return (fmt + " ± " + fmt).format(st.mean(values), st.stdev(values))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", default=str(BENCH / "runs-long"))
    a = ap.parse_args()
    rows = {}
    for rd in sorted(Path(a.runs_dir).glob("long-*-r*")):
        run = load(rd / "run.json")
        if not run or not run.get("valid"):
            continue
        for k in (1, 2, 3):
            stage = load(rd / f"s{k}" / "run.json")
            score = load(rd / f"s{k}" / "score.json")
            if stage:
                rows.setdefault((run["arm"], k), []).append((rd.name, stage, score))
    print("# Long task report\n")
    print("| arm | stage | n | hidden pass rate | old-suite failures (regression) | new-feature failures | cost US$ | minutes | calls before first write | interventions |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for (arm, k), items in sorted(rows.items()):
        rates, old, new = [], [], []
        for _, _, score in items:
            if score:
                o, n, passed, total = split(score, k)
                rates.append(passed / total)
                old.append(o)
                new.append(n)
        print(f"| {arm} | {k} | {len(items)} | {cell(rates)} | {cell(old, '{:.1f}')} | {cell(new, '{:.1f}')} | "
              f"{cell([s['usage']['cost_usd'] for _, s, _ in items if 'usage' in s])} | "
              f"{cell([s['wall_seconds'] / 60 for _, s, _ in items if 'wall_seconds' in s], '{:.1f}')} | "
              f"{cell([s.get('calls_before_first_write') for _, s, _ in items], '{:.1f}')} | "
              f"{cell([s.get('intervention_count') for _, s, _ in items], '{:.1f}')} |")
    print("\nRuns whose stop reason is not `finished`:")
    for rd in sorted(Path(a.runs_dir).glob("long-*-r*")):
        run = load(rd / "run.json")
        if run and run["stop_reason"] != "finished":
            print(f"- {rd.name}: {run['stop_reason']}")


if __name__ == "__main__":
    main()
