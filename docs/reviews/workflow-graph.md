---
status: PASS
reviewer: reviewer
fingerprint: 1bc706c5d7fbff158dc9930b7707576626f4b385420cf21f91c7148a71c30645
---
# Review: workflow graph (execution graph, decision trace, metrics, global lessons)

Scope: uncommitted working tree on `feat/workflow-graph` against `main` (HEAD 0493bfd). I compared the following in order: spec `docs/specs/workflow-graph.md` (approved, XL, LOW, with the post-review adjustments recorded under Decisions), tasks `docs/tasks/workflow-graph.md`, the TESTs and eval, then the implementation and docs. This is round 2. Round 1 (fingerprint `9d93fd6e…2949`) was PASS_WITH_WARNINGS with FIND-001 (major) and FIND-002 to FIND-006 (minor). The orchestrator fixed all six, and this round re-checks each by running it.

Commands run in round 2:
- `python agent-system/scripts/test_system.py`: 106 passed, 0 failed.
- `python agent-system/scripts/run_evals.py`: 9/9 passed.
- `python agent-system/scripts/validate_workflow.py`: exit 0, 26 nodes, 54 edges. The README drift test is part of the suite and passes.
- `check_proofs.py --fingerprint`: `1bc706c5…0645`. This equals the digest in `.cursor/agent-system/proofs/workflow-graph.json`, so the proofs are current.
- `next_step.py` probes:
  - `proofs` and `plan` without `--interface`: exit 2.
  - HIGH risk with a new UI: a three-branch fan-out joining at `gate`.
  - `design_review --result escalate`: goes to `accept_risk` with `needs_decision`.
  - `accept_risk` fail and `escalate` pass with `--interface new`: go to `frontend_implement`.
  - `accept_risk` fail with `--interface none`: goes to `implement`.
  - `classify`, whose edges do not depend on interface: still routes without `--interface`.
- Malformed graphs through `validate_workflow.py --json`:
  - List-valued `from`, dict `join`, list `on`, and a `null` edge: each gives a JSON `structure` error (exit 1), with no traceback.
  - A list-valued node id gives `node-missing-field`.
- `record_event.py` in a scratch opted-in project:
  - `--node gate` exits 2.
  - A forged `VERIFICATION_COMPLETED` without a node leaves `revisions` unchanged (`{}`).
- `lessons.leak()` on the 17 round-1 probes plus UNC and project-name probes (results under FIND-003).

This repository is not opted in, so no REVIEW_* events were recorded.

Verdict: PASS. Every round-1 finding is resolved, verified by running it, and covered by a test that would fail if the fix were reverted. No new blocker or major turned up.

## Verification Audit

Legend: Q1 the test matches the criterion; Q2 it checks behavior; Q3 a mutation that would slip through; Q4 negative cases; Q5 boundaries; Q6 assertion specificity; Q7 result vs implementation detail; Q8 untested condition; Q9 proof current.

Q9 holds for every TEST: the proofs file digest equals the current workspace fingerprint (`1bc706c5…0645`).

