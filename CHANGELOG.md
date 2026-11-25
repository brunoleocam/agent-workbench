# Changelog

Versions before 0.7.0 are summarized under "New in" in the README.

## Unreleased

### Changed

- Rule 03 asks for a test with two or more processes on the same store for code that keeps shared state, including startup initialization. Found in the benchmark's medium round (a start race in 2 of 9 runs).
- `architecture-discovery`, `architecture-options` and `architecture-review` are explicit commands (`disable-model-invocation`), like the other stage-style skills. The `architecture` pipeline still links them. Their descriptions no longer load in every session. The remaining skills are unchanged: the benchmark saw 0 of 42 used, but agents and rules refer to the others by name, so cutting them needs a separate decision.

### Added (spec first)

- `PreToolUse` check (`spec_first.py`): before the first production code file of a project with no spec and no recorded classification, the write is denied once or twice with the reason (classify small work, or write the spec first). It allows the write after a classification or any spec exists, never denies more than twice, and `AGENT_WORKBENCH_SPEC_FIRST=off` turns it off. Found in the benchmark: the spec followed the code in 6 of 6 plugin runs.

### Fixed

- The Stop gate no longer escalates `no_progress` while the agent is writing the spec, tasks, review, or proofs after a block. Its progress check now includes those documents, which the workspace fingerprint leaves out on purpose. Found in the benchmark's simple round (3 of 3 runs).
- The Stop gate no longer escalates `no_progress` while a subagent (for example the reviewer) has started and not yet stopped. Its work is progress that has not landed. `max_blocks` still caps the loop. Found in the benchmark's medium round.

### Added

- `validate_verification.py` warns `spec-after-code` when the Stop gate had to ask for the classification before the feature was classified (the spec followed the code). It is a warning for the reviewer and fails only with `--strict`.

## 0.7.0 (2026-11-19)

### Added

- `classify_floor.py`: a deterministic floor for the declared complexity, measured from the git diff (files, lines, attack surfaces). A declaration below the floor exits 1 unless a justification is recorded as `CLASSIFICATION_DOWNGRADED`.
- Claude Code `Stop` hook goal loop: an M+ feature cannot end the session while `validate_verification.py` fails. It escalates to the user after `max_revisions` blocks, at a per-feature cost budget, or with no progress. Escapes: `AGENT_WORKBENCH_STOP_GATE=off` and `STOP_GATE_WAIVED`.
- `ci_gate.py` and `init_project.py --with-ci`: a pull request check that runs the proofs and the gate for changed M+ features.
- `check_mutation.py`: an optional mutation proof for Python files listed in `Mutate:`. With `mutation_min_score`, the gate requires a fresh score.
- `SKILL_USED` events (the Skill tool and typed plugin slash commands, names only). `metrics.py` now reports skills, classifications, and stop gate activity.
- Evals: `downgrade-refused`, `stop-gate-loop`, `mutation-catches-weak-test`, `mutation-strong-tests`. `run_evals.py` supports git fixtures and hook steps.
- ADR-0004 (declared test runner, proposed), ADR-0005 (work queue and issue to PR, design only), ADR-0006 (isolation for untrusted code, design only).
- `docs/progress/skill-inventory.md`.

### Changed

- In Claude Code the main session is the only orchestrator. The `orchestrator` agent is no longer "use proactively" and no longer delegates when it runs as a subagent.
- The `CLAUDE.md` block gains the classification floor, the Stop gate, mutation, and a condensed context-economy section.
- `feature-development` merged into `feature`; `lean-investigation` merged into `debug` (section "Reading little"). There are now 42 skills.
- Fourteen skill descriptions shortened, from about 12,400 to about 9,100 characters of listing text.

### Fixed

- `layout.json` `proof_allow` was dropped by `resolve_layout` and never reached `check_proofs.py`.

### Removed

- The Cursor-only rules `mcp-triagem-obrigatoria` and `uso-ferramentas-mcp`. Projects initialized before keep a copy in `.cursor/rules/` until it is deleted by hand.

### Upgrade

Run `/init-agent-system` again in each project to copy the new scripts. Add `--with-ci` for the pull request workflow.
