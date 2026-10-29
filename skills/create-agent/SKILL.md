---
name: create-agent
description: Creates a specialized subagent and registers it for the orchestrator. Use only when the user invokes /create-agent.
disable-model-invocation: true
---

# /create-agent

O argumento é o nome, por exemplo `security-reviewer`.

`<plugin>` é a raiz do plugin agent-workbench, dois níveis acima deste `SKILL.md`.

1. Rode `python "<plugin>/agent-system/scripts/create_agent.py" check --name <nome>`. Se houver conflito com agente built-in ou já existente, pare.
2. Escreva `<plugin>/agents/<nome>.md` com frontmatter `name` e `description`. A description diz quando o orchestrator deve delegar. O corpo tem papel, responsabilidades, limites, entrada, saída e critério de pronto. Não use um texto genérico.
3. Rode `register --name <nome> --purpose "<uma frase>" --recommended-for "<quando delegar>"`. Se o projeto atual tiver `.cursor/agent-system/state.json`, passe `--root` com a raiz do projeto.
4. Não registre agentes built-in do Cursor.
5. O agente novo fica no repositório do plugin. Não commite, a menos que o usuário peça.

Confirme o nome e a frase de delegação.