| AC | TEST | Q1-Q2 | Q3: mutation that passes | Q4-Q5 | Q8: untested |
| --- | --- | --- | --- | --- | --- |
| AC-001 plugin graph valid | TEST-001 | Yes. Runs the CLI; every non-orchestrator agent has a node; all 7 human ids exist. | None found. | n/a | none |
| AC-002 each error fails | TEST-001 | Yes. Each mutation gets exit 1, its code, and now a non-empty `ref` (test_workflow_graph.py:93). Malformed edge ends are included. Missing file and invalid JSON give exit 2. | None found. | Every REQ-007 error has a fixture. | none |
| AC-003 state ownership | TEST-001 | Yes. Code and ref for missing, unknown, and bad writer. | None found. | Yes | none |
| AC-004 Mermaid and drift | TEST-003 | Yes. Block equals `--mermaid`; a changed edge produces a different diagram. | None found. | An invalid graph gives no diagram. | none |
| AC-005 complexity routing | TEST-002 | Yes. | None found. | Missing `--class` gives exit 2. | XS/L/XL rest on the same rank comparison. |
| AC-006 fan-out | TEST-002 | Yes. HIGH, LOW, new UI, and now HIGH with new UI (three branches). | None found. | fail goes to fix_failure. | none |
| AC-007 designer | TEST-002 | Yes. Also asserts exit 2 when `--interface` is omitted at `proofs` and `plan`. | Restoring `default="none"` would now fail the test. | Yes | none |
| AC-008 human node | TEST-002 | Yes. | None found. | Terminal node returns `done`. | none |
| AC-009 escalation | TEST-002, TEST-004 | Yes, with real gate runs. `test_the_limit_comes_from_the_graph` uses `max_revisions: 1` and an absent `limits` (default 3). A forged event does not move the counter. `--node gate` is refused. The escalate answer resets the counter to 0. | Hard-coding 3 would now fail. | 2 vs 3, 0 vs 1, and the default are covered. | none |
| AC-010 orchestrator and init | TEST-003 | Text presence plus a behavioral check of the init copy. Both texts now name `--interface new\|existing\|none`. | None found. | Migration keeps existing values. | none |
| AC-011 verdict trace | TEST-005 | Yes. | None found. | n/a | none |
| AC-012 manual trace | TEST-005 | Yes. | None found. | Yes | none |
| AC-013 feature view | TEST-006 | Yes. | None found. | Yes | none |
| AC-014 metrics | TEST-008 | Yes, including a byte-for-byte read-only check. | None found. | Yes | none |
| AC-015 tokens | TEST-007, TEST-008 | Yes. Numbers only; transcript text and path are absent. | None found. | Yes | Large-file timing: 0.3 s for 51 MB, measured in round 1. |
| AC-016 promotion | TEST-009 | Yes. | None found. | Yes | none |
| AC-017 leak refusal | TEST-009 | Yes. Now includes `~/`, UNC, `www.`, `host.tld/`, and normalized and squashed project-name probes. | None found. | Yes | none |
| AC-018 injection and precedence | TEST-010 | Yes. `confirmed_at` is set explicitly, with the duplicate as the newest global lesson, so removing the dedupe would show it. | None found. | Opt-out covered. | none |
| AC-019 suite, eval, docs | TEST-011 + suite + evals | String presence, as the AC asks. | n/a | n/a | none |

Residual observations, none of them findings:
- The escalate reset is an event any caller of `record_event.py --node escalate` can write. The router only recommends, and `validate_verification.py` remains the hard barrier, so this matches the spec's Assumptions.
- The squashed project-name check (≥ 6 chars) and the `host.tld/` URL pattern can over-refuse. For example, `see lib.py/` is refused as a URL. That fails safe: the user rewrites the lesson.

## Findings

### FIND-001: A missing `--interface` silently routes a new UI past design, frontend implementation, and design review
- Severity: major
- Status: resolved
- Location: agent-system/scripts/next_step.py:47, agent-system/scripts/workflow.py:289-292, agent-system/templates/CLAUDE.md:15, agents/orchestrator.md:44
- Requirement: REQ-010, REQ-012, AC-007, AC-010
- Evidence (round 1): `--interface` defaulted to `none`. `--from proofs --complexity M --security LOW` returned only `review` for a new UI, and the `CLAUDE.md` block never mentioned the flag.
- Verification (round 2):
  - `--interface` has no default, and `match()` raises `this step depends on --interface (new, existing, or none)`.
  - `--from proofs --complexity M --security LOW` exits 2; `--from plan ...` exits 2.
  - `classify`, whose edges do not depend on interface, still routes.
  - The `CLAUDE.md` line and `orchestrator.md` name `--interface new|existing|none`, and `cli.md` documents the exit 2.
  - Tests: `test_next_step.py` (missing `--interface` gives exit 2; three-branch fan-out).
- Recommendation: none.

