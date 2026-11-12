# Review checklist

Every question must be answered "no". Each "yes" is a defect to fix before delivery. P0 blocks delivery; P1 should be fixed; P2 is polish.

## P0: blocks delivery

1. Does the lint report any P0 (`lint_design.py`)?
2. Does any body text have contrast below 4.5:1 against its actual background, including text on the accent, on images, and in dark sections?
3. Does any large text (24px and up, or 18.66px bold), icon, or focus ring have contrast below 3:1?
4. Does any button have text nearly the same color as its fill?
5. Can any interactive element be reached by mouse but not by keyboard, or does it lack a visible `:focus-visible` style?
6. Does any control lack an accessible name (icon-only button without `aria-label`, input without a label)?
7. Is any information carried by color alone (status, error, selection)?
8. Does the page scroll horizontally at any width from 320px to 1920px?
9. Does any number, testimonial, logo, or customer name appear that the user did not provide?

## P1: should fix

10. Can a first-time viewer fail to tell what the main action is within two seconds?
11. Is any touch target smaller than 44px in either dimension on touch layouts?
12. Does any button label, nav link, tab, or CTA wrap to two lines between 320px and 1920px?
13. Is any reading column outside 45 to 75 characters per line?
14. Does any component lack a state it can be in: hover, focus-visible, active, disabled, loading, error, empty?
15. Does the empty state leave the user without a next action?
16. Does any error message omit what to do next, or appear far from the field it concerns?
17. Is any padding, gap, or margin off the spacing scale?
18. Does an input have a different height from the button next to it?
19. Is disabled shown with opacity only, without `cursor: not-allowed` and `aria-disabled` or `disabled`?
20. Do two icon sets appear on the same screen?
21. Is any animation missing a reduced-motion fallback, or does it animate `width`, `height`, `top`, `left`, or `margin`?
22. Does the screen follow Hero → three equal cards → CTA, or repeat the structure of the previous screen, with only colors changed?

## P2: polish

23. Is the accent used on more than two elements in the viewport?
24. Do all sections share the same spacing and rhythm, with no alternation between tight and breathing?
25. Is there a decorative element (blob, glow, sticker, badge) with no meaning in the content?
26. Does a success toast confirm something the user can already see?
27. Does a tooltip wait before appearing on keyboard focus, or appear instantly on mouse hover? (It should be the reverse: instant on focus, 800 to 1000 ms on hover.)
28. Is a card nested inside another card?
