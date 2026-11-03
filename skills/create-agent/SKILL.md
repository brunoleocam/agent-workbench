---
name: create-agent
description: Creates a specialized subagent and registers it for the orchestrator. Use only when the user invokes /create-agent.
disable-model-invocation: true
---

# /create-agent

O argumento é o nome, por exemplo `security-reviewer`.

`<plugin>` é a raiz do plugin agent-workbench. No Claude Code é `${CLAUDE_PLUGIN_ROOT}` (o caminho já chega substituído). No Cursor, fica dois níveis acima deste `SKILL.md`.

1. Rode `python "<plugin>/agent-system/scripts/create_agent.py" check --name <nome>`. Se houver conflito com agente built-in ou já existente, pare.
2. Escreva `<plugin>/agents/<nome>.md` com frontmatter `name` e `description`. A description diz quando o orchestrator deve delegar. O corpo tem papel, responsabilidades, limites, entrada, saída e critério de pronto. Não use um texto genérico.
3. Rode `register --name <nome> --purpose "<uma frase>" --recommended-for "<quando delegar>"`. Se o projeto atual tiver `.cursor/agent-system/state.json`, passe `--root` com a raiz do projeto.
4. Não registre agentes built-in do Cursor.
5. O agente novo fica no repositório do plugin. Não commite, a menos que o usuário peça.

No Claude Code, instalado de um marketplace remoto, `${CLAUDE_PLUGIN_ROOT}` é uma cópia em cache que o próximo update substitui. Antes do passo 2, pergunte ao usuário o caminho do clone local do repositório agent-workbench e use esse caminho como `<plugin>` nos passos 1 a 3. Se ele não tiver clone, grave o agente em `~/.claude/agents/<nome>.md`, pule o registro e avise que o agente fica fora do plugin.

Confirme o nome e a frase de delegação.
