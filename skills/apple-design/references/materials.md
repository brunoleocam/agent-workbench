# Materials, depth, and multimodal feedback

## Translucency signals hierarchy

Apple uses translucent materials as a functional floating layer that organizes without stealing focus. On the web, approximate it with `backdrop-filter`.

- Navigation bars, toolbars, and sheets as translucent layers (`backdrop-filter: blur()` + a semi-transparent background) with the content scrolling underneath, not opaque bars taking up a fixed strip.
- A material's weight encodes hierarchy: darker, denser materials separate structural regions (sidebars); lighter ones draw attention to interactive elements (buttons). Never stack a light translucent surface on another; legibility collapses.
- A larger surface looks thicker: stronger blur and a deeper shadow than on small chips. A heavier shadow over busy content or text; a lighter one over a plain background.
- Darken to focus, separate to keep the flow. A modal task: a surface with a dark scrim and the background pushed back. A parallel, non-blocking panel: translucency and displacement, no scrim. In stacked sheets, progressively darken and push back each parent layer.
- Text on a translucent surface: no flat gray. Use more contrast, slightly heavier weight, and a slight increase in letter-spacing. Color goes on a solid layer, not on the translucent foreground.
- Instead of a 1px divider under a fixed header, use a slight blur or a gradient mask where the content meets the floating element, only where there is real overlap.
- Materialize, don't just fade: on blurred surfaces, animate the blur radius and scale together on entry and exit.

```css
.toolbar {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid rgba(255, 255, 255, 0.4);
}
```

## Material accessibility

- `prefers-reduced-transparency: reduce`: a more solid surface, a more opaque background, no blur.
- `prefers-contrast: more`: a nearly solid background and a defined, contrasting border.

`prefers-reduced-transparency` does not have wide browser support yet. The default look must be legible without depending on that media query.

```css
@media (prefers-reduced-transparency: reduce) {
  .toolbar { background: white; backdrop-filter: none; }
}
```

## Multimodal feedback: motion, sound, and haptics

Three rules, from *Designing Audio-Haptic Experiences*:

1. **Causality**: it is obvious what caused the feedback. Fire on the real causal event (the toggle flipped, the item snapped) and match the character of the feedback to the physicality of the action.
2. **Harmony**: visual, sound, and haptic in the same frame. A delay between them breaks the illusion; do not let a CSS transition delay the sound or the vibration.
3. **Utility**: only where it is worth it. Reserve sound and haptics for relevant moments (success, error, confirmation, snapping). Excess teaches the user to ignore everything.

The Vibration API does not work on iOS Safari. On the web, haptics are a bonus on Android; the visual feedback must be enough on its own.
