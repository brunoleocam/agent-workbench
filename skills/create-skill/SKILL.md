---
name: create-skill
description: Creates a personal skill for the agent-workbench plugin (Cursor or Claude Code), with a slash name and a /help entry. Use when the user asks to create, add, or author a skill (criar skill, nova skill, comando novo).
---

# Create a skill

A new skill for the agent-workbench plugin, available in any repository and on any machine with the plugin. Do not create a skill inside the open repository unless the user asks for a project skill.

Do not write to `~/.cursor/skills-cursor/`. That directory belongs to Cursor.

## Destination

`<plugin>/skills/<name>/SKILL.md`, where `<plugin>` is the agent-workbench plugin root, two levels above this `SKILL.md`. The frontmatter `name` equals the folder name. A company- or language-specific skill does not go in the plugin, which is public: ask where to write it.

If the user asks for a skill only for that repository, then use the project's `.cursor/skills/<name>/SKILL.md` (in Claude Code, `.claude/skills/<name>/SKILL.md`).

In Claude Code, `<plugin>` is `${CLAUDE_PLUGIN_ROOT}`. Installed from a remote marketplace, that directory is a cached copy that the next update replaces: ask for the path of the local clone of the agent-workbench repository and write there. Without a clone, write to `~/.claude/skills/<name>/SKILL.md` and warn that the skill stays outside the plugin.

## Before writing

1. Extract from the request: what the skill does, when it triggers, and whether it is an explicit command (`/name`) or the agent should pull it in on its own.
2. Name: lowercase letters, numbers, and single hyphens (no leading, trailing, or doubled hyphen), at most 64 characters, equal to the folder name. The name is the command. The `description` is at most 1024 characters. These limits come from the [Agent Skills specification](https://agentskills.io/specification); `agent-system/tests/test_audit.py` checks every skill against it, so run the test suite after adding one.
3. If the user supplied the skill's text to be used exactly, copy that text. Do not paraphrase.
4. Do not duplicate a profile skill that already covers the same work. Extend the existing one if it is the same command.

## SKILL.md

```markdown
---
name: skill-name
description: What it does and when to use it, in the third person, with optional trigger words in other languages in parentheses.
---
```

`disable-model-invocation: true` only when the skill must run exclusively because the person typed `/name` (like `/help`). Without that field, the agent may apply the skill when the request matches the description.

Body in English. Actionable steps. Under 500 lines. Long detail goes in a file alongside, linked once from the `SKILL.md`. No Windows paths in the skill text.

Description: what it does and when to use it. Include the words people use to ask for it.

## After creating

1. Add an item to `skills/help/SKILL.md`, in the command list: what the command does and what it does not do.
2. If the skill changes the classification of a code request, add a line to rule `01-request-classification`. Do not bloat that rule with a skill that does not choose an implementation flow.
3. Do not create `AGENTS.md`. Do not commit unless the user asks.

Reply with the command (`/name`) and the situation it applies to.
