---
name: apple-design
description: Builds or reviews fluid, Apple-style interactive motion on the web — drag, swipe, sheets, carousels, spring animations, momentum, interruptible transitions, and reduced-motion fallbacks. Use when implementing or reviewing gesture-driven UI or spring animation (animação fluida, gesto, arrastar, swipe, sheet, drawer, spring, momentum, estilo Apple).
---

# Apple design: interactive motion on the web

Based on Apple's WWDC design talks, mainly *Designing Fluid Interfaces* (2018), translated to the web: CSS, Pointer Events, `requestAnimationFrame`, and spring libraries such as Motion.

It complements `ui-ux`: that one builds the screen and its states; this one defines how the interface moves and responds to touch.

Core principle: an interface feels alive when movement starts from the value currently on screen, inherits the user's velocity, projects momentum forward, and can be grabbed and reversed at any instant. Springs solve this because they are interruptible and accept an initial velocity.

References, load only when the request touches the subject:

- [references/materials.md](references/materials.md): translucency, depth, `backdrop-filter`, sound and haptic feedback.
- [references/typography.md](references/typography.md): tracking, leading, optical size, the system font.
- [references/principles.md](references/principles.md): Apple's eight design principles, feedback, navigation, and process.

## 1. Immediate response

- Give feedback on `pointerdown`, not on `click`. Highlight the button at the instant of touch; confirm the action on `pointerup`.
- Cut latency on the input path: debounce, artificial timers, waiting for a transition. Make sure `<meta name="viewport" content="width=device-width">` and `touch-action: manipulation` are set so there is no tap delay.
- On a drag, slider, or drawer, update the interface 1:1 with the pointer throughout the gesture, not just at the end.

```css
.button:active {
  transform: scale(0.97);
  transition: transform 100ms ease-out;
}
```

On iOS Safari, `:active` only fires if the page has a touch listener. For a critical component, prefer a class applied on `pointerdown`.

## 2. Direct manipulation

The element follows the finger from the point where it was grabbed. Jumping to the element's center breaks the illusion.

- Use Pointer Events with `setPointerCapture`, so tracking continues outside the element's bounds.
- Keep a short history of position and timestamp from the last `pointermove` events; the release velocity comes from it.

```js
el.addEventListener('pointerdown', (e) => {
  el.setPointerCapture(e.pointerId);
  const grabOffset = e.clientY - el.getBoundingClientRect().top;
  // record position + timestamp on each pointermove to compute velocity
});
```

## 3. Interruption

The most important principle: every animation can be grabbed and redirected at any moment. A closing modal that the user grabs again follows the finger; it does not finish closing and then reopen.

- Never block input during a transition.
- Always animate from the value presented on screen, never from the target value. On interruption, read the current transform and start from there.
- For gestures, do not use CSS transitions or `@keyframes`. An interrupted transition does reverse from the current value, but it loses the velocity and jolts. Springs carry velocity on re-target.
- When a gesture reverses, the new animation inherits the current velocity. Replacing one animation with another from zero creates a velocity "wall".
- 2D movement: one independent spring for X and another for Y. A single spring over the 2D distance goes out of sync when the velocities differ.

## 4. Springs instead of fixed duration

A fixed-duration animation does not respond to new input. In a spring, new input only changes the target and the motion continues. Use a spring for everything the user can touch.

Apple uses two parameters instead of mass, stiffness, and damping:

- **Damping ratio**: controls overshoot. `1.0` = critically damped, no bounce. Below `1.0` it bounces; the lower, the more it bounces.
- **Response**: how quickly it reaches the target, in seconds. Lower = snappier. It is not a duration; the settling time emerges from the parameters.

Defaults:

- Start with damping `1.0`.
- Use damping near `0.8` only when the gesture carried momentum (flick, throw, releasing a drag). Bounce on a menu that merely appeared is wrong; on a thrown card it is right.

| Interaction | Damping | Response |
| --- | --- | --- |
| Move / reposition (e.g. PiP) | `1.0` | `0.4` |
| Rotation | `0.8` | `0.4` |
| Drawer / sheet | `0.8` | `0.3` |

In Motion, `bounce` and `visualDuration` approximate damping and response: `bounce ≈ 1 − damping` and `visualDuration ≈ response`. It is an approximation; tune by eye.

```js
import { animate } from 'motion';

animate(el, { y: 0 }, { type: 'spring', bounce: 0, visualDuration: 0.4 });

// light bounce, only because a flick came before
animate(el, { y: target }, { type: 'spring', bounce: 0.2, visualDuration: 0.4, velocity: releaseVelocity });
```

## 5. Velocity handoff

When the gesture ends, the animation continues at the finger's exact velocity, with no visible seam between dragging and animating. This is the detail that most separates "fluid" from "okay".

Pass the release velocity as the spring's initial velocity. Motion accepts absolute px/s in the `velocity` option. For APIs that ask for relative velocity:

