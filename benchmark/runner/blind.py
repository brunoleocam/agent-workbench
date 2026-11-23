#!/usr/bin/env python3
"""Blind pairwise review. Per (project, round) the baseline and workbench codes become A and B,
randomly assigned. The reviewer sees only code; arm markers are stripped. The key stays in
runs/blind_key.json and is read only by `unseal`.

  python blind.py pack   --project simple --round 1     # builds benchmark/runs/blind/<project>-r<N>/{A,B}
  python blind.py review --project simple --round 1     # claude -p, fixed rubric, writes review.json
  python blind.py unseal                                # maps A/B scores back to runs -> blind_results.json
"""
import argparse
import json
import random
import shutil
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
RUNS = BENCH / "runs"
STRIP = {".git", ".agent-system", ".claude", ".cursor", "CLAUDE.md", "SPEC.md", "docs", "__pycache__",
         ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv", "venv", "node_modules", ".coverage", "*.db"}
RUBRIC = """You are an independent code reviewer. Two implementations of the same specification are in the
directories A/ and B/. The specification is in SPEC.md. Review both with the same rubric. Read the code and the tests;
you may run read-only commands. You do not know how either was produced, and must not guess.

Score each dimension from 0 to 5 (5 = excellent, 0 = broken) for A and for B:
- correctness: does the code do what SPEC.md says, including edge and error cases and concurrent use?
- security: authentication, authorization, input validation, secrets, SQL injection, timing, token handling.
- maintainability: structure, naming, duplication, dead code, configuration, readability.
- edge_coverage: do the tests exercise limits, negative cases, and concurrency, and would they catch a regression?

List concrete defects (file:line, severity blocker|major|minor, one sentence) for each implementation.
Answer with ONE JSON object and nothing else:
{"A": {"correctness": n, "security": n, "maintainability": n, "edge_coverage": n, "defects": [{"where": "", "severity": "", "what": ""}]},
 "B": {...}}"""


def ignore(_d, names):
    return [n for n in names if n in STRIP or n.endswith(".db") or n.endswith(".pyc")]


def pack(project, rnd):
    key_path = RUNS / "blind_key.json"
    key = json.loads(key_path.read_text()) if key_path.exists() else {}
    tag = f"{project}-r{rnd}"
    srcs = {arm: RUNS / f"{project}-{arm}-r{rnd}" / "ws" for arm in ("baseline", "workbench")}
    for s in srcs.values():
        if not s.exists():
            raise SystemExit(f"missing {s}")
    order = ["baseline", "workbench"]
    random.shuffle(order)
    dest = RUNS / "blind" / tag
    if dest.exists():
        raise SystemExit("already packed")
    for label, arm in zip("AB", order):
        shutil.copytree(srcs[arm], dest / label, ignore=ignore)
    shutil.copy(BENCH / "specs" / f"{project}.md", dest / "SPEC.md")
    key[tag] = {"A": f"{project}-{order[0]}-r{rnd}", "B": f"{project}-{order[1]}-r{rnd}"}
    key_path.write_text(json.dumps(key, indent=1))
    print("packed", dest)


def review(project, rnd, claude_bin):
    dest = RUNS / "blind" / f"{project}-r{rnd}"
    p = subprocess.run([claude_bin, "-p", RUBRIC, "--output-format", "json", "--model", "claude-sonnet-5-5",
                        "--setting-sources", "", "--allowedTools", "Read,Grep,Glob", "--max-budget-usd", "3"],
                       cwd=dest, capture_output=True, text=True)
    (dest / "review_raw.json").write_text(p.stdout, encoding="utf-8")
    try:
        txt = json.loads(p.stdout)["result"]
        obj = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        (dest / "review.json").write_text(json.dumps(obj, indent=1), encoding="utf-8")
        print("ok", dest / "review.json")
    except (ValueError, KeyError) as e:
        raise SystemExit(f"could not parse review: {e}")


def unseal():
    key = json.loads((RUNS / "blind_key.json").read_text())
    out = {}
    for tag, m in key.items():
        rv = RUNS / "blind" / tag / "review.json"
        if not rv.exists():
            continue
        obj = json.loads(rv.read_text())
        for label, run_id in m.items():
            out[run_id] = {k: obj[label][k] for k in ("correctness", "security", "maintainability", "edge_coverage")}
            out[run_id]["defects"] = len(obj[label].get("defects", []))
    (RUNS / "blind_results.json").write_text(json.dumps(out, indent=1))
    print("wrote", RUNS / "blind_results.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pack", "review", "unseal"])
    ap.add_argument("--project")
    ap.add_argument("--round", type=int)
    ap.add_argument("--claude-bin", default="claude")
    a = ap.parse_args()
    {"pack": lambda: pack(a.project, a.round), "review": lambda: review(a.project, a.round, a.claude_bin),
     "unseal": unseal}[a.cmd]()
