---
name: staged-task
description: Splits a large request into small steps, each with a verification, and executes one at a time, validating before moving on. Use when the request touches several files or components, has several parts, or the user asks to do it in parts (etapas, dividir, por partes, passo a passo, fatiar).
---

# Staged task

If the work follows the spec-driven flow (M or larger in rule `01-request-classification`), the steps are the spec's tasks; this skill only controls execution. It does not create a PRD, ADR, or detailed plan (that is `/implementation-plan`).

1. Plan: 3 to 7 steps, one line each, in the format `N. <deliverable> — verification: <test, command, or check>`. Each step can be verified alone and leaves the system working.
2. Order: dependencies first; the highest-risk step as early as possible.
3. Show the plan. Ask for confirmation only if there is a decision for the user (scope, approach); otherwise start with step 1.
4. In each step: edit only what is needed and run its verification with filtered output.
5. Verification failed: fix it within the step. Do not advance with a red step. If you must change the plan, adjust it and say so in one line.
6. Step closed: one line `Step N ok: <evidence>`. Do not repeat the whole plan.
7. Stop and ask the user when the step requires their decision or a validation you cannot do (visual, external environment, credential).
8. At the end: a short list of the steps with status. If the conversation got long, offer `/context-summary`.
