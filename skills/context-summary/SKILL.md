---
name: context-summary
description: Produces a summary of up to 10 lines with goal, decisions, files, and next steps, ready to paste into a new chat. Use when the conversation got long, the subject changed, or the user wants to continue in another chat (resumo, resumir contexto, chat novo, continuar em outro chat).
---

# Context summary

Reply only with the block below, at most 10 lines, and one line telling the user to paste it into the new chat. Write the block in the language the user is using.

```
Goal: <what is to be achieved, in one sentence>
Decisions: <decision>; <decision>
Files: <path> (<what changed or why it matters>); <path> (...)
State: <done and verified>; <what still fails>
Avoid: <discarded attempt and why> (only if it prevents repeating a mistake)
Next steps: 1) <...> 2) <...>
```

## Rules

- The source is what is already in the chat. Do not reread files or run commands to build the summary.
- Paths relative to the repository root. No code and no logs. A verification command only if essential for the next step.
- Only decisions that change the next step. An open question goes under Next steps.
- If the project has `docs/progress/CURRENT.md`, cite it in one line instead of repeating its content.
- Do not write a file. The summary stays only in the chat.
