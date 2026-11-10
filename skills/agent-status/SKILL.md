---
name: agent-status
description: Shows installed agents, rules, skills, hooks, and the current workflow state. Use only when the user invokes /agent-status.
disable-model-invocation: true
---

# /agent-status

Run it at the project root:

`<plugin>` is the agent-workbench plugin root. In Claude Code it is `${CLAUDE_PLUGIN_ROOT}` (the path arrives already substituted). In Cursor, it is two levels above this `SKILL.md`.

```powershell
python "<plugin>/agent-system/scripts/status_cmd.py" --root .
```

Relay the output. If the project is not initialized, say to use `/init-agent-system`. Do not invent a task, blocker, or next step that the script did not show.
