---
name: timeline
description: Shows the append-only development timeline for an initialized project. Use only when the user invokes /timeline.
disable-model-invocation: true
---

# /timeline

A fonte de verdade é `.cursor/timeline/events.jsonl`. Não reescreva esse arquivo à mão.

`<plugin>` é a raiz do plugin agent-workbench, dois níveis acima deste `SKILL.md`.

```powershell
python "<plugin>/agent-system/scripts/timeline_view.py" --root . --limit 40 --write-md
```

Mostre os eventos. `TIMELINE.md` é só a vista gerada agora. Se não houver arquivo, diga que o projeto ainda não tem eventos. Não invente eventos.
