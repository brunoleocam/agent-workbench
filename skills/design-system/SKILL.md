---
name: design-system
description: Turns the chosen visual direction into the project's design contract, DESIGN.md at the root plus design/tokens.css, with color roles and contrast pairs, a type scale of at most three families, a 4px spacing scale, component states, motion, voice, and anti-patterns. Use after a direction is chosen in design-directions, or to update an existing DESIGN.md (design system, DESIGN.md, tokens, sistema de design, paleta e tipografia do projeto).
---

# Design system

Third step of `design`. Input: the direction the user chose in `design/directions/` (see [design-directions](../design-directions/SKILL.md)) and `design/brief.md`. Output: `DESIGN.md` and `design/tokens.css`, the contract every screen follows.

## 1. Existing DESIGN.md

If `DESIGN.md` already exists at the root, read it first. Show the user what would change, section by section, and overwrite only after explicit confirmation. Without confirmation, change nothing. Prefer updating the affected sections over rewriting the file.

## 2. Write DESIGN.md

Follow [../design/references/design-md-format.md](../design/references/design-md-format.md): the front matter and the nine sections with their exact headings, in order. Extract every value from the chosen direction's `:root`; do not invent a new look at this step.

- Section 1 states the distinctive choice of the direction in one concrete sentence.
- Section 9 lists the lint P0 rules from [../design/references/anti-slop.md](../design/references/anti-slop.md), the project's own don'ts with reasons, and what the brief marked as "Do not copy".
- Section 7 points to the `apple-design` skill when the product has drag, swipe, sheets, or springs.
- Section 8 follows [../design/references/microcopy.md](../design/references/microcopy.md).

For complete examples of the format, see [../design/references/examples/](../design/references/examples/editorial-calm.md).

## 3. Write design/tokens.css

Start from [references/tokens-template.css](references/tokens-template.css). Every token lives in `:root`. Rules:

- **Same values.** Every color, font, size, and spacing value named in `DESIGN.md` exists in `design/tokens.css` with the same value, and the reverse.
- **Spacing in multiples of 4px**: `--space-1: 4px`, `--space-2: 8px`, and up.
- **Fonts**: use at most 3 font families: `--font-display`, `--font-body`, and one optional outlier such as `--font-mono`. Each with a local fallback stack.
- **Contrast pairs.** Every color used as a background for text has a matching `-ink` token (`--color-accent` and `--color-accent-ink`) with a contrast ratio of at least 4.5:1, or 3:1 for text 24px and up. Body ink on the surface also meets 4.5:1. The focus color meets 3:1 against the surface.
- No color from the framework's default indigo or violet unless the brief says it is the brand.

Check every pair by computing the WCAG contrast ratio:

```text
channel c in 0..1:   c' = c / 12.92                    if c <= 0.04045
                     c' = ((c + 0.055) / 1.055) ^ 2.4  otherwise
luminance L = 0.2126 R' + 0.7152 G' + 0.0722 B'
ratio = (L_lighter + 0.05) / (L_darker + 0.05)
```

Run a one-off script for this if the shell is available; do not estimate contrast by eye.

## 4. Page exceptions

When one page needs a different rule (a dashboard that must be denser than the marketing site), write `design/pages/<page>.md`. It names the `DESIGN.md` rule it replaces, the new value or token, and why. The exception applies to that page only and wins over `DESIGN.md` there. Add any new token it needs to `design/tokens.css`.

## 5. Approve

Write `DESIGN.md` with `status: draft`, summarize it in a few lines (stance, distinctive choice, colors, fonts, density), and ask for approval. Change to `status: approved` only after the user's explicit approval.

## Done when

`DESIGN.md` has `status: approved` and the nine sections, `design/tokens.css` matches it, every contrast pair passes, and the lint reports no P0 on `design/`. Next step: [design-review](../design-review/SKILL.md) on the chosen direction, then `ui-ux` or the `frontend-implementer` agent, one screen at a time.
