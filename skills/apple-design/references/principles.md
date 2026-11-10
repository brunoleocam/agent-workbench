# Design principles and process

The eight principles from *Principles of Great Design* (WWDC 2026), cited by the original skill. Use these names when justifying a design decision.

1. **Purpose.** Make with intent and decide what not to build. Every feature costs the user time, attention, and trust; spend only where it pays off.
2. **Agency.** The user in control: offer choices, not a single path. Forgive mistakes with easy undo; confirmation dialogs only for destructive, irreversible actions. Excess confirmation teaches clicking without reading.
3. **Responsibility.** Act in the user's interest. Privacy: ask at the right time, only what is needed, with transparency. Safety: anticipate misuse and harm, especially with AI. Use previews, confirmation, and warnings; cut the feature whose risk outweighs its value.
4. **Familiarity.** Build on what people already know. Metaphors neither too literal nor too abstract (trash can = delete), respecting their physics. What looks the same behaves the same and sits in the same place. Break a familiar pattern only if you can prove the new one is better, and test it.
5. **Flexibility.** Design for different contexts, devices, and abilities. Phone is quick touch; desktop is deep flow with a precise pointer. Include age, language, experience, and accessibility. When no layout serves everyone, let people customize.
6. **Simplicity, not minimalism.** Remove what is unnecessary so the purpose shows; hiding everything in one place looks minimal but is not simple. Direct language, fewer steps, clear hierarchy through order, spacing, and contrast. Sometimes adding context simplifies. The common path first; the advanced option one level down.
7. **Craft.** Attention to detail builds trust: typography, colors that adapt to light and dark, clear icons, responsive animation. No value is arbitrary; every spacing, timing, and alignment has a justification. Jittery scrolling and a misaligned icon look careless.
8. **Delight.** The result of getting the other seven right, not confetti stuck on top. Decide the emotion (calm, confidence, excitement) and reinforce it in every decision.

## Tactical rules

- **Feedback has four types:** status, completion, warning, and error. Confirm relevant actions, expose in-progress status, warn before the problem, validate inline and not only on submit.
- **Orientation.** Every screen answers: where am I, where can I go, what is there, how do I leave. Never trap the user.
- **Grouping and mapping.** Proximity indicates relation. Put the control near what it affects, organized like what it changes. If the control needs a label to explain it, the mapping is weak.
- **A specific label beats a generic one.** Name navigation by its content ("Progress", "Library"), not by vague umbrellas ("Home").

## Process

- Prototype interactively. A working prototype is worth more than many static screens and fixes a concrete pattern for the final version.
- Design interaction and visuals together; motion is not a layer applied after the pixels.
- Test with real people in a real context. Review the motion in slow motion or frame by frame to catch what goes unnoticed at normal speed.
