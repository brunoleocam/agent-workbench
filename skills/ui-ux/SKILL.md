---
name: ui-ux
description: Designs and builds a user interface for a defined task, including empty, error, and loading states. Use when creating a screen, flow, component, or experience (criar UI, criar UX, tela, fluxo, interface).
---

# Create UI/UX

Builds the interface already chosen. If alternatives are still open, use `ui-ux-experiment` or `brainstorm` first.

1. Name the user's task and the success state.
2. If the repo has a design system, reuse its components, spacing, and tone. Do not replace the system.
3. Cover the empty, loading, error, and success states. Each with the user's next step.
4. Controls with an accessible name, keyboard focus, and readable contrast.
5. Implement from the spec or the plan. Follow `tdd` where the interface logic is testable.
6. In a web application, verify the flow in the browser: click, type, submit, navigate. A screenshot alone does not close the task. Also check the other screen that reads the same state.

Do not create `AGENTS.md`. Do not commit unless the user asks.
