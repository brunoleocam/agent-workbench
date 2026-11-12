---
name: design
description: Runs the full design pipeline for a new product, site, or screen, interview, three rendered directions, DESIGN.md with tokens, and review, so the front end has a consistent, non-generic visual identity before any screen is built. Skips stages already approved and stops wherever the user must answer or choose. Use for a new visual interface without an approved DESIGN.md (design, criar o design, identidade visual, design profissional, sem cara de IA, design system do projeto).
---

# Design

Chains four skills, in this order:

1. [design-discovery](../design-discovery/SKILL.md): a short interview with recommended answers, producing `design/brief.md`.
2. [design-directions](../design-directions/SKILL.md): three structurally different directions in `design/directions/`, chosen by the user.
3. [design-system](../design-system/SKILL.md): `DESIGN.md` and `design/tokens.css` from the chosen direction.
4. [design-review](../design-review/SKILL.md): self-critique, checklist, and lint on the chosen direction.

Use it before building screens for a new visual interface. For a small change in an interface that already has its own visual system, use `ui-ux` directly.

## Resume where it stopped

Before starting, check what already exists and skip what is done:

| Stage | Done when |
| --- | --- |
| discovery | `design/brief.md` has `status: approved` |
| directions | `design/directions/` has `a.html`, `b.html`, `c.html`, and the user has named one |
| design system | `DESIGN.md` has `status: approved` and `design/tokens.css` exists |
| review | the review report was given after the last change to the chosen direction |

Say in one line which stages are done and which one starts.

## Stop points

The pipeline waits for the user at three points and never decides for them:

- the interview answers and the brief approval (discovery),
- the choice of one direction and its adjustments (directions),
- the approval of `DESIGN.md` (design system).

Approval is the user's explicit word. Changing `status: draft` to `status: approved` without it is not allowed.

## Shared references

All four stages use the files in `references/`:

- [anti-slop.md](references/anti-slop.md): what the lint blocks and warns about, the structural tells, and the 80/20 rule.
- [design-md-format.md](references/design-md-format.md): the nine sections of `DESIGN.md`.
- [microcopy.md](references/microcopy.md): labels, headings, errors, and empty states.
- [examples/](references/examples/editorial-calm.md): four complete `DESIGN.md` files for fictional products.
- [CREDITS.md](references/CREDITS.md): sources and licenses.

The lint is `agent-system/scripts/lint_design.py` in the plugin, or `.cursor/agent-system/scripts/lint_design.py` in a project after the init.

## After the pipeline

Build screens one at a time with `ui-ux`, or delegate each to the `frontend-implementer` agent. Each screen reads `DESIGN.md` and the tokens, runs the lint, and goes through `design-review` before delivery. Drag, swipe, sheets, and springs follow `apple-design`.

## Done when

`design/brief.md` and `DESIGN.md` are approved, `design/tokens.css` matches `DESIGN.md`, and the review of the chosen direction has no open P0.
