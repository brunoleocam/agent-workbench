#!/usr/bin/env python3
"""Process metrics per plugin run: order of the first code write and the first spec write, spec-first denials,
whether the agent's tests start a server with several workers or processes, cost and time, hidden pass.

  python benchmark/runner/process_metrics.py [runs-dir ...]
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_lib as B  # noqa: E402

BENCH = Path(__file__).resolve().parents[1]
WRITE_TARGET = re.compile(r"(?:>>?|tee)\s+([\w./-]+\.(?:py|md))")
MULTI = re.compile(r"workers|subprocess|multiprocessing|Popen")


def norm(path):
    return str(path).replace(chr(92), "/")


def measure(run_dir):
    events = []
    for stream in sorted(glob.glob(run_dir + "/stream-*.jsonl")):
        events += B.read_events(stream)
    first_code = first_spec = None
    for index, call in enumerate(B.tool_calls(events), 1):
        data = call["input"] or {}
        if call["name"] in ("Write", "Edit", "MultiEdit"):
            paths = [norm(data.get("file_path") or "")]
        elif call["name"] == "Bash":  # the agents write most files through shell redirects
            paths = [norm(m) for m in WRITE_TARGET.findall(str(data.get("command") or ""))]
        else:
            continue
        for path in paths:
            if "docs/specs/" in path:
                first_spec = first_spec or index
            elif path.endswith(".py") and "test" not in path and "docs/" not in path and ".agent-system" not in path:
                first_code = first_code or index
    raw = "".join(Path(s).read_text(encoding="utf-8", errors="replace") for s in glob.glob(run_dir + "/stream-*.jsonl"))
    tests = glob.glob(run_dir + "/ws/tests/**/*.py", recursive=True)
    multiproc = any(MULTI.search(Path(t).read_text(encoding="utf-8", errors="replace")) for t in tests)
    run = json.load(open(run_dir + "/run.json"))
    score = Path(run_dir + "/score.json")
    hidden = json.loads(score.read_text())["hidden"] if score.exists() else {}
    return {"run": os.path.basename(run_dir), "code_at": first_code, "spec_at": first_spec,
            "spec_first_denials": raw.count("no spec and no classification"), "multiproc_test": multiproc,
            "cost": round(run["usage"]["cost_usd"], 2), "minutes": round(run["wall_seconds"] / 60, 1),
            "hidden": f"{hidden.get('passed')}/{hidden.get('total')}"}


if __name__ == "__main__":
    for base in sys.argv[1:] or [str(BENCH / "runs"), str(BENCH / "runs-v2")]:
        for folder in sorted(glob.glob(base + "/medium-*")):
            if "baseline" not in folder:
                print(Path(base).name, measure(folder))
