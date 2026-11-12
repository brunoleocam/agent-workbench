---
name: lessons
description: Proposes, lists, confirms, or rejects project lessons learned with lessons.py, loading only confirmed lessons relevant to the current activity. Use when a significant step reveals a reusable lesson, when the user says "registrar lição", "lições aprendidas", "confirmar lição", or before work in a category that has confirmed lessons.
---

# Lessons learned

An initialized project (`.cursor/agent-system/state.json`). The source of truth is `.cursor/agent-system/lessons.json`; `LESSONS.md` is generated. Commands in `agent-system/docs/cli.md`.

## Propose

Only propose a lesson that would change behavior in future work and that has evidence (TEST, FIND, SEC, commit, path). Do not record every observation from the conversation. At most one per relevant step.

```powershell
python .cursor/agent-system/scripts/lessons.py add --category testing --title "Expiry test uses an injected clock" --description "Time tests use a fake clock; a real sleep made TEST-004 flaky." --evidence TEST-004 --agent tester
```

No secrets, tokens, passwords, personal data, or private code snippets: the script refuses what looks like a secret, but the responsibility is yours. A duplicate (same normalized title, including a rejected one) is refused.

After proposing, show the lesson to the user and ask whether they confirm it.

## Confirm or reject

Only with the user's explicit decision. The agent does not confirm on its own.

```powershell
python .cursor/agent-system/scripts/lessons.py confirm --id LESSON-003
python .cursor/agent-system/scripts/lessons.py reject --id LESSON-004 --reason "too specific"
```

## Load

Session start already brings up to five confirmed titles. Before work in an area, load only its category:

```powershell
python .cursor/agent-system/scripts/lessons.py list --status confirmed --category security --verbose
```

Candidates and rejected lessons never enter the context automatically. Session start also brings up to three global lessons after the project's.

## Global lessons

A lesson that holds in every project (a preference of the user, a general practice) can live in the user's global store. Only the user promotes, and only a confirmed lesson:

```powershell
python .cursor/agent-system/scripts/lessons.py promote --id LESSON-003
python .cursor/agent-system/scripts/lessons.py list --scope global --status confirmed
```

You may propose one with `add --scope global` and then ask the user to confirm it with `confirm --scope global`. Write it in general terms: the script refuses a text with this project's path or name, an absolute path, a URL, or a secret. A project whose `layout.json` has `"global_lessons": false` neither reads nor writes the global store.
