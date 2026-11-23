#!/usr/bin/env python3
"""Comparative report from benchmark/runs/*: mean and dispersion per arm and metric.

  python benchmark/runner/report.py [--project simple] [--out benchmark/report-simple.md]

Optional hand-written inputs in benchmark/runs/:
  failures.json      [{"run_id": ..., "category": "interpretation|execution|consistency|propagation", "note": ...}]
  blind_results.json {"<run_id>": {"correctness": 0-5, "security": 0-5, "maintainability": 0-5, "edge_coverage": 0-5}}
                     (written by blind.py unseal; never edit by hand after the review)
"""
import argparse
import json
import statistics as st
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
ARMS = ["baseline", "workbench", "lean"]


def load(runs_dir, project):
    rows = []
    for rd in sorted(runs_dir.glob(f"{project}-*-r*")):
        if not (rd / "run.json").exists():
            continue
        run = json.loads((rd / "run.json").read_text(encoding="utf-8"))
        sc = json.loads((rd / "score.json").read_text(encoding="utf-8")) if (rd / "score.json").exists() else {}
        rows.append((run, sc))
    return rows


def metrics_of(run, sc, blind):
    h = sc.get("hidden") or {}
    mu = (sc.get("mutation") or {}).get("score")
    b = blind.get(run["run_id"]) or {}
    return {
        "hidden_pass_rate": h.get("pass_rate"),
        "mutation_score": mu,
        "ruff_issues": sc.get("ruff_issues"),
        "mypy_errors": sc.get("mypy_errors"),
        "cost_usd": run["usage"]["cost_usd"],
        "minutes": run["wall_seconds"] / 60,
        "output_tokens": run["usage"]["output_tokens"],
        "cache_read_tokens": run["usage"]["cache_read_input_tokens"],
        "first_call_tokens": run.get("first_call_tokens"),
        "interventions": run["intervention_count"],
        "skills_used": len(run.get("skills_used", [])),
        "agents_used": len(run.get("agents_used", [])),
        "review_correctness": b.get("correctness"),
        "review_security": b.get("security"),
        "review_maintainability": b.get("maintainability"),
        "review_edge_coverage": b.get("edge_coverage"),
    }


def ms(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None, None, 0
    return st.mean(v), (st.stdev(v) if len(v) > 1 else 0.0), len(v)


def fmt(m, s, n):
    return "n/a" if m is None else f"{m:.3g} ± {s:.2g} (n={n})"


def verdict(a, b):
    (ma, sa, na), (mb, sb, nb) = a, b
    if ma is None or mb is None:
        return ""
    d = mb - ma
    if min(na, nb) < 2 or abs(d) <= max(sa, sb):
        return "within dispersion"
    return "workbench higher" if d > 0 else "workbench lower"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--runs-dir", default=str(BENCH / "runs"))
    ap.add_argument("--out")
    a = ap.parse_args()
    rdir = Path(a.runs_dir)
    blind = json.loads((rdir / "blind_results.json").read_text()) if (rdir / "blind_results.json").exists() else {}
    fails = json.loads((rdir / "failures.json").read_text()) if (rdir / "failures.json").exists() else []
    rows = load(rdir, a.project)
    by = {}
    for run, sc in rows:
        by.setdefault(run["arm"], []).append((run, sc))
    out = [f"# Benchmark report: {a.project}", ""]
    invalid = [r["run_id"] for r, _ in rows if not r.get("valid")]
    if invalid:
        out += [f"INVALID runs (arm proof failed, excluded): {', '.join(invalid)}", ""]
    arms = [x for x in ARMS if x in by]
    table = {arm: [metrics_of(r, s, blind) for r, s in by[arm] if r.get("valid")] for arm in arms}
    out += ["| metric | " + " | ".join(arms) + " | baseline vs workbench |", "|---|" + "---|" * (len(arms) + 1)]
    names = list(next(iter(table.values()))[0].keys()) if table and next(iter(table.values())) else []
    for name in names:
        cells = {arm: ms([m[name] for m in table[arm]]) for arm in arms}
        v = verdict(cells["baseline"], cells["workbench"]) if "baseline" in cells and "workbench" in cells else ""
        out.append(f"| {name} | " + " | ".join(fmt(*cells[arm]) for arm in arms) + f" | {v} |")
    if "baseline" in table and "workbench" in table:
        pb, pw = ms([m["hidden_pass_rate"] for m in table["baseline"]])[0], ms([m["hidden_pass_rate"] for m in table["workbench"]])[0]
        cb, cw = ms([m["cost_usd"] for m in table["baseline"]])[0], ms([m["cost_usd"] for m in table["workbench"]])[0]
        out += ["", "## Cost per quality point"]
        if None not in (pb, pw, cb, cw) and abs(pw - pb) > 1e-9:
            out.append(f"Extra cost US$ {cw - cb:.2f} for {100 * (pw - pb):+.1f} points of hidden pass rate: "
                       f"US$ {(cw - cb) / (100 * (pw - pb)):.2f} per point (not meaningful if the verdict above is 'within dispersion').")
        else:
            out.append("No difference in hidden pass rate: the extra cost buys no measured quality on this metric.")
    wb = [r for r, _ in rows if r["arm"] == "workbench" and r.get("valid")]
    if wb:
        out += ["", "## Workbench-only", "", "| run | stop | skills used | agents used |", "|---|---|---|---|"]
        for r in wb:
            out.append(f"| {r['run_id']} | {r['stop_reason']} | {', '.join(sorted(set(r['skills_used']))) or '-'} | {', '.join(sorted(set(r['agents_used']))) or '-'} |")
    if fails:
        out += ["", "## Failure taxonomy", "", "| arm | interpretation | execution | consistency | propagation |", "|---|---|---|---|---|"]
        for arm in arms:
            c = Counter(f["category"] for f in fails if f["run_id"].startswith(f"{a.project}-{arm}-"))
            out.append(f"| {arm} | {c['interpretation']} | {c['execution']} | {c['consistency']} | {c['propagation']} |")
    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