```
relativeVelocity = gestureVelocity / (target − currentValue)
```

Example: element at `y=50`, target `y=150`, finger at 50 px/s → `50 / 100 = 0.5`.

## 6. Momentum projection

Do not pick the snap point closest to where the finger released. Project where the element would stop, like scroll deceleration, and snap to the point closest to the projection. This makes a flick feel like a throw.

```js
// decelerationRate ≈ 0.998 for a normal scroll feel; 0.99 for snappier
function project(initialVelocity /* px/s */, decelerationRate = 0.998) {
  return (initialVelocity / 1000) * decelerationRate / (1 - decelerationRate);
}

const projectedEndpoint = currentPosition + project(releaseVelocity);
const target = nearestSnapPoint(projectedEndpoint);
animateSpringTo(target, { velocity: releaseVelocity });
```

This is the function from Apple's sample code. Do not use the physics formula `v²/(2·deceleration)`. To decide between closing and returning, use the sign of the velocity at release, not just the position.

## 7. Spatial consistency

- Enter and leave by the same path. A panel that enters from the right leaves to the right.
- Anchor to the trigger: a menu, popover, or sheet is born from the element that opened it. Use `transform-origin` on the trigger's side, not the center.
- Intermediate motion points toward the result. The Control Center modules "grow up and out, toward the finger".
- For a reversible transition without a gesture, mirror the curve: forward and back with inverted cubic-bézier control points. With a gesture, use a spring.

## 8. Rubber-band at the limits

At the limit, resist progressively instead of stopping dead. A dead stop looks like a freeze; continuous resistance says "it responds, but there is nothing more here".

```js
function rubberband(overshoot, dimension, constant = 0.55) {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
}
```

## 9. Gesture details

- Tap: highlight on down, confirm on up. About 10px of margin around the target; allow canceling by dragging out and back.
- Drag and swipe: a threshold of about 10px before locking the direction, then track 1:1.
- Recognize all possible gestures in parallel from the first movement and cancel the losers once the intent is clear. Avoid recognizers that only report the final state (events like `swipeleft`).
- Detecting a double tap delays the single tap. Only pay that cost where a double tap exists.

## 10. Smoothness per frame

- Animate only `transform` and `opacity`. Use `will-change` when motion is imminent and remove it afterward.
- `requestAnimationFrame` is the clock synchronized with the screen.
- Keep the per-frame displacement below the perception threshold to avoid a strobing effect. In very fast motion, a slight blur or stretch conveys speed better than a sharp trail.

## 11. Reduced motion

Reduced motion is not the absence of feedback; it is an equivalent without vestibular motion.

- With `prefers-reduced-motion: reduce`, replace slide, spring, and parallax with a short fade or an instant change. Remove the bounce. Keep the opacity and color changes that help understanding.
- Remove the animation, not the position. A sheet closed with `translateY(100%)` stays off screen; it just stops sliding.

```css
@media (prefers-reduced-motion: reduce) {
  .sheet { transition: opacity 200ms ease; }
}
```

```js
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

animate(el, { y: target }, reduceMotion
  ? { duration: 0 }
  : { type: 'spring', bounce: 0, visualDuration: 0.4 });
```

Also avoid full-screen moving backgrounds, slow looping oscillation (near 0.2 Hz), and abrupt brightness jumps; soften the switch between light and dark themes.

## Review

When reviewing an interaction, go through the list and report only what fails, with file and line:

1. Does feedback appear on `pointerdown`?
2. Does the drag respect the point where the element was grabbed and use `setPointerCapture`?
3. Can you grab the animation midway and reverse it without a jump?
4. Does the animation start from the on-screen value and inherit the release velocity?
5. Does snapping use momentum projection and the sign of the velocity?
6. Does bounce only appear after a gesture with momentum?
7. Do the limits use rubber-band?
8. Entry and exit by the same path, anchored to the trigger?
9. Are only `transform` and `opacity` animated?
10. With reduced motion, does the element end up in the right position, with no slide or spring?

Format: `[fail] file:line — what happens — suggested fix`. If nothing fails, say so in one line.

## Quick reference

| Need | Technique | Value |
| --- | --- | --- |
| Default spring | Critically damped | damping `1.0`, response `0.3–0.4` |
| Spring after a flick | Slight bounce | damping `~0.8`, response `0.3–0.4` |
| Gesture → spring | Pass the release velocity | `velocity / (target − current)` if relative |
| Flick stopping point | Project momentum | `current + (v/1000)·d/(1−d)`, `d ≈ 0.998` |
| Interrupt | Start from the on-screen value | read the current transform |
| Close or return | Sign of the velocity | at release |
| 1:1 drag | Pointer Events + capture | respect the grabbed point |
| Limit | Rubber-band | progressive resistance |
| Reduced motion | Fade or jump, position kept | `prefers-reduced-motion` |
