---
name: create-agent
description: Creates a specialized subagent and registers it for the orchestrator. Use only when the user invokes /create-agent.
disable-model-invocation: true
---

# /create-agent

The argument is the name, for example `security-reviewer`.

`<plugin>` is the agent-workbench plugin root. In Claude Code it is `${CLAUDE_PLUGIN_ROOT}` (the path arrives already substituted). In Cursor, it is two levels above this `SKILL.md`.

1. Run `python "<plugin>/agent-system/scripts/create_agent.py" check --name <name>`. If it conflicts with a built-in or existing agent, stop.
2. Write `<plugin>/agents/<name>.md` with `name` and `description` frontmatter. The description says when the orchestrator should delegate. The body has role, responsibilities, limits, input, output, and a definition of done. Do not use generic text.
3. Run `register --name <name> --purpose "<one sentence>" --recommended-for "<when to delegate>"`. If the current project has `.cursor/agent-system/state.json`, pass `--root` with the project root.
4. Do not register Cursor's built-in agents.
5. The new agent lives in the plugin's repository. Do not commit unless the user asks.

In Claude Code, installed from a remote marketplace, `${CLAUDE_PLUGIN_ROOT}` is a cached copy that the next update replaces. Before step 2, ask the user for the path of the local clone of the agent-workbench repository and use that path as `<plugin>` in steps 1 to 3. If they have no clone, write the agent to `~/.claude/agents/<name>.md`, skip the registration, and warn that the agent stays outside the plugin.

Confirm the name and the delegation sentence.
