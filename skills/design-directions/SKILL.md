---
name: design-directions
description: Generates three structurally different visual directions as self-contained HTML previews from an approved design brief, so a person with no design background chooses by reacting to what they see, then tunes the chosen one with variety, motion, and density dials. Use after design-discovery and before design-system (direções visuais, opções de visual, moodboard, escolher estilo, comparar layouts).
---

# Design directions

Second step of `design`. Input: `design/brief.md` with `status: approved`. Without it, run [design-discovery](../design-discovery/SKILL.md) first.

The user chooses by looking, not by reading jargon. Each direction is a real page with the product's real content, rendered in the browser.

## 1. Plan three different bets

Read the brief, the shared rules in [../design/references/anti-slop.md](../design/references/anti-slop.md), and the dials and macrostructures in [references/directions.md](references/directions.md).

Fill a matrix before writing any HTML:

| Direction | layout (macrostructure) | display (typeface family) | palette (temperature) | density |
| --- | --- | --- | --- | --- |
| a | | | | |
| b | | | | |
| c | | | | |

Every pair of directions must differ on **at least two** of the four axes: layout, display, palette, density. A difference in color alone does not count. If two rows differ on one axis only, change one of them before building.

Each direction is a defensible standalone bet, not a cosmetic variant of another. Give each a short name, a one-sentence stance, one distinctive choice (the 20% from the anti-slop rules), and dial values from 1 to 10 for variety, motion, and density.

All three respect the brief: audience, task, tone, language, and every constraint, including existing brand colors or fonts.

## 2. Build the previews

Write four files:

- `design/directions/a.html`, `design/directions/b.html`, `design/directions/c.html`: the main screen of the product in that direction.
- `design/directions/index.html`: the three side by side in `<iframe>` elements with relative `src`, each with its name and stance underneath. Skeleton in [references/directions.md](references/directions.md).

Each direction file:

- Starts with this comment, on one line:
  `<!-- direction: <name> | stance: <one sentence> | distinctive: <the 20%> | variety: N | motion: N | density: N | axes: layout=..., display=..., palette=..., density=... -->`
- Is self-contained: CSS in a `<style>` block with every value as a custom property in `:root`. No `<script src>` and no `<img src>` pointing to the network. A web font may load from a font CDN only with a local fallback stack, so the page still renders offline.
- Uses real content from the brief: the product's name, the user's main task, real labels in the brief's language. No lorem ipsum, no "Feature one", no invented metrics, no placeholder image services. Where a photo belongs, use a labelled block ("foto do produtor").
- Covers the main screen's states that matter for the choice, at least the default and an empty or error state, so the user sees how the direction handles them.
- Works from 320px to 1440px wide with no horizontal scroll.

## 3. Check before showing

Run the lint on the folder:

```bash
python <plugin>/agent-system/scripts/lint_design.py design/directions
```

No P0 may remain open. Fix them and run again. P1 findings are fine in a preview only when you can say why.

## 4. Stop and wait

Show the user where to open `design/directions/index.html`, with one line per direction: name, stance, and what is distinctive. Recommend one and say why in one sentence, tied to the brief.

**Stop and wait** for the user to choose. Do not write `DESIGN.md` or `design/tokens.css` in this step.

## 5. Adjust the chosen one

When the user asks for a change to the chosen direction, either a dial ("densidade 8") or free text ("menos arredondado"):

- Regenerate only that file. Leave the other two untouched.
- Update the dial values and axes in its first-line comment.
- Run the lint again.

If the user asks to combine parts of different directions ("a tipografia da A com as cores da C"), explain in one or two sentences that pieces from different directions usually clash, then deliver one coherent revision of the chosen direction that brings in what they liked. Do not paste fragments together.

## Done when

The user has named one direction and any adjustments are applied. Next step: [design-system](../design-system/SKILL.md), which turns the chosen direction into `DESIGN.md` and tokens.
