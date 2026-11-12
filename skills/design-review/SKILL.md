---
name: design-review
description: Reviews a screen or a direction preview for design quality before it is handed over. Scores six axes from 1 to 5 and revises anything below 3, then runs the P0/P1/P2 checklist, the microcopy rules, and the anti-slop lint, and reports the outcome in plain prose. Use before showing or delivering UI work, or when asked whether an interface looks generic (revisão de design, design review, está com cara de IA, revisar a tela, checar o visual).
---

# Design review

Last step of `design`, and the check `ui-ux` and the `frontend-implementer` agent run before delivering a screen. It is a quality bar, not a performance: review, fix, and say what happened.

Inputs: the screen or preview, `DESIGN.md` and `design/tokens.css` when they exist, and `design/brief.md`. Without a `DESIGN.md`, review against the brief and the shared rules only.

## 1. Self-critique on six axes

Score the work from 1 to 5 on each axis. Base each score on something you can point to on the screen.

| Axis | Question |
| --- | --- |
| Stance | Does the screen take a position for this product and this user, or is it only a layout? |
| Hierarchy | Can someone tell in two seconds what is primary, secondary, and tertiary? |
| Execution | Are the details in spec: alignment, spacing on the scale, focus rings, contrast, wrapping, states? |
| Specificity | Does it look like this brief, or could it belong to any product? Apply the screenshot test from the anti-slop rules. |
| Restraint | Was everything that does not earn its place removed: decoration, duplicate text, a second accent? |
| Variety | Does it avoid the template skeleton and the structure of the previous screens or directions, beyond a color swap? |

Any axis **below 3** forces a revision of that weakness and a new score. Allow at most **3 passes**. A third pass that still fails usually means the brief or the direction is wrong; say so instead of polishing further.

## 2. Checklist, microcopy, and lint

1. Answer every question in [references/review-checklist.md](references/review-checklist.md). Every answer must be "no"; fix each "yes".
2. Apply the self-check at the end of [../design/references/microcopy.md](../design/references/microcopy.md).
3. Check the structural tells in [../design/references/anti-slop.md](../design/references/anti-slop.md) that no script can see.
4. Run the lint on the files you reviewed:

   ```bash
   python <plugin>/agent-system/scripts/lint_design.py <files or folder>
   ```

   No P0 may remain open. A deliberate exception needs a `design-lint-disable <RULE> -- <reason>` comment with a real reason.

5. When `DESIGN.md` exists, confirm the screen uses only its tokens and respects `design/pages/<page>.md` when present.

## 3. Report in prose

Report **in prose**, in the user's language, as part of the normal answer:

- what you checked,
- what you fixed and why,
- the final scores in one line (for example "postura 4, hierarquia 4, execução 5, especificidade 4, contenção 4, variedade 3"),
- what stays open and why, so the user can decide.

Do not write a score file, a JSON report, or a panel of named reviewer personas. None of them feed anything.

## Done when

All six axes are at 3 or above, the checklist has no "yes", the lint has no open P0, and the report is written. If a pass limit was hit, the report says what is left and why.
