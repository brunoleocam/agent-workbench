---
status: approved
complexity: L
security_risk: LOW
security_triggers: command_execution, file_system
approved_by: brunoleocam (Phase 1 plan, items 1.1, 1.2, N1 and addendum A)
---

# Spec: deterministic enforcement (0.7.0)

Problem: the gates of 0.6.1 are advisory. `next_step.py` only recommends, the hooks only observe, and the complexity that switches the gates on comes from the model. Calling an M feature S turns every gate off, and nothing stops a session that says "done" without `validate_verification.py` exiting 0. The timeline does not record the classification or which skills ran, so neither can be measured.

Outcome: a deterministic classification floor computed from the diff, a Claude Code `Stop` hook that keeps an M+ feature working until the gate passes (with an iteration limit, a cost budget, and escalation to the user), an optional CI check for pull requests, and skill and classification events in the timeline and in `metrics.py`.

## Requirements

### REQ-001: Classification floor
WHEN `classify_floor.py` runs with a declared complexity, THE SYSTEM SHALL measure the change against a git base (by default the base recorded for the feature, else the merge base with the default branch, else HEAD), counting renamed files as changed, binary files as one line, and attack surfaces by whole words of the path, compute a floor complexity, and fail with exit 1 when the declared complexity is below the floor.

### REQ-002: Recorded downgrade
IF the declared complexity is below the floor AND a justification is given, THEN THE SYSTEM SHALL accept the classification with a warning, record a `CLASSIFICATION_DOWNGRADED` event with the justification, and keep the declared complexity as the effective one.

### REQ-003: Classification in state and timeline
WHEN a classification is checked, THE SYSTEM SHALL record a `CLASSIFICATION_RECORDED` event and store, per feature, the declared, floor, and effective complexity, security risk, git base, and time in `state.json`; an M+ classification SHALL require a feature slug.

### REQ-004: Skill usage events
WHEN Claude Code invokes a skill through the Skill tool, or the user types a slash command that names a known plugin skill, THE SYSTEM SHALL record a `SKILL_USED` event with the skill name only, never the arguments or the prompt, ignore a bare slash command that is also a Claude Code built-in (`/help`, `/security-review`), and count a slash command followed by the Skill tool for the same skill once.

### REQ-005: Stop gate
WHEN the Claude Code main session stops, an opted-in project has an open M+ classification (any feature, not closed by a passing gate and not waived), and `validate_verification.py` does not exit 0 for it, THE SYSTEM SHALL block the stop with a reason that lists the gate failures; a gate that cannot run in time SHALL let the session stop.

### REQ-006: Unclassified large change
WHEN the main session stops with no open classification, no classification recorded for the current base, and a floor of M or larger, THE SYSTEM SHALL block the stop once per workspace state and ask for `classify_floor.py`.

### REQ-007: Loop limits and escalation
THE SYSTEM SHALL stop blocking and escalate to the user (a message and a `STOP_GATE_ESCALATED` event) when the stop gate has blocked `limits.max_revisions` times for the feature, when the feature's estimated cost passes its budget, or when a stop arrives with the workspace unchanged since the previous block (in the same turn or a later one); it SHALL block at most once per workspace state and send each escalation message once.

### REQ-008: Escape
THE SYSTEM SHALL skip the stop gate when `AGENT_WORKBENCH_STOP_GATE=off` is set or the user waived the feature with a `STOP_GATE_WAIVED` event, record a waiver only with a reason, and drop the waiver when the feature is classified again.

### REQ-009: CI gate
WHEN `ci_gate.py` runs on a pull request, THE SYSTEM SHALL find the features whose spec or tasks changed against the base or whose tasks list a changed file in `Files`, keep those that are M+ at the base or the head, fail a feature whose pull request lowers it below M (unless `--allow-downgrade`), run `check_proofs.py`, `check_mutation.py` when a minimum score is set, and `validate_verification.py` for each, and exit 1 when any of them fails; `init_project.py --with-ci` SHALL install a GitHub Actions workflow that runs it, without overwriting an existing file.

### REQ-010: Metrics
THE SYSTEM SHALL report in `metrics.py` the skill counts, the classifications with downgrades, and the stop gate blocks, escalations by reason, and waivers.

## Acceptance Criteria

### AC-001: Floor rejects a downgrade
- Requirements: REQ-001
Given a git project where 7 source files changed against HEAD
When `classify_floor.py --declared S` runs
Then it exits 1 and reports floor M.

### AC-002: Attack surface raises the floor
- Requirements: REQ-001
Given a change of one line in `src/auth/login.py`
When `classify_floor.py --declared XS` runs
Then it exits 1 with floor M and names the `authentication` surface.

### AC-003: Small change passes
- Requirements: REQ-001, REQ-003
Given a one-line change in a file outside every surface
When `classify_floor.py --declared XS --feature f` runs
Then it exits 0 and `state.json` holds the classification for `f` with the base commit.

