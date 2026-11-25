#!/usr/bin/env python3
"""Static size of the choice space the Workbench adds at session start (no model call).
Measured from the plugin files; the runtime cost is measured in run.json as first_call_tokens
(baseline vs workbench). Rough tokens = chars / 4."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fm(path):
    t = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---", t, re.S)
    d = re.search(r"^description:\s*(.+)$", m.group(1), re.M) if m else None
    return (d.group(1).strip() if d else "")


skills = {p.parent.name: fm(p) for p in (ROOT / "skills").glob("*/SKILL.md")}
agents = {p.stem: fm(p) for p in (ROOT / "agents").glob("*.md")}
rules = {p.name: len(p.read_text(encoding="utf-8")) for p in (ROOT / "rules").glob("*")}
out = {"skills": len(skills), "skill_description_chars": sum(map(len, skills.values())),
       "agents": len(agents), "agent_description_chars": sum(map(len, agents.values())),
       "rules_files": len(rules), "rules_chars": sum(rules.values())}
out["approx_tokens_descriptions"] = (out["skill_description_chars"] + out["agent_description_chars"]) // 4
print(json.dumps(out, indent=1))
