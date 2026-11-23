#!/usr/bin/env python3
"""Run one benchmark execution: one project, one arm, one round.

  python benchmark/runner/run.py --project simple --arm workbench --round 1
  python benchmark/runner/run.py --project simple --arm baseline --round 1 --backend local --claude-bin <stub>

The agent only ever sees SPEC.md (and, in the workbench arm, the plugin and an initialized
project). The hidden tests are not in the workspace, the plugin copy, or the container.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_lib as B  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / "benchmark"
IMAGE = "agent-workbench-bench:1"
PLUGIN_PARTS = [".claude-plugin", "agent-system", "agents", "hooks", "rules", "skills"]
LIMITS = {"simple": {"usd": 8.0, "minutes": 45}, "medium": {"usd": 20.0, "minutes": 100}}
FIXED = {"model": "claude-sonnet-5-5"}


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def git(ws, *a):
    return sh(["git", "-C", str(ws), "-c", "user.name=bench", "-c", "user.email=bench@example.com", *a])


def make_plugin_copy(dest):
    """Plugin without benchmark/, .git, docs: nothing of the hidden material can travel with it."""
    for part in PLUGIN_PARTS:
        src = ROOT / part
        if src.is_dir():
            shutil.copytree(src, dest / part, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    head = git(ROOT, "rev-parse", "HEAD").stdout.strip()
    dirty = bool(git(ROOT, "status", "--porcelain", "--", *PLUGIN_PARTS).stdout.strip())
    return {"commit": head, "dirty": dirty}


def prepare_workspace(project, arm, ws, plugin_dir):
    ws.mkdir(parents=True)
    shutil.copy(BENCH / "specs" / f"{project}.md", ws / "SPEC.md")
    git(ws, "init", "-q", "-b", "main")
    if arm == "workbench":
        r = sh([sys.executable, str(plugin_dir / "agent-system" / "scripts" / "init_project.py"),
                "--root", str(ws), "--claude"])
        if r.returncode != 0:
            raise SystemExit("init_project failed: " + r.stderr[-500:])
    git(ws, "add", "-A")
    git(ws, "commit", "-q", "-m", "benchmark start")


class Docker:
    def __init__(self, name):
        self.name = name

    def start(self, ws, plugin_dir):
        env = dict(os.environ)
        r = sh(["docker", "create", "--name", self.name, "-e", "CLAUDE_CODE_OAUTH_TOKEN",
                "-e", "DISABLE_AUTOUPDATER=1", "--memory", "4g", "--cpus", "2", IMAGE], env=env)
        if r.returncode:
            raise SystemExit("docker create failed: " + r.stderr)
        sh(["docker", "start", self.name])
        sh(["docker", "cp", str(ws) + "/.", f"{self.name}:/work"])
        if plugin_dir:
            sh(["docker", "exec", "-u", "root", self.name, "mkdir", "-p", "/opt/plugin"])
            sh(["docker", "cp", str(plugin_dir) + "/.", f"{self.name}:/opt/plugin"])
        sh(["docker", "exec", "-u", "root", self.name, "chown", "-R", "bench", "/work", "/opt/plugin"])
        sh(["docker", "exec", self.name, "git", "config", "--global", "--add", "safe.directory", "/work"])

    def exec(self, argv, timeout, out_path):
        cmd = ["docker", "exec", "-w", "/work", "-e", "CLAUDE_CODE_OAUTH_TOKEN", self.name, *argv]
        return run_streaming(cmd, timeout, out_path)

    def fetch(self, dest):
        sh(["docker", "cp", f"{self.name}:/work/.", str(dest)])

    def stop(self):
        sh(["docker", "rm", "-f", self.name])


class Local:
    """Fresh directory, no container: the minimum of ADR-0006. Used for harness tests and as a fallback."""

    def __init__(self, ws):
        self.ws = ws

    def start(self, ws, plugin_dir):
        pass

    def exec(self, argv, timeout, out_path):
        return run_streaming(argv, timeout, out_path, cwd=self.ws)

    def fetch(self, dest):
        pass

    def stop(self):
        pass


def run_streaming(cmd, timeout, out_path, cwd=None):
    t0 = time.time()
    timed_out = False
    with open(out_path, "w", encoding="utf-8") as f:
        p = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, cwd=cwd, text=True)
        try:
            p.wait(timeout=max(5, timeout))
        except subprocess.TimeoutExpired:
            timed_out = True
            p.kill()
            p.wait()
    return {"seconds": time.time() - t0, "timed_out": timed_out, "code": p.returncode}


def claude_argv(claude_bin, arm, prompt, budget, session_id):
    a = [claude_bin, "-p", prompt, "--output-format", "stream-json", "--verbose",
         "--model", FIXED["model"], "--dangerously-skip-permissions",
         "--setting-sources", "project,local", "--max-budget-usd", f"{budget:.2f}"]
    if arm == "workbench":
        a += ["--plugin-dir", "/opt/plugin" if claude_bin == "claude" else str(PLUGIN_LOCAL[0])]
    if session_id:
        a += ["--resume", session_id]
    return a


PLUGIN_LOCAL = [None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", choices=sorted(LIMITS), required=True)
    ap.add_argument("--arm", choices=["baseline", "workbench"], required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--backend", choices=["docker", "local"], default="docker")
    ap.add_argument("--claude-bin", default="claude")
    ap.add_argument("--usd", type=float, help="override the cost cap")
    ap.add_argument("--minutes", type=float, help="override the wall-clock cap")
    ap.add_argument("--runs-dir", default=str(BENCH / "runs"))
    a = ap.parse_args()

    if a.backend == "docker" and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        raise SystemExit("set CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`) in this shell")
    run_id = f"{a.project}-{a.arm}-r{a.round}"
    rd = Path(a.runs_dir) / run_id
    if rd.exists():
        raise SystemExit(f"{rd} exists; refusing to overwrite a run")
    rd.mkdir(parents=True)
    cap_usd = a.usd or LIMITS[a.project]["usd"]
    cap_s = (a.minutes or LIMITS[a.project]["minutes"]) * 60
    policy = json.loads((BENCH / "policy.json").read_text(encoding="utf-8"))
    prompt = (BENCH / "prompt.txt").read_text(encoding="utf-8").strip()

    plugin_dir = rd / "plugin"
    plugin_info = make_plugin_copy(plugin_dir) if a.arm == "workbench" else None
    ws = rd / "ws"
    prepare_workspace(a.project, a.arm, ws, plugin_dir)
    PLUGIN_LOCAL[0] = plugin_dir
    be = Docker(f"bench-{run_id}") if a.backend == "docker" else Local(ws)
    be.start(ws, plugin_dir if a.arm == "workbench" else None)

    t0 = time.time()
    spent, session, interventions, all_results, all_events = 0.0, None, [], [], []
    stop_reason, turn = "finished", 0
    try:
        while True:
            turn += 1
            remaining_usd, remaining_s = cap_usd - spent, cap_s - (time.time() - t0)
            if remaining_usd < 0.25:
                stop_reason = "cost_cap"
                break
            if remaining_s < 30:
                stop_reason = "time_cap"
                break
            text_in = prompt if turn == 1 else interventions[-1]["answer"]
            stream = rd / f"stream-{turn}.jsonl"
            info = be.exec(claude_argv(a.claude_bin, a.arm, text_in, remaining_usd, session), remaining_s, stream)
            ev = B.read_events(stream)
            all_events += ev
            res = B.last_result(ev)
            if res:
                all_results.append(res)
                spent += float(res.get("total_cost_usd", 0) or 0)
                session = res.get("session_id") or session
            init = B.init_event(ev)
            if turn == 1:
                proof = B.arm_proof(init, a.arm, "/opt/plugin" if a.backend == "docker" else str(plugin_dir))
                (rd / "arm_proof.json").write_text(json.dumps(proof, indent=1), encoding="utf-8")
                if not proof["ok"]:
                    stop_reason = "INVALID_ARM: " + proof["reason"]
                    break
            if info["timed_out"]:
                stop_reason = "time_cap"
                break
            if not res or res.get("is_error"):
                stop_reason = "error: " + str((res or {}).get("subtype", "no result"))
                break
            text = B.final_text(ev)
            if not B.needs_reply(text):
                break
            if len(interventions) >= policy["max_interventions"]:
                stop_reason = "intervention_limit"
                break
            node, ans = B.choose_answer(policy, text)
            interventions.append({"turn": turn, "node": node, "question": B.last_paragraph(text)[:400], "answer": ans})
    finally:
        be.fetch(ws)
        be.stop()

    skills, agents = B.skill_and_agent_use(all_events)
    tot = B.usage_totals(all_results)
    run = {"run_id": run_id, "project": a.project, "arm": a.arm, "round": a.round, "model": FIXED["model"],
           "claude_version": (sh([a.claude_bin, "--version"]).stdout.strip() if a.backend == "local" else "2.1.322 (image)"),
           "backend": a.backend, "caps": {"usd": cap_usd, "seconds": cap_s}, "stop_reason": stop_reason,
           "wall_seconds": round(time.time() - t0, 1), "turns": turn, "usage": tot,
           "interventions": interventions, "intervention_count": len(interventions),
           "skills_used": skills, "agents_used": agents, "tool_calls": len(B.tool_calls(all_events)),
           "first_call_tokens": B.first_call_tokens(all_events), "plugin": plugin_info,
           "valid": not stop_reason.startswith("INVALID_ARM")}
    (rd / "run.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
    print(json.dumps({k: run[k] for k in ("run_id", "stop_reason", "wall_seconds", "intervention_count", "valid")}
                     | {"cost_usd": round(tot["cost_usd"], 2)}))


if __name__ == "__main__":
    main()
