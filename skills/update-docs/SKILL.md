---
name: update-docs
description: Updates project documentation so specs, ADRs, verification notes, and progress match the behavior just changed. Use when the user asks to update docs, or when a meaningful change left specification or architecture docs stale (atualizar documentação, spec desatualizada, ADR).
---

# Update documentation

The docs describe what the system must do and the decisions in force. Do not rewrite history.

1. Read the repo's canonical docs before editing. If a place for specs or ADRs already exists, use it. Do not create the whole `docs/` tree in an old repo.
2. Update only what this change altered:
   - behavior → spec and acceptance criteria
   - new architecture decision → new ADR; do not edit the accepted ADR
   - verification → a note in `docs/tests/` or the test file the repo already uses for strategy
   - state of the front → `docs/progress/CURRENT.md` or the progress the repo already has
3. Do not document behavior you did not read in the code or verify.
4. Do not duplicate the same fact in two files. Point to the canonical one.
5. Do not create `AGENTS.md` in this flow.

Say which files changed and what behavior each now describes.
