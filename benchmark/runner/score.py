#!/usr/bin/env python3
"""Score one finished run: hidden acceptance tests, mutation score, ruff, mypy.

The hidden tests live only in this scoring step. In docker mode they go into a NEW container
(never the one the agent used), and no API token is passed to it.

  python benchmark/runner/score.py --run benchmark/runs/simple-baseline-r1 [--backend local]
"""
import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmark"
IMAGE = "agent-workbench-bench:1"


def sh(args, timeout=None):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(args, 124, e.stdout or "", "timeout")


class Env:
    def __init__(self, backend, ws, name):
        self.backend, self.ws, self.name = backend, ws, name

    def start(self, project):
        if self.backend == "docker":
            sh(["docker", "rm", "-f", self.name])
            sh(["docker", "create", "--name", self.name, "--memory", "4g", "--cpus", "2", IMAGE])
            sh(["docker", "start", self.name])
            sh(["docker", "cp", str(self.ws) + "/.", f"{self.name}:/work"])
            sh(["docker", "exec", "-u", "root", self.name, "mkdir", "-p", "/hidden"])
            sh(["docker", "cp", str(BENCH / "hidden" / project) + "/.", f"{self.name}:/hidden/{project}"])
            sh(["docker", "cp", str(BENCH / "hidden" / "common.py"), f"{self.name}:/hidden/common.py"])
            sh(["docker", "cp", str(BENCH / "runner" / "mutation.py"), f"{self.name}:/hidden/mutation.py"])
            sh(["docker", "exec", "-u", "root", self.name, "chown", "-R", "bench", "/work", "/hidden"])
            self.hidden, self.work = "/hidden", "/work"
        else:
            self.hidden, self.work = str(BENCH / "hidden"), str(self.ws)

    def run(self, argv, timeout=None, env=None):
        if self.backend == "docker":
            pre = []
            for k, v in (env or {}).items():
                pre += ["-e", f"{k}={v}"]
            return sh(["docker", "exec", "-w", "/work", *pre, self.name, *argv], timeout)
        import os
        e = dict(os.environ, **(env or {}))
        try:
            return subprocess.run(argv, cwd=self.work, capture_output=True, text=True, timeout=timeout, env=e)
        except subprocess.TimeoutExpired as ex:
            return subprocess.CompletedProcess(argv, 124, ex.stdout or "", "timeout")

    def pull(self, remote, local):
        if self.backend == "docker":
            sh(["docker", "cp", f"{self.name}:{remote}", str(local)])

    def stop(self):
        if self.backend == "docker":
            sh(["docker", "rm", "-f", self.name])


def junit_counts(path):
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return None
    suites = [root] if root.tag == "testsuite" else list(root)
    tests = fails = errs = skips = 0
    failed = []
    for s in suites:
        tests += int(s.get("tests", 0))
        fails += int(s.get("failures", 0))
        errs += int(s.get("errors", 0))
        skips += int(s.get("skipped", 0))
        for tc in s.iter("testcase"):
            if tc.find("failure") is not None or tc.find("error") is not None:
                failed.append(tc.get("name"))
    return {"total": tests, "passed": tests - fails - errs - skips, "failed": fails + errs, "skipped": skips,
            "failed_names": failed[:80]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--backend", choices=["docker", "local"], default="docker")
    ap.add_argument("--skip-mutation", action="store_true")
    ap.add_argument("--no-install", action="store_true")
    a = ap.parse_args()
    rd = Path(a.run)
    run = json.loads((rd / "run.json").read_text(encoding="utf-8")) if (rd / "run.json").exists() else {}
    project = run.get("project") or rd.name.split("-")[0]
    ws = rd / "ws"
    env = Env(a.backend, ws, f"bench-score-{rd.name}")
    env.start(project)
    score = {"run_id": rd.name, "project": project}
    try:
        if not a.no_install and (ws / "requirements.txt").exists():
            r = env.run([sys.executable if a.backend == "local" else "python", "-m", "pip", "install", "-q", "-r", "requirements.txt"], 600)
            score["pip_install_ok"] = r.returncode == 0
        py = sys.executable if a.backend == "local" else "python"
        junit = "/tmp/hidden.xml" if a.backend == "docker" else str(rd / "hidden.xml")
        total_r = env.run([py, "-m", "pytest", f"{env.hidden}/{project}", "--collect-only", "-q", "-p", "no:cacheprovider"],
                          300, {"APP_DIR": env.work})
        m = re.search(r"(\d+) tests? collected", total_r.stdout)
        expected = int(m.group(1)) if m else None
        r = env.run([py, "-m", "pytest", f"{env.hidden}/{project}", "-q", "-p", "no:cacheprovider",
                     f"--junitxml={junit}"], 1500, {"APP_DIR": env.work})
        if a.backend == "docker":
            env.pull(junit, rd / "hidden.xml")
        counts = junit_counts(rd / "hidden.xml") or {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "failed_names": []}
        denom = expected or counts["total"] or 1
        counts["expected_total"] = expected
        counts["pass_rate"] = counts["passed"] / denom
        score["hidden"] = counts
        (rd / "hidden.log").write_text((r.stdout or "")[-6000:] + (r.stderr or "")[-2000:], encoding="utf-8")

        rf = env.run([py, "-m", "ruff", "check", "--output-format", "json", "--exit-zero", "."], 120)
        try:
            score["ruff_issues"] = len(json.loads(rf.stdout or "[]"))
        except ValueError:
            score["ruff_issues"] = None
        mp = env.run([py, "-m", "mypy", "app", "--ignore-missing-imports", "--no-error-summary"], 300)
        score["mypy_errors"] = len([ln for ln in (mp.stdout or "").splitlines() if ": error:" in ln])

        if not a.skip_mutation:
            mu = env.run([py, f"{env.hidden}/mutation.py", "--root", env.work, "--max", "60"], 3000)
            try:
                score["mutation"] = json.loads(mu.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                score["mutation"] = {"score": None, "reason": "mutation run failed: " + (mu.stderr or "")[-300:]}
        agent_tests = [p for p in ws.rglob("test*.py") if ".git" not in p.parts and ".agent-system" not in p.parts]
        score["agent_test_files"] = len(agent_tests)
    finally:
        env.stop()
    (rd / "score.json").write_text(json.dumps(score, indent=1), encoding="utf-8")
    print(json.dumps({"run": rd.name, "hidden": f"{score['hidden']['passed']}/{score['hidden'].get('expected_total')}",
                      "ruff": score.get("ruff_issues"), "mypy": score.get("mypy_errors"),
                      "mutation": (score.get("mutation") or {}).get("score")}))


if __name__ == "__main__":
    main()
