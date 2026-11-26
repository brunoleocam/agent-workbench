#!/usr/bin/env python3
"""Run the long task: three sessions on one project, one arm, one round.

  python benchmark/runner/run_long.py --arm workbench --round 1 [--runs-dir benchmark/runs-long]

Session 1 gets specs/long-1.md and prompt.txt. Sessions 2 and 3 each start a NEW Claude Code session (no --resume across
sessions, so the conversation is gone) in the same workspace, with SPEC.md replaced by the next version and
prompt-long-update.txt. Interventions (auto-answers) resume the session they belong to. After each session the workspace is
copied to <run>/s<k>/ws and scored separately (score.py, project long-s<k>), so a regression shows up in the later stages.
The agent never sees the specs of later versions, nor the hidden tests.
"""
import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_lib as B  # noqa: E402
import run as R  # noqa: E402

BENCH = R.BENCH
STAGES = 3
LIMITS = {"usd": 12.0, "minutes": 90}


def stage_prompt(k):
    name = "prompt.txt" if k == 1 else "prompt-long-update.txt"
    return (BENCH / name).read_text(encoding="utf-8").strip()


def run_stage(be, arm, k, rd, claude_bin, policy, spent, t0, cap_usd, cap_s):
    """One session (plus its resumed interventions). Returns the stage record, the new total spend and the events."""
    session, interventions, results, events = None, [], [], []
    stop_reason, turn, cost = "finished", 0, 0.0
    started = time.time()
    while True:
        turn += 1
        remaining_usd, remaining_s = cap_usd - spent - cost, cap_s - (time.time() - t0)
        if remaining_usd < 0.25:
            stop_reason = "cost_cap"
            break
        if remaining_s < 30:
            stop_reason = "time_cap"
            break
        text_in = stage_prompt(k) if turn == 1 else interventions[-1]["answer"]
        stream = rd / f"stream-s{k}-{turn}.jsonl"
        info = be.exec(R.claude_argv(claude_bin, arm, text_in, remaining_usd, session), remaining_s, stream)
        ev = B.read_events(stream)
        events += ev
        res = B.last_result(ev)
        if res:
            results.append(res)
            cost += float(res.get("total_cost_usd", 0) or 0)
            session = res.get("session_id") or session
        if k == 1 and turn == 1:
            expected = "/opt/plugin" if claude_bin == "claude" else str(R.PLUGIN_LOCAL[0])
            proof = B.arm_proof(B.init_event(ev), arm, expected)
            (rd / "arm_proof.json").write_text(json.dumps(proof, indent=1), encoding="utf-8")
            if not proof["ok"]:
                return {"stage": k, "stop_reason": "INVALID_ARM: " + proof["reason"], "usage": B.usage_totals(results)}, spent + cost, events
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
    skills, agents = B.skill_and_agent_use(events)
    calls = B.tool_calls(events)
    first_write = next((i for i, c in enumerate(calls, 1) if c["name"] in ("Write", "Edit", "MultiEdit")), None)
    record = {"stage": k, "stop_reason": stop_reason, "wall_seconds": round(time.time() - started, 1), "turns": turn,
              "usage": B.usage_totals(results), "interventions": interventions, "intervention_count": len(interventions),
              "skills_used": skills, "agents_used": agents, "tool_calls": len(calls),
              "calls_before_first_write": (first_write - 1) if first_write else len(calls),
              "first_call_tokens": B.first_call_tokens(events)}
    return record, spent + cost, events


def put_spec(be, backend, ws, k):
    """Replace SPEC.md in the agent's workspace with version k. Later versions are never in the workspace before this."""
    src = BENCH / "specs" / f"long-{k}.md"
    if backend == "docker":
        R.sh(["docker", "cp", str(src), f"{be.name}:/work/SPEC.md"])
        R.sh(["docker", "exec", "-u", "root", be.name, "chown", "bench", "/work/SPEC.md"])
        R.sh(["docker", "exec", be.name, "git", "-C", "/work", "add", "-A"])
        R.sh(["docker", "exec", be.name, "git", "-C", "/work", "-c", "user.name=bench", "-c", "user.email=bench@example.com",
              "commit", "-q", "-m", f"end of session {k - 1}", "--allow-empty"])
    else:
        shutil.copy(src, ws / "SPEC.md")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["baseline", "workbench", "lean"], required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--backend", choices=["docker", "local"], default="docker")
    ap.add_argument("--claude-bin", default="claude")
    ap.add_argument("--usd", type=float)
    ap.add_argument("--minutes", type=float)
    ap.add_argument("--runs-dir", default=str(BENCH / "runs-long"))
    a = ap.parse_args()
    if a.backend == "docker" and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        raise SystemExit("set CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`) in this shell")
    run_id = f"long-{a.arm}-r{a.round}"
    rd = Path(a.runs_dir) / run_id
    if rd.exists():
        raise SystemExit(f"{rd} exists; refusing to overwrite a run")
    rd.mkdir(parents=True)
    cap_usd, cap_s = a.usd or LIMITS["usd"], (a.minutes or LIMITS["minutes"]) * 60
    policy = json.loads((BENCH / "policy.json").read_text(encoding="utf-8"))

    plugin_dir = rd / "plugin"
    plugin_info = R.make_plugin_copy(plugin_dir, lean=a.arm == "lean") if a.arm != "baseline" else None
    ws = rd / "ws"
    R.prepare_workspace("long-1", a.arm, ws, plugin_dir)
    R.PLUGIN_LOCAL[0] = plugin_dir
    be = R.Docker(f"bench-{run_id}") if a.backend == "docker" else R.Local(ws)
    be.start(ws, plugin_dir if a.arm != "baseline" else None)

    t0, spent, stages, stop_reason = time.time(), 0.0, [], "finished"
    try:
        for k in range(1, STAGES + 1):
            if k > 1:
                put_spec(be, a.backend, ws, k)
            rec, spent, _ = run_stage(be, a.arm, k, rd, a.claude_bin, policy, spent, t0, cap_usd, cap_s)
            stages.append(rec)
            snap = rd / f"s{k}"
            (snap / "ws").mkdir(parents=True)
            if a.backend == "docker":
                be.fetch(snap / "ws")
            else:
                shutil.copytree(ws, snap / "ws", dirs_exist_ok=True)
            (snap / "run.json").write_text(json.dumps({"run_id": f"{run_id}-s{k}", "project": f"long-s{k}", "arm": a.arm,
                                                       "round": a.round, **rec}, indent=1), encoding="utf-8")
            if rec["stop_reason"] != "finished":
                stop_reason = f"stage {k}: {rec['stop_reason']}"
                break
    finally:
        be.stop()
    total = {"cost_usd": sum(s.get("usage", {}).get("cost_usd", 0) for s in stages)}
    run = {"run_id": run_id, "project": "long", "arm": a.arm, "round": a.round, "model": R.FIXED["model"], "backend": a.backend,
           "caps": {"usd": cap_usd, "seconds": cap_s}, "stop_reason": stop_reason, "wall_seconds": round(time.time() - t0, 1),
           "stages": stages, "total": total, "plugin": plugin_info,
           "valid": not stop_reason.startswith("stage 1: INVALID_ARM")}
    (rd / "run.json").write_text(json.dumps(run, indent=1), encoding="utf-8")
    print(json.dumps({"run_id": run_id, "stop_reason": stop_reason, "wall_seconds": run["wall_seconds"],
                      "cost_usd": round(total["cost_usd"], 2), "valid": run["valid"]}))


if __name__ == "__main__":
    main()
