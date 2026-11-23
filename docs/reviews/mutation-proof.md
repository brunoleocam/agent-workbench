---
status: PASS_WITH_WARNINGS
reviewer: reviewer
fingerprint: 8ca545c12f9f4054aecd7bef9b7c4ecef08f5e8838a8fd05ddde96578a201302
---
# Review: mutation proof (0.7.0), final pass

Scope: the earlier passes covered `466f2c6..22a68ee`; the final pass adds `git diff 22a68ee..HEAD` (commit 419fd17: the original mtime is kept in `pending.json` and restored, a dead lock is taken over by `os.replace`, the live-lock message mentions a reused PID, and the gate's PASS line shows kills by timeout). The third pass covered the fixes in `git diff c6ac742..22a68ee` (commit 22a68ee): check_mutation.py (PID lock, uncapped default, `truncated`, `timeouts`), validate_verification.py (`mutation-partial`), the spec (AC-011, AC-012), the tasks, and tests/test_mutation.py.

Proof state: `validate_verification.py --feature mutation-proof --no-record` reports 3 required checks proven on the current workspace (fresh). The project is not opted in, so no review events were recorded. Only this file and docs/reviews/enforcement.md were written. Every experiment ran in scratch copies with `PYTHONDONTWRITEBYTECODE` unset.

## Verification Audit

| AC | TEST | Matches | Would fail if broken / mutation that survives | Gaps |
|----|------|---------|-----------------------------------------------|------|
| AC-001, AC-002 | TEST-003 | Yes | Yes | None |
| AC-003..AC-010 | TEST-001, TEST-002 | Yes | Yes (audited in pass 2) | None |
| AC-011 | TEST-001 (`lock_protects_a_live_run`, `lock_of_a_dead_run_is_taken_over`) | Yes | Yes. Restoring before taking the lock fails the live-run test, which checks that the file and backup are untouched. | The takeover race and a reused PID are not tested (FIND-011). |
| AC-012 | TEST-002 (`refuses_a_partial_mutation_run`) | Yes, for `--max-mutants 1` | Yes. Deleting the `mutation-partial` branch fails it. | The cut by `--budget-seconds` is not tested. It sets the same `truncated` flag the gate checks, so the risk is low. |

Independent checks (third pass, code unchanged in these paths except `acquire`'s takeover and `restore_pending`'s mtime):
- **Concurrent runs:** my pass-2 reproduction, rerun. Run 2 started while run 1 was mutating and got `exit 2: another check_mutation.py run (process 16888) holds .agent-system/mutation.lock`. Run 1 finished, and `src/coupon.py` is byte-identical to the original.
- **Killed run:** run 1 killed with `taskkill /F` in the middle of a mutant. `check_proofs.py` then refused with the "may still be mutated" error, and the next `check_mutation.py` printed `restored files left mutated`. The file is byte-identical, and the lock and the backup folder are gone.
- **Partial runs:** `--max-mutants 1` is now refused by the gate (`mutation-partial`).

### FIND-001: Stale bytecode makes the score non-deterministic
- Severity: blocker
- Status: resolved
- Location: agent-system/scripts/check_mutation.py (mtime per mutant, restored mtime, `PYTHONDONTWRITEBYTECODE`)
- Requirement: REQ-001, REQ-002, AC-006
- Evidence (resolution): verified in pass 2 with plain and `python -I` TEST commands; `test_mutation_ignores_stale_bytecode`.

### FIND-002: The score is not bound to the Mutate targets
- Severity: major
- Status: resolved
- Location: agent-system/scripts/validate_verification.py (`mutation-targets-changed`)
- Requirement: REQ-004, AC-009
- Evidence (resolution): `test_gate_rejects_a_score_for_other_targets_or_commands`.

### FIND-003: An invalid minimum silently disables the gate
- Severity: major
- Status: resolved
- Location: agent-system/scripts/artifacts.py (`mutation_threshold`)
- Requirement: REQ-004, AC-008
- Evidence (resolution): `test_mutation_minimum_must_be_valid`.

### FIND-004: CI cannot pass for a feature with a minimum
- Severity: major
- Status: resolved
- Location: agent-system/scripts/ci_gate.py (mutation step)
- Requirement: REQ-004, enforcement REQ-009
- Evidence (resolution): `test_ci_gate_runs_the_mutation_proof` (exit 1 and "mutation score 0.0" for a weak TEST).

### FIND-005: A killed run's leftovers; restore outside the root
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/check_mutation.py:127-148; check_proofs.py; validate_verification.py
- Requirement: REQ-002, AC-007
- Evidence (resolution): proofs and the gate refuse while a backup is pending, and the restore applies `inside()`. The kill experiment above confirms the end-to-end behavior.

### FIND-006: Non-UTF-8 sources are decoded with replacement
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/check_mutation.py (`mutate_file`)
- Requirement: REQ-003
- Evidence (resolution): `test_mutation_refuses_non_utf8_source`.

### FIND-007: The cost of a run is unbounded in practice
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/check_mutation.py (per-mutant cap, `--budget-seconds`)
- Requirement: REQ-003
- Evidence (resolution): each mutant is capped at 5x the slowest baseline (at least 10 s), and the run has a time budget. A run cut by the budget is now partial and fails the gate, so the cap can no longer be used to pass.

### FIND-008: The concurrency lock does not work while a run is mutating; overlapping runs leave the source mutated
- Severity: blocker
- Status: resolved
- Location: agent-system/scripts/check_mutation.py:255-290 (`acquire`, `release`)
- Requirement: REQ-002, AC-011
- Evidence (resolution): an `O_CREAT | O_EXCL` lock file holding the PID is taken before any restore. A live holder gives exit 2 and leaves everything untouched; a dead holder is taken over, and its backup is then restored. My original reproduction now refuses the second run, and the file stays byte-identical (see the checks above). The kill-and-recover path also works. Edge cases are in FIND-011.

### FIND-009: `--max-mutants` and `--budget-seconds` let a small sample pass the gate
- Severity: major
- Status: resolved
- Location: agent-system/scripts/check_mutation.py (`mutate_file` truncation, default `--max-mutants 0`); validate_verification.py (`mutation-partial`)
- Requirement: REQ-004, AC-012
- Evidence (resolution): by default every mutation site is run. A run capped by `--max-mutants` or cut by the time budget is marked `truncated`, and the gate fails it before it compares the score (`test_gate_refuses_a_partial_mutation_run`). The pass-2 bypass (`--max-mutants 1` turning 0.5 into a passing 1.0) now fails.

### FIND-010: A slow machine can count a mutant as killed
- Severity: minor
- Status: resolved
- Resolution: the gate's PASS line now reports how many kills were timeouts (validate_verification.py `check_mutation_scores`), so a score inflated by timeouts is visible at the gate. Counting timeouts as kills is kept on purpose and documented, as in common mutation tools. The 5x cap still has no test, a gap too small for its own finding. Original evidence below.
- Location: agent-system/scripts/check_mutation.py (`mutate_file` outcome handling; `options.timeout` cap)
- Requirement: REQ-001
- Evidence: timeouts still count as kills. They are now reported per file in `timeouts` and documented, which matches common mutation tools. The gate message does not show the timeout count, so a score inflated by timeouts on a loaded runner is not visible at the gate. The 5x cap has no test.
- Recommendation: either accept this as residual risk (it needs the user's decision and a Justification), or add the timeout count to the gate's `mutation` and `mutation-score` messages.

### FIND-011: Lock edge cases: takeover race, reused PID, and the restore mtime after a killed run
- Severity: minor
- Status: open
- Final-pass update:
  - **Restore mtime: resolved.** `pending.json` stores `mtime_ns`, `restore_pending` restores it, and `test_mutation_restore_keeps_the_modification_time` covers it.
  - **Reused PID: resolved.** The live-lock error now says to delete the lock when no run is active.
  - **Takeover race: still open, though the window is narrower.** In `acquire` (agent-system/scripts/check_mutation.py:270-285), a run that read a dead holder calls `os.replace(lock, ...)` without checking what it is moving. Two runs, A and B, both read the dead PID. A renames the stale lock and creates its own with `O_EXCL`. If B's `os.replace` lands after A's create, B moves A's *live* lock aside and creates another, and both runs mutate. The code comment ("the other cannot remove the lock the winner creates next") holds only when B renames before A creates. This still needs two runs to start at the same moment right after a crash.
  - **Recommendation:** after the rename, read the moved file. If it does not hold the dead PID, rename it back and refuse. Better, hold an OS lock on the lock file (`msvcrt.locking` on Windows, `fcntl.flock` elsewhere), which the OS releases when the process dies, so no takeover logic is needed.
- Original evidence:
- Location: agent-system/scripts/check_mutation.py:127-148 (`restore_pending`), 255-280 (`acquire`)
- Requirement: REQ-002
- Evidence:
  - **Takeover race.** Two runs that start at the same moment after a crash can both read the dead PID. The first deletes the lock and creates its own, and the second then deletes that *fresh* lock (`lock.unlink()`, line 274) and creates another, so both proceed. The window is narrow.
  - **Reused PID.** A PID the operating system reused (common on Windows) makes a dead lock look live forever. The error says only "wait for it to finish", with no hint to delete the lock.
  - **Restore mtime.** `restore_pending` uses `shutil.copyfile`, so after a killed run the file gets the current time rather than its original mtime. With a `python -I` TEST (which ignores `PYTHONDONTWRITEBYTECODE`), a same-size mutant's `.pyc` written at a future mtime could then match. That needs a recently edited file and an exact one-second collision.
- Recommendation:
  - Take over a stale lock by atomic rename (`os.replace` of a fresh temporary lock), then re-read it to check ownership. Store the process start time next to the PID.
  - Name the lock file in the error so the user can delete it.
  - Store the original `st_mtime_ns` in `pending.json` and restore it in `restore_pending`.
