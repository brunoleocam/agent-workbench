---
status: PASS_WITH_WARNINGS
reviewer: reviewer
fingerprint: 8ca545c12f9f4054aecd7bef9b7c4ecef08f5e8838a8fd05ddde96578a201302
---
# Review: deterministic enforcement (0.7.0), final pass

Scope: the earlier passes covered `466f2c6..22a68ee`; the final pass adds `git diff 22a68ee..HEAD` (commit 419fd17: `open_features` skips escalated features and, once they have been blocked, features with no spec or tasks in this checkout; a justified downgrade covers the unclassified check only up to its recorded floor). The third pass covered the fixes in `git diff c6ac742..22a68ee` (commit 22a68ee): stop_gate.py (`MAX_OPEN`, once-per-feature limit escalation, the grown-change check), ci_gate.py (merge base, removed or superseded specs), hook.py (slash/tool dedupe), the workflow template comment, the spec (AC-020..AC-023), the tasks, and tests/test_enforcement.py.

Proof state: `validate_verification.py --feature enforcement --no-record` reports 8 required checks proven on the current workspace (fresh). The project is not opted in, so no review events were recorded. Only this file and docs/reviews/mutation-proof.md were written. Every experiment ran in scratch copies.

## Verification Audit

| AC | TEST | Matches | Would fail if broken / mutation that survives | Gaps |
|----|------|---------|-----------------------------------------------|------|
| AC-001..AC-004, AC-013, AC-014 | TEST-001, TEST-007 | Yes | Yes (checked in pass 2) | FIND-015 (documented) |
| AC-005, AC-018, AC-023 | TEST-002 | Yes | Yes. A dedupe that also swallows tool-to-tool repeats fails `count_two_real_uses` (`["debug", "debug"]`). | None |
| AC-006..AC-010, AC-015, AC-019 | TEST-003, TEST-008 | Yes | Yes | None |
| AC-016 | TEST-003 (`keeps_an_older_failing_feature...`, `newer_dead_feature_does_not_shadow_an_older_one`) | Yes, now including two open M features | Yes. The new test fails on the previous stop_gate.py (per the orchestrator), and my scenario confirms it. | None |
| AC-020 | TEST-003 (`asks_again_when_the_change_outgrows...`) | Yes | Yes. Restoring the "any classification on this base" shortcut fails it. | Justified-downgrade case now tested (FIND-018 resolved). |
| AC-021 | TEST-003 (`limit_escalates_once_per_feature`) | Yes | Yes | None |
| AC-011, AC-017, AC-022 | TEST-004 | Yes | Yes. The CI mutation step is now proven (`runs_the_mutation_proof` asserts "mutation score 0.0" and exit 1). Removed and superseded specs fail, and `--allow-downgrade` gives exit 0. | None |
| AC-012 | TEST-005 | Yes | Yes | None |

Final pass: my FIND-017 reproduction (`feat` M with a failing gate, then `ghost` M with no spec) now gives block (ghost) once, then block (feat) three times, then the limit message for feat once, then `{}`. The grown-change scenario still blocks and asks for `classify_floor.py`. I found no remaining way for the gate to trap a session, or to stay silent for a failing open feature, before that feature escalates.

Safety, rechecked: blocks still need a workspace change, and limit and budget escalations are now sent once per feature. One gate run per stop fits the 20 s hook. Errors and timeouts fail open. Projects that are not opted in, Cursor, and privacy are unchanged.

### FIND-001: Renamed files are dropped from the floor
- Severity: blocker
- Status: resolved
- Location: agent-system/scripts/classify_floor.py:155
- Requirement: REQ-001
- Evidence (resolution): `--no-renames`. Reproduced in pass 2: floor M, 16 files, `authentication`. `test_floor_counts_staged_renames` covers it.

### FIND-002: The floor is measured against HEAD, so committing resets it
- Severity: major
- Status: resolved
- Location: agent-system/scripts/classify_floor.py:60-80
- Requirement: REQ-001, REQ-006
- Evidence (resolution): the merge base with the default branch when on another branch; reproduced in pass 2. Commits on the default branch itself are FIND-015.

