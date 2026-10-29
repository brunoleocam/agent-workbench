---
name: agent-status
description: Shows installed agents, rules, skills, hooks, and the current workflow state. Use only when the user invokes /agent-status.
disable-model-invocation: true
---

# /agent-status

Rode na raiz do projeto:

`<plugin>` é a raiz do plugin agent-workbench, dois níveis acima deste `SKILL.md`.

```powershell
python "<plugin>/agent-system/scripts/status_cmd.py" --root .
```

Repasse a saída. Se o projeto não estiver inicializado, diga para usar `/init-agent-system`. Não invente task, blocker ou próxima etapa que o script não mostrou.
