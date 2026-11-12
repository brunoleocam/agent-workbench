# DESIGN.md format

`DESIGN.md` sits at the project root. It is the visual contract: every screen reads it before it is built, and every value it names exists in `design/tokens.css` with the same value. `AGENTS.md` or `CLAUDE.md` says how to build the project; `DESIGN.md` says how it looks and feels.

Front matter:

```markdown
---
status: draft        # draft | approved; only the user approves
direction: b         # the chosen file in design/directions/
---
```

The nine sections below are fixed: these headings, in this order, with nothing renamed. Write their content in the user's language.

## 1. Tema visual e atmosfera

- The stance in one sentence: what this interface believes and for whom.
- Density (compact, balanced, spacious) and why.
- **Distinctive choice**: the 20% in one concrete sentence ("headings in a condensed serif at 0.92 line height", not "bold and modern").
- Three adjectives the product is, and three it is not.

## 2. Cor

A table with one row per token: token name, value, semantic role, and where it is used. Required roles: surface, raised surface, ink (body text), muted ink, accent, danger, success, focus. Every color used as a text background has a matching `-ink` pair with at least 4.5:1 contrast (3:1 for text 24px and up, or 18.66px bold). State the accent budget, for example "accent on at most two elements per screen".

## 3. Tipografia

- At most three families: display, body, and one optional outlier (mono, or one wordmark face). Give the fallback stack for each.
- A scale table: token, size, line height, weight, letter spacing, use.
- Body at least 16px; measure between 45 and 75 characters.

## 4. Espaçamento e grid

- A spacing scale in multiples of 4px, with token names (`--space-1: 4px` and up).
- Grid: columns, gutters, max content width, and breakpoints.
- Section rhythm: which sections are tight and which breathe.

## 5. Layout e composição

- The macrostructure (editorial column, asymmetric split, index, canvas, dense feed, chapters) and why it fits the user's main task.
- Where the eye lands first on the main screens.
- What may be centered and what may not.

## 6. Componentes

For each component the product uses (button, input, select, card, list row, nav, dialog, toast, empty state): anatomy, sizes, radius, and every state: default, hover, focus-visible, active, disabled, loading, and error where it applies. Input and button share one height (at least 44px for touch). Disabled uses more than opacity.

## 7. Movimento e interação

- Durations and easings as tokens, by purpose (feedback, transition, emphasis).
- What moves and what never moves.
- The reduced-motion behavior.
- When the product has drag, swipe, sheets, or spring animation, follow the `apple-design` skill and name which of its rules apply.

## 8. Voz e microcopy

Tone in two sentences, five button labels in the product's own verbs, how errors are written (cause plus next step), and how empty states invite the first action. Follow [microcopy.md](microcopy.md).

## 9. Anti-padrões

- The lint P0 list from [anti-slop.md](anti-slop.md), always.
- The project's own don'ts, each with the reason ("no photography of people: the users are clinics, not models").
- What was deliberately rejected from the references (the "Do not copy" column of the brief).

## Page exceptions

A page that needs a different rule gets `design/pages/<page>.md`. It names the `DESIGN.md` rule it replaces, the new value, and why. The exception wins for that page only.
