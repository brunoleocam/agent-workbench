# Dials, macrostructures, and the index page

## Dials (1 to 10)

Each direction states its three dial values. The user tunes the chosen direction by naming a dial and a number.

| Dial | Low (1–3) | Mid (4–7) | High (8–10) |
| --- | --- | --- | --- |
| variety | Calm, aligned, predictable; one column or a strict grid | Balanced; one section breaks the rhythm | Asymmetric, oversized type, cropped elements, strong tension |
| motion | Only state feedback (press, focus) under 120ms | Section and state transitions under 240ms | One choreographed moment (a count, a reveal, a sheet with a spring); everything else still calm |
| density | Spacious: spacing scale 24px to 96px, few items per screen | Balanced: 16px to 64px | Dense: 8px to 32px, tables, many rows visible |

Every motion level has a reduced-motion fallback. High motion with drag or springs follows the `apple-design` skill.

## Macrostructures to vary

Pick a different one, or a clearly different variation, for each direction. These change the page's structure, not only its colors.

| Macrostructure | Shape | Good for |
| --- | --- | --- |
| Editorial column | One reading column with an annotated margin | Long reading, notes, documentation |
| Asymmetric split | A large fixed area beside a scrolling one | Product plus detail, a map plus a list |
| Index or table | Rows first, details on demand | Operations, admin, comparison |
| Canvas or map | The workspace fills the screen, controls float at the edges | Tools, planning, maps |
| Dense feed | Cards or rows of different sizes in a continuous flow | Listings, news, marketplaces |
| Chapters | Full-width bands, each with its own rhythm | Stories, events, a single product |
| Command center | Panels with fixed roles side by side | Monitoring, dispatch, support |

Avoid the template skeleton (Hero → three equal feature cards → pricing → FAQ → CTA) unless the brief truly needs a marketing page, and then change at least one section into something only this product would have.

## Axes, in plain words

- **layout**: which macrostructure, and where the eye lands first.
- **display**: the family used for headings (serif, grotesque, condensed, mono, slab). Two directions with the same display family must differ on the other axes.
- **palette**: temperature (warm, cool, neutral), light or dark, and how much color (monochrome plus one accent, or several flat colors).
- **density**: the dial above.

## Index page skeleton

```html
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Direções — <produto></title>
<style>
  :root { --gap: 16px; --ink: #1f1d1a; --surface: #f4f2ee; --paper: #ffffff; --muted: #6a655d; --font-ui: system-ui, sans-serif; }
  body { margin: 0; padding: var(--gap); background: var(--surface); color: var(--ink); font-family: var(--font-ui); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: var(--gap); }
  figure { margin: 0; }
  iframe { width: 100%; height: 720px; border: 1px solid var(--muted); background: var(--paper); }
  figcaption { padding-top: 8px; }
</style>
</head>
<body>
  <h1>Três direções para <produto></h1>
  <div class="grid">
    <figure><iframe src="a.html" title="Direção A"></iframe><figcaption><strong>A — <nome></strong>: <postura></figcaption></figure>
    <figure><iframe src="b.html" title="Direção B"></iframe><figcaption><strong>B — <nome></strong>: <postura></figcaption></figure>
    <figure><iframe src="c.html" title="Direção C"></iframe><figcaption><strong>C — <nome></strong>: <postura></figcaption></figure>
  </div>
</body>
</html>
```

The index page is scaffolding, not a direction: it is the only file in the folder allowed to stay neutral.
