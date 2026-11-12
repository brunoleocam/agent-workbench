---
name: design-discovery
description: Short design interview that turns a vague "I want it to look professional" into an approved design/brief.md with audience, task, tone, density, constraints, and decomposed references. Use at the start of a new product, site, or screen with no approved brief (entrevista de design, brief de design, referências visuais, começar o design, quero um visual profissional).
---

# Design discovery

First step of `design`. Produces `design/brief.md`, the input for [design-directions](../design-directions/SKILL.md).

Use when a new visual interface is starting and there is no `design/brief.md` with `status: approved`. Skip it when an approved brief exists; go to `design-directions`.

The person answering may have no design background. Never ask an abstract design question ("Which spacing scale?", "Glassmorphism or flat?"). Ask about their product and their users; the visual decisions come later, from rendered options.

## 1. Read before asking

Read the request, the README, the code, existing screens, and any earlier brief. Every answer you can get from them becomes `inferido` in the brief and is not asked. Example: a README that says "for small veterinary clinics" answers the audience question.

## 2. Ask once, with recommendations

Ask in a single message, **at most 5 questions**, only about what is still missing and would change the design. Typical gaps, in priority order:

1. Who uses it, and in what situation (desk, phone in a hurry, shared screen).
2. The one task the user must finish on the main screen.
3. The tone: how the product should talk.
4. Density: few things at a time, or a lot at once.
5. Hard constraints: brand colors or fonts that already exist, language, accessibility needs, things they dislike.

Rules for each question:

- Give a **recommended answer** already filled in, inferred from the context. The user can accept it with one word.
- Offer **at most 7 options**, in plain words. Merge near-duplicates.
- Always allow a free answer.
- In Claude Code, use the closed-choice question tool when available, recommended option first. Elsewhere, a numbered list with the recommendation marked.

Translate jargon into plain words:

| Jargon | Say instead |
| --- | --- |
| editorial | looks like a magazine or a book |
| minimal | few elements, a lot of empty space |
| dense / data-dense | many rows and numbers visible at once |
| brutalist | raw, strong, looks like a poster |
| playful | light, with humor |
| corporate | formal, institutional |
| bento grid | boxes of different sizes side by side |

## 3. Ask for references

Ask for **2 to 3 references**: links or screenshots of sites, apps, posters, or packaging they like, even from another industry. One sentence on what they like in each is enough.

If they have none, write in the brief that the direction starts from the brief alone, and continue. Do not invent references for them.

## 4. Decompose each reference

For each reference, fill three columns:

- **Keep**: qualities to borrow: density, rhythm, color temperature, type contrast, how photos are used.
- **Change**: what must differ: subject, content, exact layout.
- **Do not copy**: logos, product names, copy, prices, illustrations, proprietary screens.

Mark what you saw yourself as `observado` and what the user said as `fornecido`.

## 5. Write and approve the brief

1. Write `design/brief.md` from [references/brief-template.md](references/brief-template.md) with `status: draft`. Every item carries its origin: `fornecido`, `observado`, or `inferido`.
2. Show the brief in a short summary and ask for approval or corrections.
3. Only after the user's explicit approval, change it to `status: approved`.

Tone guidance for the brief comes from [../design/references/microcopy.md](../design/references/microcopy.md).

## Done when

`design/brief.md` exists with `status: approved`, every section filled or marked as not applicable, and every reference decomposed. Next step: [design-directions](../design-directions/SKILL.md).

Do not generate directions, a DESIGN.md, or code in this step.
