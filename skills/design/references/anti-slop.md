# Anti-slop rules

What separates an interface someone designed from default model output. The P0 and P1/P2 IDs match `agent-system/scripts/lint_design.py`; a P0 blocks review.

Run the lint:

```bash
python <plugin>/agent-system/scripts/lint_design.py <path>             # plugin copy
python .cursor/agent-system/scripts/lint_design.py <path>              # project after the init
```

Options: `--design DESIGN.md`, `--tokens design/tokens.css` (both read by default when present), `--format json`. Exit 0 without P0, 1 with a P0, 2 on a usage error. A color declared in the tokens (a `--name: value` custom property) or in the `## 2. Cor` section of `DESIGN.md` is the brand, not a finding. Colors mentioned anywhere else, including the forbidden list in section 9, are not allowed by that mention.

## P0: blocks review

| ID | What it catches | Why it reads as generated | Fix |
| --- | --- | --- | --- |
| `P0-INDIGO` | `#6366f1`, `#4f46e5`, `#4338ca`, `#3730a3`, `#8b5cf6`, `#7c3aed`, `#a855f7`, or `indigo/violet/purple-400…700` classes | The framework default accent every model reaches for | Use `var(--color-accent)` from the tokens |
| `P0-GRADIENT` | Two-stop purple, blue, cyan, or pink gradient; gradient text | The "trust" hero of a thousand landing pages | A flat surface and deliberate type |
| `P0-EMOJI-ICON` | Emoji inside `h1`–`h6`, `button`, `li`, or an `icon` class | Decoration standing in for meaning | One monoline SVG set with `currentColor`, or nothing |
| `P0-SIDE-STRIPE` | Rounded card with a colored left or right border of 2px or more | The default "AI dashboard tile" | Drop the stripe or the radius |
| `P0-FILLER` | Lorem ipsum, "feature one/two/three", "placeholder text", "sample content", John/Jane Doe, Acme | Nobody thought about the content | Real content from `design/brief.md`, or a designed empty state |
| `P0-METRIC` | "10x faster", "99.9% uptime", "trusted by 50,000+ teams" | Invented claims destroy trust | A sourced number, or no number |
| `P0-PLACEHOLDER-CDN` | unsplash.com, placehold.co, placekitten.com, picsum.photos, via.placeholder.com | Fragile and obvious | A local asset or a labelled placeholder block |

## P1 and P2: warnings

| ID | What it catches | Fix |
| --- | --- | --- |
| `P1-RAW-COLOR` | Literal hex, `rgb()`, `hsl()`, `oklch()` outside `:root` and the tokens file | Reference a token |
| `P1-FONT-LITERAL` | `font-family` with a literal family outside the tokens | `var(--font-display)` or `var(--font-body)` |
| `P1-FONT-COUNT` | More than three font families across the scanned files; each file in `design/directions/` counts on its own | Display, body, and at most one outlier |
| `P1-TRANSITION-ALL` | `transition: all` or `transition-all` | Name the properties |
| `P1-OUTLINE-NONE` | Focus outline removed with no `:focus-visible` style in the file | A visible 2px focus ring |
| `P1-NO-REDUCED-MOTION` | Motion with no `prefers-reduced-motion` fallback in the file | Remove or shorten the motion under `reduce` |
| `P1-SUPPRESSION-NO-REASON` | `design-lint-disable` without a reason | Add the reason |
| `P2-ACCENT-OVERUSE` | Accent used more than 6 times in one file | Keep the accent for one or two things per screen |
| `P2-UNIFORM-HOVER-SCALE` | The same hover scale on more than 3 elements | Feedback that fits each element |

## Suppressing one finding

When a finding is a deliberate choice (a real SLA, an emoji the brand uses on purpose), suppress it on that line or on the line after the comment, with a reason:

```html
<!-- design-lint-disable P0-METRIC -- SLA from the signed contract, section 4 -->
<p>99.9% uptime</p>
```

Any comment syntax works (`/* */`, `<!-- -->`, `{/* */}`, `//`). The reason needs a space after `--`. Without a reason the suppression is ignored and reported.

## Structural tells the lint cannot see

Check these by eye in `design-review`:

- The page follows Hero → Features → Pricing → FAQ → CTA with no section that could only belong to this product.
- A grid of three equal cards, each an icon over a heading over two lines of text.
- The hero centers eyebrow, title, lede, and button on one axis. Center at most two of them.
- The nav is wordmark left, four links, button right; the footer is four link columns plus a social row. Fine when it serves the product, a tell when it is the only idea.
- A redrawn browser bar, phone frame, or code window around a screenshot.
- Every section has the same rhythm and spacing. Alternate a dense section with a breathing one.
- Decorative blobs, waves, or glows that mean nothing.
- Card inside a card.
- Pure `#000` on pure `#fff` as the only contrast idea; neutrals with no tint toward the brand hue.

## The 80/20 rule

About 80% proven patterns and 20% one distinctive choice. The 20% lives in a single place:

- One bold visual move: a typeface, a proportion, a color decision.
- Microcopy that could only belong to this product (see [microcopy.md](microcopy.md)).
- One interaction people remember, such as a number that settles, or a button that gives 2px.
- One detail only someone who used the product would add, such as a keyboard hint or a status in the product's own words.

Screenshot test: show the screen to someone outside the project. If they can tell which product it is, it has a point of view. If it could be anyone's, it is a template.
