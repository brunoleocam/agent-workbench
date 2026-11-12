---
name: ui-ux
description: Designs and builds a user interface for a defined task, including empty, error, and loading states. Use when creating a screen, flow, component, or experience (criar UI, criar UX, tela, fluxo, interface).
---

# Create UI/UX

Builds the interface already chosen. If alternatives are still open, use `ui-ux-experiment` or `brainstorm` first.

1. Read the visual contract before building:
   - If `DESIGN.md` exists at the root, read it, `design/tokens.css`, and `design/pages/<page>.md` when present; the page exception wins for that page. Use only the declared tokens for color, font, spacing, radius, shadow, and duration. No raw values in components.
   - If there is no `DESIGN.md` and the task creates a new visual interface (a new product, site, or screen with no visual system of its own), recommend running `/design` first and wait for the user's decision.
   - A small change in an interface that already has its own visual system goes ahead without that recommendation; follow the system that is there.
2. Name the user's task and the success state.
3. If the repo has a design system or component library, reuse its components, spacing, and tone. Do not replace the system.
4. Cover the empty, loading, error, and success states. Each with the user's next step. Write the text following the microcopy rules in `skills/design/references/microcopy.md` of the plugin.
5. Controls with an accessible name, keyboard focus, and readable contrast.
6. Implement from the spec or the plan. Follow `tdd` where the interface logic is testable. Drag, swipe, sheets, and spring animation follow `apple-design`.
7. Before delivering, run the anti-slop lint on the changed files: `python <plugin>/agent-system/scripts/lint_design.py <files>` (or `.cursor/agent-system/scripts/lint_design.py` after the init). No P0 may remain open. Then run `design-review` on the screen.
8. In a web application, verify the flow in the browser: click, type, submit, navigate. A screenshot alone does not close the task. Also check the other screen that reads the same state.

Do not create `AGENTS.md`. Do not commit unless the user asks.