### FIND-003: The block budget is shared across user turns
- Severity: major
- Status: resolved
- Location: agent-system/scripts/stop_gate.py (once-per-state check)
- Requirement: REQ-007
- Evidence (resolution): `test_stop_blocks_once_per_state_across_turns`; verified in pass 2.

### FIND-004: The recorded classification is global and never cleared
- Severity: major
- Status: resolved
- Location: agent-system/scripts/classify_floor.py:226-250
- Requirement: REQ-003, REQ-005
- Evidence (resolution): classifications are kept per feature and closed when the gate passes. The `MAX_OPEN = 1` change reintroduces part of this for two open M features; see FIND-017.

### FIND-005: The numstat path and the thresholds have no effective test
- Severity: major
- Status: resolved
- Location: agent-system/tests/test_enforcement.py
- Requirement: REQ-001
- Evidence (resolution): boundary and rename tests now exist; verified in pass 2.

### FIND-006: ci_gate never runs check_mutation
- Severity: major
- Status: resolved
- Location: agent-system/scripts/ci_gate.py (mutation step)
- Requirement: REQ-009
- Evidence (resolution): `test_ci_gate_runs_the_mutation_proof` asserts exit 1 and "mutation score 0.0" for a weak TEST with a minimum.

### FIND-007: CI scope bypassed by leaving docs alone or lowering complexity
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/ci_gate.py
- Requirement: REQ-009
- Evidence (resolution): `Files`-based selection and the max of base and head complexity (`test_ci_gate_keeps_the_base_complexity_and_follows_task_files`).

### FIND-008: Substring surface tokens and binary line counts
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/classify_floor.py:27-40, 83-122
- Requirement: REQ-001
- Evidence (resolution): whole-word matching and binary files counted as one line (`test_floor_word_matching_and_binary_files`). One residual remains, too small for a finding: `line_count` still reads the whole untracked file to test 8 KB.

### FIND-009: A typed built-in command is logged as a plugin skill
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/hook.py
- Requirement: REQ-004
- Evidence (resolution): `test_skill_events_skip_builtins_and_duplicates`.

### FIND-010: The gate blocks without a counter or on a gate error
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/classify_floor.py:275-277; stop_gate.py (`run_gate`)
- Requirement: REQ-007
- Evidence (resolution): M+ requires `--feature`, and a timeout fails open without resetting the counter.

### FIND-011: The agent can waive its own gate
- Severity: minor
- Status: open
- Location: agent-system/scripts/record_event.py:35-37; agent-system/templates/CLAUDE.md:14
- Requirement: REQ-008
- Evidence: unchanged from pass 2. The orchestrator proposes to keep it as a documented limitation. I agree it is minor. The orchestrator will put it to the user; moving it to `accepted` needs the user's decision and a Justification, so it stays open.
- Recommendation: the user decides whether to accept it. If not, surface the last session's waivers in SessionStart context.

### FIND-012: An early small classification silences the unclassified-change check
- Severity: major
- Status: resolved
- Location: agent-system/scripts/stop_gate.py (`unclassified`)
- Requirement: REQ-006, AC-020
- Evidence (resolution): a classification on the base now covers the check only when its effective complexity reaches the current floor. `test_stop_asks_again_when_the_change_outgrows_an_early_classification` covers it. Residual: FIND-018.

### FIND-013: An open feature with no spec on the current branch blocks, then sends a message on every change
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/stop_gate.py (`escalate`, `open_features`)
- Requirement: REQ-007
- Evidence (resolution): reproduced again. A spec-less M feature `ghost` blocked 3 times, sent the limit message once (stop 4), and then stayed silent (stops 5-6). `MAX_OPEN = 1` bounds the gate time. Checking only the newest open feature has a new cost, reported as FIND-017.

