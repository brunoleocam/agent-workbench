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
- Plan drift check (branch `feat/plan-drift-check`): `check_drift.py` stamps and checks a per-file `Baseline` on pending tasks; `/implementation-plan` gains `Out of scope`, `Stop if`, and the stamp step; the `implementer` stops on unaccounted drift. Adapted from shadcn/improve (MIT).
- Language: rules, skills, agents' docs, templates, ADRs, references, and user-facing script messages are in English. The roadmap marker "You are here:" replaces "Você está aqui:" (the Portuguese form is still read). `README.pt-BR.md` stays as the Portuguese README. The Cursor-only rule files keep their Portuguese file names.

## Workflow graph front (branch `feat/workflow-graph`, not merged)

Spec: `docs/specs/workflow-graph.md` (approved, XL, four phases). Tasks: `docs/tasks/workflow-graph.md`.

- Phase 1, execution graph: done. `agent-system/workflow.json` (26 nodes, 54 edges, 7 human nodes, parallel review group joining at the gate, `limits.max_revisions` 3, `state_fields` owners); `workflow.py` (shared loading, validation, routing, Mermaid); `validate_workflow.py` (structure, `--mermaid`); `next_step.py` (router; `needs_decision` on human nodes, escalation after `max_revisions` failed gates); `state.json → revisions.<slug>` counted by `apply_semantic_state` on `VERIFICATION_COMPLETED`; README diagram with a drift test; orchestrator and `CLAUDE.md` block point to the router; the init copies the graph and the scripts; eval `revision-escalation`. TEST-001 to TEST-004 proven.
- Phase 2, decision trace: done. `artifacts.record(..., node=, inputs=, fingerprint=)` adds the trace to the completion events of the four validators (paths only, never content); `record_event.py --node --inputs` (unknown node exits 2); `timeline_view.py --feature <slug> [--json]` marks a verdict made on a different fingerprint. TEST-005 and TEST-006 proven.
- Phase 3, metrics: done. `metrics.py` (runs, durations, response chars, and tokens per agent; gates and revisions per feature; read only); the Claude Code `SubagentStop` hook reads only the usage numbers from `agent_transcript_path` (best effort; Cursor stays `unavailable`). TEST-007 and TEST-008 proven.
- Phase 4, global lessons: done. `lessons.py promote` and `--scope global` on add, list, confirm, and reject, stored in `$AGENT_WORKBENCH_HOME/lessons.json` (default `~/.agent-workbench/`); a leak filter refuses the project's path or name, absolute paths, URLs, and secrets; session start adds up to three global titles after the project's (the project wins on the same title); `"global_lessons": false` in `layout.json` turns it off. User docs (README.md, README.pt-BR.md, `/help`, `lessons` skill) updated. TEST-009 to TEST-011 proven.
- State: all 10 tasks done, 11 TESTs proven, suite 104 passed, evals 9/9. `validate_verification.py --feature workflow-graph` fails only on the missing review.
- Review 1 (reviewer agent): PASS_WITH_WARNINGS, FIND-001 (major) to FIND-006 (minor), all fixed with tests; suite 106 passed.
- Review 2: PASS, all six findings resolved. `validate_verification.py --feature workflow-graph` exits 0 (11 proofs on the current workspace, review fingerprint matches).
- Next: commit, push, and PR of `feat/workflow-graph`.

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
