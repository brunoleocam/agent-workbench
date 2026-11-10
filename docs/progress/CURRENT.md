# Current progress

State of the repository after versions 0.1 to 0.4.0 and the audit-improvements front. Everything before the audit front is merged into `main` (PRs #1 to #7).

## Delivered (merged)

- Deterministic core: `artifacts.py`, `validate_spec.py`, `validate_tasks.py`, `check_proofs.py`, `validate_verification.py` (the gate).
- `check_proofs.py` command policy (ADR-0002): no shell, an executable allowlist, best-effort refusal of install/publish by subcommand, refusal of inline code by default (`--allow-inline` only with authorization), shell only with `Shell: yes` + `--allow-shell`, process-tree termination on timeout.
- Workspace fingerprint from file contents (no HEAD), so a review recorded before a commit stays valid; the proof stores the fingerprint from before the run.
- Security: rule `08`, the `security-best-practices` and `security-review` skills, the `security-reviewer` agent, redaction of `Authorization`/Bearer/Basic in hooks and `timeline_view.py`.
- Lessons (`lessons.py`, ADR-0003): only the user confirms; `confirm` refuses an apparent secret.
- Deterministic evals (`run_evals.py`, 8 fixtures with real test files).
- Claude Code support (0.4.0): `.claude-plugin/` manifests, `hooks/claude-hooks.json` (the same `hook.py`, which translates the payload), `init_project.py --claude` writing the condensed rules into a managed block of the project `CLAUDE.md`, and `model: inherit` on the subagents.

## Audit-improvements front (branch `chore/audit-improvements`, not merged)

- Documentation: `agent-system/README.md` names both hook files; this file no longer describes already-merged work as uncommitted.
- Consistency: the `init_project.py` skill list is derived from `skills/`; new tests assert that `agents.json` matches `agents/*.md` and that skill names match their folders.
- Hooks: events are appended under a file lock and the duplicate-edit filter (`agg.json`) is locked and tolerates a corrupt file; the Claude Code hooks start with `python -I -S`; `re_failed` now reads runner summary lines instead of matching "failed" or "error:" anywhere in the output.
- Agents: `reviewer` and `security-reviewer` declare `tools: Read, Grep, Glob, Bash, Write` (no `Edit`).
- CI: `.github/workflows/ci.yml` runs the test suite and the evals on Ubuntu and Windows, Python 3.10 and 3.13.
- Adapted from outside projects (all MIT or the open specification): a refutation pass and a `mode: refute` for the `security-reviewer`, plus a Rejected Candidates section in the report (from Cloudflare's security-audit-skill); the "smallest sufficient change" ladder in rule `00`, the `CLAUDE.md` template, and the `implementer` (from ponytail); and a test that checks every skill against the Agent Skills specification (agentskills.io, as published in anthropics/skills).
- Language: rules, skills, agents' docs, templates, ADRs, references, and user-facing script messages are in English. The roadmap marker "You are here:" replaces "Você está aqui:" (the Portuguese form is still read). `README.pt-BR.md` stays as the Portuguese README. The Cursor-only rule files keep their Portuguese file names.

## Verification

```text
python agent-system/scripts/test_system.py
python agent-system/scripts/run_evals.py
```

## Known limits

- `check_proofs.py` is a guardrail, not a sandbox or a security boundary against malicious code (FIND-011, 017, 018, 019, accepted).
- macOS is not tested. CI covers Ubuntu and Windows only.
- Hooks call `python`; on Windows the Microsoft Store stub can shadow a real interpreter, and the hooks then fail open silently.
- Not yet tested: a real Claude Code session (substitution of `${CLAUDE_PLUGIN_ROOT}` in skills, hooks firing end to end).
