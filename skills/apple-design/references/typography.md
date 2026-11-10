# Typography: optical size, tracking, and leading

From *The Details of UI Typography* (WWDC 2020). Apple designs the font to change shape with size; the same discipline applies on the web.

- **Tracking (letter-spacing) depends on size.** Large display text needs negative tracking, because letters look spread apart as they grow; small text needs slightly positive tracking. A fixed `letter-spacing` is wrong at some size. Tighten headings, leave body text near `0`.
- **Leading (line-height) is inverse to size.** Tight on large headings, looser on body text. Increase it for scripts with tall ascenders and descenders; tighten it in information-dense UI.
- **Hierarchy comes from weight, size, and leading together**, not size alone. Emphasize with weight: it gives presence without taking more space.
- **Respect the user's text size.** Scale the layout along with the text, with spacing in `rem`/`em`, not fixed px, so larger text does not break the layout.
- **Start with the system font.** It already brings optical size, tracking tables, and legibility tuning. Swap it only with a reason.

```css
:root { font: 100%/1.5 system-ui, sans-serif; }

.display {
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1.05;
  letter-spacing: -0.02em;
  font-optical-sizing: auto;
}
```