### FIND-002: The revision counter never resets after escalation and can be moved by manual events
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lib.py:439-462, agent-system/scripts/record_event.py:47-49
- Requirement: REQ-004, REQ-011
- Evidence (round 1): the counter stayed at 3 or more after the user answered, a manual `VERIFICATION_COMPLETED` incremented or reset it, and the trim to 50 kept insertion order.
- Verification (round 2):
  - The counter moves only for `VERIFICATION_COMPLETED` with `node: gate`. Only `validate_verification.py` writes that, because `record_event.py --node gate` exits 2 ("is a script node; only validate_verification.py records it").
  - An event with `node: escalate` and a feature resets the counter to 0. `orchestrator.md` and `cli.md` tell the orchestrator to record the user's answer with `REWORK_STARTED --node escalate`.
  - `set_revisions` pops and re-inserts the key before trimming.
  - Checked in a scratch project: the forged event left `revisions` as `{}`.
  - Test: `test_gate_failures_escalate_at_the_limit` (forged event, refused `--node gate`, reset by the escalate answer).
- Recommendation: none.

### FIND-003: The global leak filter misses home-relative paths, UNC paths, scheme-less URLs, and project-name variants
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lessons.py:33-34, agent-system/scripts/lessons.py:49-64
- Requirement: REQ-022, AC-017
- Evidence (round 1): `~/work/client-x/notes`, `~/.config/tool`, a UNC path, `www.example.com`, `example.com/path`, `Agent-Workbench`, and `AgentWorkbench` all passed.
- Verification (round 2):
  - With root `C:\Dev\Agent Workbench`, each of those is now refused: home-relative paths and UNC (`\\server\share\x`, `\\srv\x`) as absolute paths, `www.` and `host.tld/` as URLs, and both name variants as the project's name.
  - The 10 round-1 probes that were already refused still are.
  - `write integration tests` is not refused for a project named `testing`.
  - Test: `test_leak_filter_refuses_project_details`, with the new probes.
- Recommendation: none.

### FIND-004: Graph edges disagree with the orchestrator text on escalation and the frontend path
- Severity: minor
- Status: resolved
- Location: agent-system/workflow.json (`design_review`, `accept_risk`, and `escalate` edges), agents/orchestrator.md:42-44
- Requirement: REQ-005, REQ-012
- Evidence (round 1): `design_review --result escalate` went to `gate`. `accept_risk` fail and `escalate` pass ignored a new UI. The stale-proof shortcut was not in the graph.
- Verification (round 2):
  - `design_review --result escalate` goes to `accept_risk` (`needs_decision`).
  - `accept_risk` fail with `--interface new` goes to `frontend_implement`, and with `none` goes to `implement`.
  - `escalate` pass with `--interface new` goes to `frontend_implement`.
  - The graph validates with 54 edges, and the README drift test passes.
  - `orchestrator.md` marks the stale-proof shortcut as outside the graph.
  - Test: `test_escalations_and_new_ui_reach_the_right_nodes`.
- Recommendation: none.

### FIND-005: `validate_workflow.py` crashes on a malformed edge end instead of reporting it
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/workflow.py (`validate`)
- Requirement: REQ-007
- Evidence (round 1): `{"from": ["a"]}` raised `TypeError: unhashable type: 'list'`.
- Verification (round 2):
  - List `from`, dict `join`, list `on`, and a `null` edge each return JSON `{"code": "structure", "ref": "edge #54"}` (the `null` edge: `ref` empty) with exit 1.
  - A list-valued node id returns `node-missing-field`, without a crash.
  - Test: the malformed cases in `test_each_structural_error_fails`.
- Recommendation: none.

### FIND-006: Test gaps that let specific mutations pass
- Severity: minor
- Status: resolved
- Location: agent-system/tests/test_next_step.py:143-155, agent-system/tests/test_workflow_graph.py:93, agent-system/tests/test_global_lessons.py:126-127
- Requirement: REQ-004, AC-002, AC-018
- Evidence (round 1): the tests only ever used `max_revisions` 3, never asserted `ref`, and the dedupe test depended on timestamp ties.
- Verification (round 2):
  - `test_the_limit_comes_from_the_graph` covers `max_revisions: 1` (one failure escalates) and an absent `limits` (2 failures go to implement, 3 escalate).
  - `ref` is asserted for every expected error code.
  - `confirmed_at` is written explicitly, with the duplicate newest (`11:00:00`), so removing the dedupe would put it first in the global list.
- Recommendation: none.