### FIND-014: A PR skips the CI gate by superseding, deleting, or renaming its spec
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/ci_gate.py (`merge_base`, `removed_large`)
- Requirement: REQ-009, AC-022
- Evidence (resolution): the base complexity is read at the merge base, and a removed, renamed, or superseded M+ spec fails unless `--allow-downgrade` is passed (`test_ci_gate_fails_a_removed_or_superseded_large_spec`). The template now tells users to protect the workflow file. A PR editing its own workflow is a documented CI limit.

### FIND-015: Committed work on the default branch is still measured against HEAD
- Severity: minor
- Status: open
- Location: agent-system/scripts/classify_floor.py:60-80
- Requirement: REQ-001
- Evidence: unchanged (reproduced on `main` in pass 2), and the spec documents it. The orchestrator proposes to keep it as a documented limitation; accepting it needs the user's decision.
- Recommendation: record the session's start commit at SessionStart and use it as the base on the default branch.

### FIND-016: Remaining test gaps and the skill-count side effect
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/hook.py (`repeated_skill`); agent-system/tests/test_enforcement.py
- Requirement: REQ-004, REQ-006, REQ-009
- Evidence (resolution): the dedupe now pairs a slash command only with the Skill tool call that follows it (`test_skill_events_count_two_real_uses`). The CI mutation, grown-change, and dropped-spec tests now exist. State is now written only for slash events and for the pairing.

### FIND-017: With two open M+ features, only the newest is checked; a dead or exhausted newest feature switches the gate off for an older failing one
- Severity: major
- Status: resolved
- Resolution: `open_features` (agent-system/scripts/stop_gate.py:169-198) skips features that have escalated at a limit, and features with no spec or tasks in this checkout once they have been blocked. Reproduced: ghost blocks once, then feat is gated (3 blocks and one limit message). `test_stop_newer_dead_feature_does_not_shadow_an_older_one` covers it. Original evidence below.
- Location: agent-system/scripts/stop_gate.py:34, 169-177, 215-233
- Requirement: REQ-005 ("an open M+ classification (any feature ...)"), AC-016
- Evidence: `open_features()` returns `[:MAX_OPEN]` (1), the newest open classification. A feature stays open until its gate passes or the user waives it, so it can shadow every older feature indefinitely. Reproduced in a scratch copy of the complete-feature fixture:
  1. `classify_floor.py --feature feat --declared M`, where the gate fails because no proofs exist.
  2. Then `--feature ghost --declared M` (a feature whose spec is on another branch).
  3. Six stops, each after an edit, gave: block (ghost) x3, then the limit message for ghost once, then `{}`, `{}`.

  `feat` was never checked, and its failing gate never blocked. The same happens with two real M features once the newer one reaches `max_blocks` or the budget. The test for AC-016 classifies the second feature as S, so it cannot see this.
- Recommendation: keep one gate run per stop, but pick the feature to check better:
  - skip features whose gate exits 2 because the spec or tasks file is missing, and features that have already escalated for `max_blocks` or the budget;
  - otherwise rotate through the open features across stops.

  Add a test with two open M features (one spec-less or exhausted) and assert that the older one blocks.

### FIND-018: A justified downgrade on the base covers any later growth of the change
- Severity: minor
- Status: resolved
- Resolution: a downgrade now covers the check only while its recorded `floor` reaches the current floor (stop_gate.py `unclassified`). `test_stop_asks_again_when_the_change_outgrows_a_justified_downgrade` covers it. Original evidence below.
- Location: agent-system/scripts/stop_gate.py (`unclassified`, the `item.get("downgraded")` clause)
- Requirement: REQ-006
- Evidence: any classification on the same base with `downgraded: true` returns `{}`, whatever the current floor. An early `--declared XS --justification "..."` against an S floor therefore suppresses the M+ ask for the rest of the branch, the same way FIND-012 did with a plain XS. It needs a recorded justification, which leaves an audit trail.
- Recommendation: let a downgrade cover only the floor it was justified against (store `floor` and compare it with `found["floor"]`).