### AC-004: Justified downgrade
- Requirements: REQ-002, REQ-003
Given the change of AC-001
When `classify_floor.py --declared S --justification "generated files"` runs
Then it exits 0, the timeline has `CLASSIFICATION_DOWNGRADED` with the justification, and the effective complexity is S.

### AC-005: Skill events hold names only
- Requirements: REQ-004
Given a PostToolUse payload for the Skill tool with arguments, and a UserPromptSubmit payload `/agent-workbench:tdd secret text`
When the hook runs
Then the timeline has two `SKILL_USED` events named `tdd` and no argument or prompt text.

### AC-006: Stop blocked while the gate fails
- Requirements: REQ-005
Given an opted-in project classified M for feature `f` whose gate fails
When the hook receives `Stop`
Then it returns `decision: block` with a reason naming `validate_verification.py --feature f`.

### AC-007: Stop allowed when the gate passes
- Requirements: REQ-005
Given the project of AC-006 after the gate passes
When the hook receives `Stop`
Then it returns no block.

### AC-008: Unclassified large diff
- Requirements: REQ-006
Given an opted-in project with 7 changed files and no classification
When the hook receives `Stop` twice with no change between them
Then the first reply blocks and asks for `classify_floor.py`, and the second (with `stop_hook_active`) does not block.

### AC-009: Limits escalate
- Requirements: REQ-007
Given the project of AC-006
When the stop gate already blocked `max_revisions` times, or the budget is exceeded, or a continued stop arrives with no workspace change
Then the hook does not block, returns a message for the user, and records `STOP_GATE_ESCALATED`.

### AC-010: Escape hatches
- Requirements: REQ-008
Given the project of AC-006
When `AGENT_WORKBENCH_STOP_GATE=off` is set, or a `STOP_GATE_WAIVED` event with a summary exists for `f`
Then the hook does not block; and `record_event.py --event STOP_GATE_WAIVED` without `--feature` exits 2.

### AC-011: CI gate
- Requirements: REQ-009
Given a git repo with a base commit and a later commit that adds an M spec with an unproven TEST
When `ci_gate.py --base <base>` runs
Then it exits 1 naming the feature; a repo where only an S spec changed exits 0; and `init_project.py --with-ci` writes the workflow once and keeps an existing one.

### AC-012: Metrics
- Requirements: REQ-010
Given a timeline with skill, classification, and stop gate events
When `metrics.py --json` runs
Then the report has `skills`, `classifications`, and `stop_gate` with the right counts.

### AC-013: Renames and committed work
- Requirements: REQ-001
Given 7 files moved with `git mv`, edited, and staged into `src/auth/`, or 7 files committed on a branch off `main`
When `classify_floor.py --declared XS` (or `S`) runs
Then the floor is M (with the `authentication` surface for the first case).

### AC-014: Thresholds and word matching
- Requirements: REQ-001
Given tracked changes of 5 then 6 files, or of 150 then 300 lines, and untracked `AUTHORS`, `docs/secretary_notes.txt`, and a binary file
When the floor is measured
Then it is S, M, S, M respectively, no surface is reported for the untracked names, and `src/AuthService.ts` reports `authentication`.

### AC-015: Once per workspace state
- Requirements: REQ-007
Given the project of AC-006 blocked once
When two more stops arrive with nothing changed
Then the second returns one message for the user without a block, the third returns nothing, and the block count stays 1.

### AC-016: Older failing feature still holds
- Requirements: REQ-003, REQ-005
Given the project of AC-006 and a later classification of another feature
When the hook receives `Stop`
Then it still blocks for `feat`.

### AC-017: CI follows code and refuses a self-downgrade
- Requirements: REQ-009
Given an M feature whose tasks list `src/coupon.py`
When a pull request changes only `src/coupon.py`, and then also lowers the spec to S
Then `ci_gate.py` checks the feature and exits 1 both times.

### AC-018: Built-in commands and repeats
- Requirements: REQ-004
Given `/help`, `/security-review`, `/agent-workbench:tdd` followed by the Skill tool for `tdd`, and `/agent-workbench:help`
When the hook runs
Then the timeline has `SKILL_USED` for `tdd` and `help` only.

### AC-019: Waiver ends with a new classification
- Requirements: REQ-008
Given a waiver for `feat`
When `feat` is classified again
Then the stop gate blocks again.

## Assumptions

- The project is a git repository; without git the floor is `unknown`, the classification is recorded with a warning, and the stop gate only uses the recorded classification.
- The Claude Code hook contract (Stop `decision: block`, `stop_hook_active`, `transcript_path`, the eight-block cap) is the one documented at code.claude.com/docs/en/hooks on 2026-11-19.

## Constraints

- Standard library only. Hooks fail open: any error returns `{}`.
- No secret, prompt, argument, or file content enters the timeline.
- Cursor keeps its current behavior; the stop gate is Claude Code only.

## Open Questions

## Decisions

- Cost budget in US$ from token counts and per-MTok rates configurable in `layout.json` (`stop_gate`), defaults for Claude Opus 5.5.
- One block per workspace state on a continued stop, so a session waiting on a human node can still stop.
