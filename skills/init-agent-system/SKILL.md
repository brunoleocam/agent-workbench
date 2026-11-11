---
name: init-agent-system
description: Initializes the spec-driven agent system in the current project without overwriting existing Cursor or Claude Code config. Use only when the user invokes /init-agent-system.
disable-model-invocation: true
---

# /init-agent-system

Installs the spec-driven system at the root of the open project. Do not run it in the home directory.

`<plugin>` is the agent-workbench plugin root. In Claude Code it is `${CLAUDE_PLUGIN_ROOT}` (the path arrives already substituted). In Cursor, it is two levels above this `SKILL.md`.

In Cursor:

```powershell
python "<plugin>/agent-system/scripts/init_project.py" --root .
```

In Claude Code, add `--claude`:

```bash
python "<plugin>/agent-system/scripts/init_project.py" --root . --claude
```

With `--claude`, the script does not touch `.cursor/hooks.json` (Claude Code uses the plugin's own hooks) and writes the condensed rules `00` to `08` into a managed block of the project's `CLAUDE.md`, between the `agent-workbench:begin` and `agent-workbench:end` markers. It creates `CLAUDE.md` if missing, appends the block at the end if the file exists, and on a new init replaces only the block's content. Text outside the markers is not changed. The `claude_md` field of the report says what happened.

The script creates what is missing and does not replace a file that already exists:

- project hooks, with a backup of `hooks.json` if it already exists (Cursor only)
- `state.json`, the agent registry, and the scripts in `.cursor/agent-system/`: timeline, validators (`validate_spec`, `validate_tasks`, `check_proofs`, `validate_verification`), and `lessons`

A project script without the `agent-system-managed` mark that differs from the plugin's is preserved. An existing `state.json` gains only the new keys. In `layout.json`, the `overrides` and `proof_allow` you wrote survive a new init.

Rules, skills, and subagents already come from the plugin and are not copied, because a copy in the project would load everything twice. For Cursor Cloud Agents, which do not load the local plugin, run with `--for-cloud`: it copies rules `00` to `08` and the subagents (including `security-reviewer`) without overwriting existing ones. Skills and security references are not copied; in the Cloud, the agent follows the rules and subagents.

It does not create empty PRDs, specs, or ADRs. It does not move existing documentation. Do not commit.

In a project already under way, the script looks for the PRD, PDR, ADR, architecture, and specs wherever they are and writes the map to `.cursor/agent-system/layout.json`. It also detects frameworks (Express, Next.js, React, FastAPI, Django, Flask, Laravel, ASP.NET Core, Spring), the matching security references, and candidate surfaces (authentication, API, database, upload, payment, cryptography, multi-tenant, infrastructure). Later work uses those paths. The init does not summarize the code or rewrite the documents.

Show the script's JSON, including `layout` and `suggestions`. Read `.cursor/agent-system/SUGGESTIONS.md` and present the suggestions to the user.

Do not create PRDs, ADRs, tests, or new agents because of those suggestions. Wait for the user to ask. If `state.json` already exists, the state is kept and the map and suggestions are updated.
