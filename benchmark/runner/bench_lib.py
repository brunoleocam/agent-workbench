"""Pure helpers for the benchmark runner: stream parsing, arm proof, auto-answer policy."""
import json
import re
from pathlib import Path

PLUGIN_NAME = "agent-workbench"


def read_events(path):
    out = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def init_event(events):
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            return e
    return None


def _names(items):
    res = []
    for it in items or []:
        res.append(str(it.get("name", "")) if isinstance(it, dict) else str(it))
    return res


def arm_proof(init, arm, expected_plugin_path=None):
    """Prove from the init message which plugin and skills were loaded.
    Returns {"ok": bool, "reason": str, "plugins": [...], "skills": n, "agents": n}."""
    if init is None:
        return {"ok": False, "reason": "no init message in the stream", "plugins": [], "skills": 0, "agents": 0}
    plugins = _names(init.get("plugins"))
    skills = _names(init.get("skills")) + _names(init.get("slash_commands"))
    agents = _names(init.get("agents"))
    wb_plugin = [p for p in plugins if PLUGIN_NAME in p]
    wb_skills = [s for s in skills if s.startswith(PLUGIN_NAME + ":")]
    wb_agents = [a for a in agents if a.startswith(PLUGIN_NAME + ":")]
    loaded = bool(wb_plugin or wb_skills or wb_agents)
    ok, reason = True, "ok"
    if arm == "baseline" and loaded:
        ok, reason = False, "baseline loaded the plugin: %s" % (wb_plugin or wb_skills[:3] or wb_agents[:3])
    if arm == "workbench":
        if not wb_plugin:
            ok, reason = False, "workbench arm did not load the plugin"
        elif expected_plugin_path:
            paths = [str(p.get("path", "")) for p in init.get("plugins", []) if isinstance(p, dict)]
            if paths and not any(expected_plugin_path in p for p in paths):
                ok, reason = False, "plugin loaded from %s, expected %s" % (paths, expected_plugin_path)
    return {"ok": ok, "reason": reason, "plugins": plugins, "skills": len(skills),
            "agents": len(agents), "wb_skills": len(wb_skills)}


def last_result(events):
    for e in reversed(events):
        if e.get("type") == "result":
            return e
    return None


def final_text(events):
    r = last_result(events)
    if r and isinstance(r.get("result"), str) and r["result"].strip():
        return r["result"]
    texts = []
    for e in events:
        if e.get("type") == "assistant":
            for b in (e.get("message") or {}).get("content", []) or []:
                if b.get("type") == "text":
                    texts.append(b.get("text", ""))
    return texts[-1] if texts else ""


def tool_calls(events):
    calls = []
    for e in events:
        if e.get("type") == "assistant":
            for b in (e.get("message") or {}).get("content", []) or []:
                if b.get("type") == "tool_use":
                    calls.append({"name": b.get("name"), "input": b.get("input")})
    return calls


def skill_and_agent_use(events):
    skills, agents = [], []
    for c in tool_calls(events):
        inp = c.get("input") or {}
        if c["name"] == "Skill":
            skills.append(str(inp.get("skill") or inp.get("name") or ""))
        elif c["name"] in ("Task", "Agent"):
            agents.append(str(inp.get("subagent_type") or "general-purpose"))
    return skills, agents


def first_call_tokens(events):
    """Input-side tokens of the first model call: the cost of what is loaded at session start."""
    for e in events:
        if e.get("type") == "assistant":
            u = (e.get("message") or {}).get("usage") or {}
            return (int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0))
                    + int(u.get("cache_read_input_tokens", 0)))
    return None


def usage_totals(results):
    tot = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
           "cache_read_input_tokens": 0, "cost_usd": 0.0, "api_ms": 0, "turns": 0}
    for r in results:
        u = r.get("usage") or {}
        for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            tot[k] += int(u.get(k, 0) or 0)
        tot["cost_usd"] += float(r.get("total_cost_usd", 0) or 0)
        tot["api_ms"] += int(r.get("duration_api_ms", 0) or 0)
        tot["turns"] += int(r.get("num_turns", 0) or 0)
    return tot


def last_paragraph(text):
    parts = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return parts[-1] if parts else ""


def needs_reply(text):
    """Identical rule for both arms: the agent stopped on a question to the human."""
    p = last_paragraph(text)
    return p.endswith("?") or p.rstrip("*_ `").endswith("?")


def choose_answer(policy, text):
    p = last_paragraph(text)
    for rule in policy["rules"]:
        if re.search(rule["match"], p, re.I) or re.search(rule["match"], text[-1500:], re.I):
            return rule["node"], rule["answer"]
    d = policy["default"]
    return d["node"], d["answer"]
