# ADR-0001: Traceable artifact format

Status: accepted
Date: 2026-11-03

## Context

The validators need to read specs, tasks, tests, and reviews with no external dependency. The project already keeps documents in Markdown at the paths in `layout.json`, and TLC uses `.specs/`.

## Decision

- Markdown remains the format. A traceable item is a `##`–`######` heading that starts with the ID (`### REQ-001: title`). The block runs to the next heading of equal or higher level.
- The block's fields are `- Key: value` lines with known keys (list in `agent-system/docs/artifacts.md`). The rest of the block is free text (EARS, Given/When/Then).
- Simple `key: value` front matter at the top of the spec and the review (`status`, `complexity`, `security_risk`). No full YAML.
- One file per feature, with the same slug in each folder: `<specs>/<slug>.md`, `<tasks>/<slug>.md`, `<tests>/<slug>.md` (optional), `<reviews>/<slug>.md`, `<security>/<slug>.md`.
- Paths come from `layout.json` (`overrides` first), with `docs/...` as the default. `.specs/` is not imposed.

## Alternatives

- A YAML or JSON block inside the Markdown: an easier parser, but worse reading for people and agents, and YAML would require a dependency.
- TLC's `.specs/`: would break the layout of existing projects.

## Consequences

- Old specs without IDs remain valid as text and do not go through the validators.
- The parser recognizes only known keys, so prose with a colon does not become a field by mistake.
