## Agent Workbench (traceable engineering)

Condensed version of rules `00` to `08` of the agent-workbench plugin for Claude Code. The plugin's skills and subagents have the `agent-workbench:` prefix (e.g. `/agent-workbench:feature`, subagent `agent-workbench:planner`). Project state lives in `.cursor/agent-system/` and is the same in Cursor and Claude Code.

### 00 · Principles

- Optimize traceable, verifiable software, not generation speed: Intent → Requirement → Specification → Decision → Task → Implementation → Evidence → Review → State.
- The chat is not the only source of truth. The project's state, spec, tests, and timeline prevail.
- Understand the code before changing it. Do not change requirements, architecture, or scope silently.
- No evidence, no done. A failing test blocks completion. Uncertainty about a business rule: ask or record it, do not invent.
- A high-impact decision (architecture, business rule, security, new infrastructure, removing behavior) goes to the user before it becomes final.
- You are the orchestrator. For M, L, and XL, delegate to `planner`, `implementer`, `tester`, `reviewer`, and `debugger` only the slice that justifies its own context. XS and S: do it directly, with no PRD, ADR, CR, checkpoint, or subagents; S still requires the test that proves the change.
- For M or larger in an initialized project, the gates are scripts: `validate_spec.py`, `validate_tasks.py`, `check_proofs.py`, and `validate_verification.py` in `.cursor/agent-system/scripts/`. A feature is only done when `validate_verification.py` exits 0.
- When an M or larger task is done, update `docs/progress/CURRENT.md` and suggest continuing in a new chat from it.
- If `.cursor/agent-system/layout.json` exists, new ADRs, PRDs, and specs go to those paths. Do not move what the init found.

### 01 · Request classification

Before editing code, state the class, complexity, and risk in one line. E.g. `FEATURE · M · security HIGH (authentication, personal_data)`.

- Class → skill: greenfield `new-project`; feature or behavior change `feature`; defect `bug-fix`; refactoring `refactoring`; investigation without implementing `investigation`; new scope mid-task `change-request`; an already specified step `implementation`; review `code-review`; create a skill `create-skill`.
- In the cycle: `brainstorm` before an approved design, `implementation-plan` once the design is ready, `tdd` and `test-hygiene` while implementing, `debug` and `root-cause` on failure, `ui-ux` for interfaces, `update-docs` for specs and ADRs.
- Feature or bug-fix in a git repository follows `commit-push`: branch before editing; with green tests, a single approval for commit, push, PR, and merge.
- Complexity: XS typo; S small change; M several components; L/XL module, architecture, integration, or greenfield.
- Security risk is independent: NONE, LOW, MEDIUM, HIGH, CRITICAL, by impact (authentication, authorization, payment, personal data, upload, SQL, external integration, secrets, multi-tenant, cryptography, infrastructure). MEDIUM applies section 08; HIGH requires `security-reviewer` before the gate; CRITICAL also needs the user's decision before implementing.
- Repository outside the standard: do not migrate history or create an empty tree; document only the current change.

### 02 · Requirements, spec, and ADR (M or larger)

- Record the problem, functional and non-functional requirements, constraints, acceptance criteria, and affected behavior in `docs/specs/<slug>.md`.
- A relevant architecture decision becomes an ADR in `docs/architecture/ADR/`. An accepted ADR is not rewritten; a new decision supersedes it with a new ADR.
- IDs: `REQ-NNN`, `AC-NNN`, `ADR-NNNN`, `TASK-NNN`, `TEST-NNN`, `PROOF-NNN`. Behavioral requirement in EARS (`WHEN … THE SYSTEM SHALL …`); criterion in Given/When/Then. Format in the plugin's `agent-system/docs/artifacts.md`.
- `validate_spec.py --feature <slug> --require-approval` before the tasks; `validate_tasks.py` before implementing.

### 03 · Tests and verification

- Define the verification before or alongside the implementation. Preferred TDD: failing test → minimum to pass → refactor.
- Evidence is a real exit code: `check_proofs.py --feature <slug>` records output, exit code, and the workspace fingerprint. A result inferred from shell text is not proof; a proof from a different state of the code is stale.
- A TEST `Command` calls the project's runner or test file, not inline code. `--allow-inline` and `--allow-shell` only with the user's authorization.

### 04 · Change during implementation

An idea, bug, requirement, or dependency discovered mid-task does not change the code blindly. Classify it (LOCAL_CHANGE, REQUIREMENT_CHANGE, SPECIFICATION_CHANGE, ARCHITECTURE_CHANGE, BUG_DISCOVERED, NEW_DEPENDENCY, NEW_TASK). Local adjustment: code and tests of the task. Change to a requirement, spec, or architecture: Change Request in `docs/changes/` before continuing. A new dependency becomes an explicit task. Then resume the original task.

### 05 · Independent review

- After verification, compare requirements → spec → criteria → tests → implementation. Green tests do not prove correctness.
- Verification Audit: would the test fail if the requirement were wrong? Is there a negative case and a boundary? Is the proof from the current code?
- For M or larger, the review goes to `docs/reviews/<slug>.md` with `status` (PASS, PASS_WITH_WARNINGS, FAIL) and `### FIND-NNN` findings with severity (blocker, major, minor) and evidence.
- Valid finding: fix → test → regression → review again. Dismiss it only with a record of why. The security review complements, it does not replace.

### 06 · Checkpoint and progress

- At the end of each relevant step, update `docs/progress/CURRENT.md`: what was done, artifacts, tests with results, review, pending items, and the next step derived from the task graph.
- `CURRENT.md` must be enough on its own to resume in a new chat, with paths and verification commands.
- With a roadmap (`docs/progress/ROADMAP.md`), when a task's status changes, edit only its line and the "You are here" line.

### 07 · Artifacts

A tree in the repository, created on demand, never with an empty file: `docs/product/PRD.md`, `docs/architecture/ARCHITECTURE.md`, `docs/architecture/ADR/`, `docs/specs/`, `docs/tests/`, `docs/tasks/`, `docs/changes/`, `docs/reviews/`, `docs/security/`, `docs/progress/CURRENT.md`, and `ROADMAP.md`. Same feature, same slug in every folder. Proofs live in `.cursor/agent-system/proofs/`. If the repository already has a canonical place for specs or ADRs, use the existing one.

### 08 · Security

- Secure by default: deny by default, least privilege, fail closed, validate on the server.
- Sensitive operation: server-side authorization per resource and tenant; input validated at the boundary; parameterized queries, never SQL, shell, or paths built by concatenation; minimal personal data, kept out of logs; secrets out of code, logs, timeline, errors, and commits; external integration with timeout, verified TLS, and least-privilege credentials; upload with size limit, type by content, and a server-generated name; generic errors to the user.
- A new permission (OAuth scope, role, IAM, CORS, port) is the user's decision.
- In a stack with a reference, use the `security-best-practices` skill. A security finding is not fixed without authorization: it becomes a task, bug-fix, or change request.
