---
name: timeline
description: Shows the append-only development timeline for an initialized project. Use only when the user invokes /timeline.
disable-model-invocation: true
---

# /timeline

The source of truth is `.cursor/timeline/events.jsonl`. Do not rewrite that file by hand.

`<plugin>` is the agent-workbench plugin root. In Claude Code it is `${CLAUDE_PLUGIN_ROOT}` (the path arrives already substituted). In Cursor, it is two levels above this `SKILL.md`.

```powershell
python "<plugin>/agent-system/scripts/timeline_view.py" --root . --limit 40 --write-md
```

Show the events. `TIMELINE.md` is only the view generated now. If there is no file, say the project has no events yet. Do not invent events.
