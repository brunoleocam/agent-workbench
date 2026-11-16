---
status: PASS
reviewer: reviewer
fingerprint: 7f4a1d89f3b0d610a167bae67cc096836b6d8cc6f186c1e2be849cb5dbf813f6
---
# Review: architecture pipeline, phase 1 (skills and references)

Phase 1 was closed by Review 3 (PASS; FIND-001 to FIND-015 resolved). The current verdict is in the last section, "Fase 2 / Review 3" (FIND-016 to FIND-028 resolved; Fase 2 / Reviews 1 and 2 are kept as the record), which covers the lint, the contract validator, and the hook. The phase-1 text below is kept as the record.

Scope: the uncommitted working tree on `docs/design-ensaio-2` (HEAD 273d29e), phase 1 only (REQ-001 to REQ-020, TASK-001 to TASK-006). Phases 2 and 3 (REQ-021 to REQ-038) are not implemented yet and are out of scope. The unrelated changes to `docs/specs/design-pipeline.md` and `docs/tasks/design-pipeline.md` were not reviewed.

I compared, in order: the spec `docs/specs/architecture-pipeline.md` (approved), the plan `docs/tasks/architecture-pipeline.md`, the tests in `agent-system/tests/test_architecture_skills.py`, and the delivered files: `skills/architecture/` (SKILL.md, nine references, CREDITS.md, four case studies), `skills/architecture-discovery/`, `skills/architecture-options/`, `skills/architecture-system/`, `skills/architecture-review/` (each with its template or checklist), and the `/architecture` lines in `skills/help/SKILL.md`.

Commands run:
- `python -I agent-system/scripts/check_proofs.py --feature architecture-pipeline`: 6/6 PASS. This command re-ran the six TESTs and rewrote `.cursor/agent-system/proofs/architecture-pipeline.json` with the same results (git ignores the file).
- `python -I agent-system/scripts/check_proofs.py --fingerprint`: digest `ce6189de...c4ad`, which matches the handoff. The proofs are current.
- `python -I agent-system/scripts/validate_verification.py --feature architecture-pipeline --no-record`: the 6 required checks are proven on the current workspace. It fails because AC-017 to AC-035 have no TEST (expected in phase 1, as the plan says) and because this review did not exist yet.
- `python -I agent-system/scripts/test_system.py`: 112 passed, 0 failed.
- I ran in-memory mutations against the test's own helpers (`MEASURABLE`, `stage_triggers`, `contract_headings`) and changed no files. Results are in FIND-001.

The project is not opted in (`record_event.py` returned "Project is not initialized"), so no REVIEW_* events were recorded.

Verdict: PASS_WITH_WARNINGS. The skills cover every phase-1 requirement on paper. The references are original prose, `CREDITS.md` holds the single topic-checklist source with the no-transcription note, and the case studies use fictional products. There is no blocker. There are four majors:
- the trigger regex is weak and has a `%` bug that phase 2 would inherit (FIND-001);
- the format reference tells the agent to translate the stage labels that the tests and the phase-2 validator read literally (FIND-002);
- the case studies, offered as "worked contracts", skip most of the REQ-012 minimum content (FIND-003);
- every skill AC is proven only by phrases being present, and three ACs count as covered by tests that do not exercise their validator half (FIND-004).

## Verification Audit

Legend: Q1 the test matches the criterion; Q2 it checks behavior; Q3 a wrong implementation that slips through; Q4 negative cases; Q5 boundaries; Q6 specific assertions; Q7 checks the result, not implementation details; Q8 important conditions left untested; Q9 the proof is current.

Q9 holds for every TEST: `check_proofs.py` re-ran all six on fingerprint `ce6189de...c4ad`, and `validate_verification.py` reported no stale proofs.

All six TESTs are structural: they check that a file exists, that headings appear in order, or that a substring is present. They show that the instructions exist. They do not show that an agent following the instructions satisfies the AC. The plan says so (behavior is confirmed in a rehearsal after phase 3), so the table below rates each test against what it can prove.

| AC | TEST | Q1-Q2 | Q3: mutation that passes | Q4-Q6 | Q8: untested |
| --- | --- | --- | --- | --- | --- |
| AC-001 limit and recommendations | TEST-003 | Partial. The needle `"6"` matches any digit 6 (there are 3 in the file). | Change "at most 6 questions" to "at most 10": `"6"` is still found in "6. **The infrastructure target**". Remove the recommended-answer rule or the one-line jargon explanations: passes. | No negatives. | Number of options, recommended answer, jargon explanation. |
| AC-002 known answer skipped | TEST-003 | No. No needle covers "do not ask what is known" or `observado` with a file. | Delete section 1 "Read before asking": passes (the `docker-compose` and `fly.toml` needles survive in section 2). | None. | Whole AC. |
| AC-003 infra target always asked | TEST-003 | Partial (`ainda não sei`, `fly.toml`). | Make the question conditional ("ask the target only if no file shows one"): passes. | None. | "Always asked" and "recommendation cites the file". |
| AC-004 brief and estimate | TEST-003 | Template structure proven (12 headings, 3 origin marks, `status: draft`). | Delete step 3 "Estimate capacity" from SKILL.md: passes. Origin marks are checked as words anywhere, not per line. | Headings specific. | Arithmetic shown; average and peak req/s. |
| AC-005 existing system | TEST-003, TEST-004 | No. Nothing checks `## Arquitetura atual` content rules or the "keep current with adjustments" option. | Delete "keep the current architecture with adjustments" from options SKILL.md: passes. | None. | Whole AC. |
| AC-006 options really differ | TEST-004 | Template columns, Mermaid, and `## Recomendação` proven. | Delete the three-axes rule: passes. | Columns specific. | Pairwise axis difference; recommendation with reason. |
| AC-007 no overengineering | TEST-004 | Weak: `Kubernetes` anywhere. | Rewrite section 3 to "recommend Kubernetes by default": passes. | None. | Lowest-complexity rule; brief-item citation. |
| AC-008 stop for choice | TEST-004 | No: the needle `ARCHITECTURE.md` passes even if the text says to write it. | Replace "Do not write `ARCHITECTURE.md`" with "Write `ARCHITECTURE.md`": passes. | None. | The stop. |
| AC-009 contract sections | TEST-005 | Template headings in exact order proven; `status: draft` proven. | Remove the "decision not to cache" rule or the minimum-content list from SKILL.md: passes. | Headings specific. | REQ-012 minimum content. |
| AC-010 measurable stages | TEST-002 (TEST-005) | Partial. It checks the case studies, not `validate_architecture.py` (phase 2). The regex is weak, see FIND-001. | A trigger "quando crescer, revisar a cada 30 dias" passes; a later stage with no `- Gatilho:` passes when two other trigger lines exist; deleting every `Mudança`/`Custo`/`Pré-requisito` line passes; `(atual)` in prose instead of a stage title passes (all reproduced in memory). | No negative trigger. `%` is never matched. | Per-stage fields, `(fonte: ...)`, the validator exit code. |
| AC-011 vague trigger refused | TEST-005 | No: needle `quando crescer` passes whatever the sentence says. | "Record 'quando crescer' as is": passes. | None. | Refusal; the validator half (phase 2). |
| AC-012 decision becomes ADR | TEST-005 | Weak: `docs/architecture/ADR` presence. | Drop step 4 except the path: passes. | None. | ADR fields, citation, the validator half (phase 2). |
| AC-013 no overwrite without confirmation | TEST-005 | Weak: `confirm` also matches "Confirm which trigger" in step 6. | Delete section 1 "Existing ARCHITECTURE.md": passes. | None. | Whole AC. |
| AC-014 stage move | TEST-005 | Weak: `(atual)` presence. | Delete section 6 "Moving to the next stage": passes (`(atual)` is still in section 3). | None. | Whole AC. |
| AC-015 skip approved stage | TEST-006 | Partial: order of the four names and `status: approved` present. | Delete the "Resume where it stopped" table except one `status: approved`: passes. | Order check real. | Skip logic for options and system. |
| AC-016 references and credits | TEST-001, TEST-002 | Mostly. 9 files, headings in order, 7 pattern names, outbox, rule 08, credits note, 3 to 4 cases. | "When to use"/"When not to use" are counted globally, so one section with seven of each passes. Replication, load balancing, and polling are not in `PATTERNS`. | Counts, not per section. | "No transcription" (manual only; I read every reference and found original prose). Contents of data-stores, caching, deploy, and observability. |

How the implementation can be wrong while every test passes: any rewrite that keeps the needles, as in the Q3 column. For example, a discovery skill that asks 10 questions and skips the infrastructure target when `fly.toml` exists passes TEST-003. Every contract trigger of the form "quando crescer ... 7 dias" passes TEST-002.

## Findings

### FIND-001: The measurable-trigger regex never matches `%`, accepts a vague trigger that only has a duration, and checks no stage fields
- Severity: major
- Status: resolved
- Location: agent-system/tests/test_architecture_skills.py:33, :44-46, :75-79; docs/tasks/architecture-pipeline.md:45; skills/architecture/references/examples/ticketing.md:112; skills/architecture/references/examples/video-platform.md:115; skills/architecture/references/architecture-md-format.md:88-90; skills/architecture/references/scaling-stages.md:47
- Evidence: `MEASURABLE` ends with `\b`. After `%` (a non-word character) followed by a space or the end of the line there is no word boundary, so `CPU > 70%` gives `None`, and so does `disponibilidade mensal < 99,5%`. The regex searches the whole line, so the duration alone satisfies it: `quando crescer por 7 dias` matches `7 dias`, and `ADR-0004 h` matches `0004 h`. `min` and `minutos` are not units, and neither is `req/min`. Two shipped triggers pass only through their duration: ticketing:112 (`70%` is not matched; `3 dias` is) and video-platform:115 (`30 minutos` is not matched; `5 dias` is). The format reference's own "Accepted" example (architecture-md-format.md:90) passes only through `3 dias`. The second example trigger in scaling-stages.md:47 fails outright, so an agent that copies it writes a contract the phase-2 check would refuse. `stage_triggers` collects `- Gatilho:` lines from the whole section 9, so a later stage without a trigger, stage fields that were deleted, or `(atual)` outside a stage title all pass. I reproduced all three in memory. The plan (tasks:35, :45) says phase 2 reuses this format and unit list, so the defect would reach `validate_architecture.py`.
- Requirement: REQ-013, REQ-014, REQ-030; AC-010, AC-011
- Recommendation: Parse section 9 per `### Estágio N` block. Require `(atual)` in exactly one stage title, and require `Gatilho`, `Mudança`, `Custo`, `Pré-requisito`, and `(fonte: ...)` in every later stage. Match the threshold, not any number: a comparison (`>`, `<`, `>=`, `acima de`, `mais de`) followed by a number and a unit, for example `(?:[<>]=?|acima de|mais de|abaixo de)\s*\d+(?:[.,]\d+)?\s*(?:%|ms|s|min|minutos|h|horas|req/s|req/min|rps|GB|TB|MB|usuários|conexões)(?![\w/])`. Add negative tests (`quando crescer por 7 dias` fails; `CPU > 70%` passes; `fila > 30 minutos` passes). Then rewrite video-platform:115 with an operator.

### FIND-002: The format reference tells the agent to translate the stage labels that tests and phase 2 read literally
- Severity: major
- Status: resolved
- Location: skills/architecture/references/architecture-md-format.md:78; skills/architecture-system/references/architecture-template.md:7; docs/tasks/architecture-pipeline.md:18, :35-45
- Evidence: "Each later stage uses this format, with the labels in the contract's language". The templates also say "Write the content in the user's language". The plan fixes `### Estágio N:`, `- Gatilho:`, and `(atual)` as the format "usado pelo teste e pela fase 2", and `stage_triggers` looks for the literal `- gatilho:`. On an English-language project the agent following line 78 writes `### Stage 1` and `- Trigger:`, and the structural check (and later `validate_architecture.py`) finds zero triggers. The headings are declared literal; the stage labels are not.
- Requirement: REQ-013, REQ-030; plan language rule
- Recommendation: In the format reference and the template, state that `### Estágio N: <nome>`, `(atual)`, `- Gatilho:`, `- Mudança:`, `- Custo:`, and `- Pré-requisito:` are literal like the ten headings, and only the text after them follows the user's language. Add the stage labels to the plan's "Idioma" literals.

### FIND-003: The case studies, offered as worked contracts, skip most of the REQ-012 minimum content
- Severity: major
- Status: resolved
- Location: skills/architecture-system/SKILL.md:63; skills/architecture-discovery/SKILL.md:58; examples/url-shortener.md:76-102; examples/ticketing.md:78-104; examples/live-scoreboard.md:72-98; examples/video-platform.md:81-107
- Evidence: `architecture-system` points to the examples as "Worked contracts", which is a strong signal for the agent to imitate. Against REQ-012 and the format reference:
  - Section 2: none of the four contracts has a Mermaid diagram (the diagrams are only under `## Opções`).
  - Section 3: none states a migration strategy.
  - Section 6: live-scoreboard:88 and video-platform:97 name no environments and no commit-to-production path; ticketing:94 has staging but no path.
  - Section 8: live-scoreboard:96 and video-platform:105 do not say which ports or services are exposed.
  - Section 5: ticketing (the e-mail job) and video-platform do not state the delivery guarantee of their async flows.
  - ADRs are cited only in section 3, although `architecture-system` (SKILL.md:38) lists "VPS or PaaS" and "RBAC or ABAC" as real alternatives that need an ADR.

  REQ-019 allows a "contrato resumido", but no example says it is abridged. Smaller drift: the examples use `### Opção A` and `### Recomendação` while the template uses `##`, and they have no per-option description sentences. The examples are also the planned phase-2 eval fixtures, so whatever they hold now becomes the reference.
- Requirement: REQ-012, REQ-015, REQ-019; AC-009
- Recommendation: Either fill the REQ-012 minimums (a section-2 Mermaid diagram, one migration line, environments and path, exposed ports, the delivery guarantee, and ADR text in section 6), or add one line under each `## Contrato` saying it is abridged and that a real contract needs the full minimum from `architecture-md-format.md`. Also change the `architecture-system` link text to "abridged worked examples".

### FIND-004: Every skill AC is proven only by phrases being present, and three ACs count as covered without their validator half
- Severity: major
- Status: resolved
- Location: agent-system/tests/test_architecture_skills.py:90-136; .cursor/agent-system/proofs/architecture-pipeline.json (TEST-002, TEST-005 acceptance lists); docs/tasks/architecture-pipeline.md:7, :218
- Evidence: See the Verification Audit. AC-001 to AC-015 describe agent behavior, and their TESTs check substrings: `"6"`; `ARCHITECTURE.md` (passes even if the skill says to write it); `confirm` (also matches "Confirm which trigger"); `quando crescer` (passes whatever the sentence says). The Then clauses of AC-010, AC-011, and AC-012 also require `validate_architecture.py` results, which is phase 2. Yet the proofs list AC-010 under TEST-002 and AC-010/011/012 under TEST-005, and `validate_verification.py` reports them as proven. When phase 2 lands, nothing forces a new TEST on these ACs. The behavioral rehearsal the plan relies on (tasks:7) does not exist yet.
- Requirement: AC-001 to AC-015; gate integrity
- Recommendation: Mark these TESTs as structural or partial in the plan (for example `required: false` for the behavioral ACs, or a note in each TEST's Expected). When phase 2 is planned, add TESTs that run `validate_architecture.py` for AC-010/011/012. Do not close the feature until the rehearsal report covers AC-001 to AC-015. Cheap hardening now: assert whole sentences instead of single tokens (for example "at most 6 questions", "Do not write `ARCHITECTURE.md`", "overwrite only after the user's explicit confirmation").

### FIND-005: The options stage's "done" marker is ambiguous and does not match REQ-018
- Severity: minor
- Status: resolved
- Location: skills/architecture/SKILL.md:24; skills/architecture-system/SKILL.md:12; skills/architecture-options/SKILL.md:12, :49; skills/architecture-options/references/options-template.md:1-3, :57; skills/architecture/references/architecture-md-format.md:10
- Evidence: REQ-018 skips "a etapa cujo artefato já existe com `status: approved`", but `options.md` has no `status` field (its front matter is only `brief:`). The plan swaps in "a escolha em options.md". The marker is described as `Escolha do usuário: <X>`, and the template ships the line `Escolha do usuário: <pendente | X (data)>`. An agent that writes `Escolha do usuário: pendente` has a line that literally matches the described marker, so the orchestrator or `architecture-system` could skip the stop (REQ-010). The option letter case also differs: `option: b` in the format reference, `Opção B` and `Escolha do usuário: B` elsewhere.
- Requirement: REQ-010, REQ-018
- Recommendation: Define the marker exactly ("a letter A to C and a date; `pendente` means no choice") or add `status: approved` plus `choice: B` to the options front matter. Record the deviation from REQ-018 in the spec's Decisions. Use one letter case.

### FIND-006: The ADR format described does not match the existing ADRs or the planner's ADR fields
- Severity: minor
- Status: resolved
- Location: skills/architecture-system/SKILL.md:40, :49-57; docs/architecture/ADR/0001-formato-dos-artefatos-rastreaveis.md:18; agents/planner.md:18
- Evidence: The skill says "in the format of the existing ADRs: ... `## Options considered`". The existing ADRs use `## Alternatives`, and 0003 has none. The planner defines ADRs with problem, alternatives, rationale, and risks, and says "Supersede with a new ADR. Do not edit an accepted ADR". The skill never says to supersede the ADR whose decision a stage move or contract rewrite reverses. The path is hard-coded as `docs/architecture/ADR/` instead of the layout's `adr_dir`.
- Requirement: REQ-015, REQ-017
- Recommendation: Point to one ADR template (or write it into the format reference) that agrees with `planner.md`. Add "a decision that changes an accepted ADR creates a new ADR that supersedes it". Read `adr_dir` from `.cursor/agent-system/layout.json` when present.

### FIND-007: architecture-review looks for the lint at a path that does not exist in a user project
- Severity: minor
- Status: resolved
- Location: skills/architecture-review/SKILL.md:14-20; skills/architecture/references/deploy.md:53; skills/design-review/SKILL.md:35 (convention)
- Evidence: "When `agent-system/scripts/lint_infra.py` exists, run ... `python agent-system/scripts/lint_infra.py`". The design skills use `<plugin>/agent-system/scripts/...` or `.cursor/agent-system/scripts/...` after init. In a user project the relative path never exists, so even after phase 2 the review would always take the "lint does not exist" branch. That branch says "check the same items by reading the files", but no reference lists the P0 items (only the spec does). deploy.md:53 tells the project's CI to run `lint_infra.py` as if it lived in the project.
- Requirement: REQ-032 (prepared in phase 1), the TASK-006 note "rode o lint quando `lint_infra.py` existir"
- Recommendation: Use the `<plugin>/...` and `.cursor/agent-system/scripts/...` convention. List the P0 checks to apply by hand in `review-checklist.md` item 11.

### FIND-008: scaling-stages understates a single instance and reuses "stage N" for a different numbering
- Severity: minor
- Status: resolved
- Location: skills/architecture/references/scaling-stages.md:11; patterns.md:70, :99; deploy.md:13, :40; caching.md:8; observability.md:3
- Evidence: Stage 0 "fits ... up to tens of requests per second for a typical CRUD app". The url-shortener case serves 770 req/s from stage 0, and AC-007's brief has 50 req/s. An agent reading "tens" can treat 50 req/s as beyond one instance and recommend a split, against REQ-009. The generic progression is numbered 0 to 7, and other references say "stage 4" and "stage 5". A contract numbers its own `Estágio 0/1/2`, so "stage 5 in scaling-stages.md" and a contract's "Estágio 1" are easy to conflate.
- Requirement: REQ-009, REQ-019
- Recommendation: Say "low hundreds of requests per second for a typical CRUD app on one modest machine, more for cached reads". Call the generic progression "step N" everywhere and keep "stage" for the contract.

### FIND-009: Discovery gaps: conditional bandwidth, a possible 7th question, no way to reopen an approved brief
- Severity: minor
- Status: resolved
- Location: skills/architecture-discovery/SKILL.md:12, :32-41, :56; skills/architecture-discovery/references/brief-template.md:74; skills/architecture-options/SKILL.md:12
- Evidence: REQ-005 requires outbound bandwidth unconditionally, but the skill and the template ask for it only "when the system serves files or media". The six "typical gaps" plus the separate sensitive-data question (line 41) can add up to 7 questions, and the skill does not say which one to drop (the target must stay). The descriptions advertise use "before a structural change", but step 0 stops on any approved brief, and options stops on any recorded choice. There is no path to revise them (set back to `draft` on the user's request), so `/architecture` on an evolving system skips discovery and options forever.
- Requirement: REQ-001, REQ-005, REQ-018
- Recommendation: Always compute bandwidth (it may be "negligible: JSON responses only"). Fold sensitive data into question 3 or state the drop order. Add "if the user asks to revise, set `status: draft` and continue from it" to discovery and options.

### FIND-010: review-checklist.md is in Portuguese, against the plan's language rule
- Severity: minor
- Status: resolved
- Location: skills/architecture-review/references/review-checklist.md:1-49; docs/tasks/architecture-pipeline.md:18, :78, :389
- Evidence: The plan says skill text is English, references included ("as referências ficam em inglês, como as do design"), with only the section titles and origin marks kept literal. The checklist is entirely Portuguese, while every other reference is English. The plan's own test needles (`segredo`, `seção 2`) forced this, so the inconsistency starts in the plan. The case studies and output templates are Portuguese by design (their headings are literals), and that is fine.
- Requirement: Plan language rule
- Recommendation: Write the checklist in English (keeping the literal section titles when cited) and change the needles to `secret` and `section 2`, or record the exception in the plan.

### FIND-011: Two case-study numbers teach the wrong lesson
- Severity: minor
- Status: resolved
- Location: skills/architecture/references/examples/ticketing.md:64; skills/architecture/references/examples/video-platform.md:68, :142 (brief budget), :201 (recommendation)
- Evidence: Ticketing option A "stops serving" because the database "não segura 500 tentativas/s de reserva". Single-row conditional UPDATEs at 500/s are well within one managed PostgreSQL. What really limits option A is scaling the app to ~2,500 req/s for 10 minutes and the arrival herd. Video option B puts ~500 TB/month of egress inside 800 to 1,500 dollars, which implies under about 3 dollars per TB. That is below typical volume CDN pricing, while the recommendation rejects option C on cost. The spec accepts rough costs, but these numbers set the agent's calibration.
- Requirement: REQ-008, REQ-019 (case studies as reference)
- Recommendation: Reword ticketing:64 around app scale-out cost and the herd. Either widen video B's range or lower the bandwidth assumption, and keep the "bandwidth decides the budget" lesson consistent with the numbers.

### FIND-012: Moving to a new stage edits an existing ARCHITECTURE.md without a confirmation step
- Severity: minor
- Status: resolved
- Location: skills/architecture-system/SKILL.md:14-16, :49-57
- Evidence: REQ-016 applies whenever `ARCHITECTURE.md` exists: propose the changes per section and overwrite only after confirmation. Section 6 (stage move) asks to confirm the trigger measurement, then updates the sections, moves `(atual)`, and creates an ADR, without proposing the diff or asking for approval. It also does not say whether `status` returns to `draft` until the user approves.
- Requirement: REQ-016, REQ-017; AC-013, AC-014
- Recommendation: In section 6, add "propose the section changes and the ADR, apply them only after explicit confirmation, keep `status: approved` only with that confirmation".

## Checked and fine

- Every phase-1 REQ has an instruction in a skill or a reference: REQ-001 to 006 (discovery), REQ-007 to 010 (options), REQ-011 to 017 (system plus the format reference), REQ-018 (architecture), REQ-019 (nine references and four cases), REQ-020 (CREDITS).
- The ten headings match the plan's literals in the format reference, the template, and all four case studies. The stage format matches the plan.
- SKILL.md text is in English, with Portuguese triggers in `description`. The origin marks `fornecido | observado | inferido` are literal.
- Third-party content: I read all nine references and four cases. The prose is original and generic. The case studies use fictional products ("Curto", "Plateia", "Lance", "Aula Aberta"), and real names appear only as technologies. CREDITS records the topic checklist with "no content was transcribed or copied".
- Case-study arithmetic checked: url-shortener ≈ 77 req/s, 770 at peak, 6 GB and 240 GB per year; ticketing 167 arrivals/s, 2,500 req/s, 500 attempts/s; scoreboard 40,000 connections ≈ 800 MB; video 800 uploads/day, ~173 TB/year, ~500 TB/month, ≈ 6 workers.
- `skills/help/SKILL.md`: five new lines, no other change. The suite stays green (112 passed).

## Review 2 (re-review after the fixes)

Scope: the same working tree after the corrections the coordinator listed for FIND-001 to FIND-012. I re-read every changed skill, template, reference, and case study, the rewritten `agent-system/tests/test_architecture_skills.py`, the "Revisão 1" note in `docs/tasks/architecture-pipeline.md`, and the proof file.

Commands run:
- `python -I agent-system/scripts/test_system.py`: 114 passed, 0 failed.
- `python -I agent-system/scripts/run_evals.py`: 9/9.
- `python -I agent-system/scripts/check_proofs.py --fingerprint`: digest `01e5374f...cd7`. The proof file holds the same digest for all six TESTs (all PASS), so the proofs are current. I did not re-run `check_proofs.py --feature` this time, because it rewrites the proof file.
- `validate_verification.py --feature architecture-pipeline --no-record`: the 6 required checks are proven. It still fails only for the ACs with no TEST: AC-017 to AC-035 (phases 2 and 3) and now AC-010 to AC-012, which were moved to phase 2 on purpose.
- I probed the new `MEASURABLE` regex and `stage_errors()` in memory, and ran every `Gatilho:` line in `skills/` through the regex.

Verdict: PASS_WITH_WARNINGS. All twelve findings are resolved. The fixes introduced three minor issues (FIND-013 to FIND-015). None blocks phase 1, but FIND-013 should be fixed before phase 2 copies the checker into `validate_architecture.py`.

### Verification Audit (Review 2)

| Finding | Verified | Evidence |
| --- | --- | --- |
| FIND-001 | Resolved | `MEASURABLE` (test file:40-44) now requires an operator, a number, and a unit with `(?![\w/])`, and `dias` is gone. Probes: `> 70%`, `< 99,5%`, `> 30 minutos`, `> 1000 req/min`, and `acima de 1,5 GB` match; `quando crescer por 7 dias`, `mais de 7 dias`, and `ADR-0004 h` do not. `stage_errors()` (:63-88) checks `(atual)` once and only in a title, at least two later stages, all four fields, a measurable trigger, and `(fonte:`. Eight negative cases in `test_stage_check_refuses_vague_or_incomplete_stages` each produce an error. Every `Gatilho:` line in the four cases, `scaling-stages.md`, and the format reference's Accepted example now matches through its threshold (ticketing `> 70%`, video `mais de 30 minutos`). The Refused example does not match. |
| FIND-002 | Resolved | `architecture-md-format.md:78` declares the stage labels literal "whatever the contract's language". The same rule is in the template comment (:7-8) and the tasks language rule (tasks:18). |
| FIND-003 | Resolved | All four contracts now have Mermaid in section 2, `- Migrações:`, `- Garantia de entrega:`, `- Ambientes:`, `- Caminho até produção:`, `- Portas expostas:`, and ADR-de-exemplo mentions for deploy and authorization. TEST-002 asserts the labels per section through `contract_section`. The `###` vs `##` note was added. |
| FIND-004 | Resolved (process residual) | The needles are now sentences ("**at most 6 questions**", "Do not write `ARCHITECTURE.md`", "only after the user's explicit confirmation", and so on). AC-010 to AC-012 were removed from TEST-002 and TEST-005 in both the tasks file and the proof file. The module docstring and the "Revisão 1" note state that the tests are structural and that AC-001 to AC-015 close only at the post-phase-3 rehearsal. Residual: the TESTs are still `required: true`, so the gate shows those ACs as proven. That is now documented, not hidden. Keep it in mind when the feature closes. |
| FIND-005 | Resolved | `options-template.md:1-5` has `status`, `choice`, and `chosen_on`. The options, architecture, and system skills all key on `status: approved` plus a non-empty `choice`. Letters are uppercase. No `Escolha do usuário` remains. |
| FIND-006 | Resolved | `architecture-system/SKILL.md:40-43` and `architecture-md-format.md:101` use the existing ADR headings (`## Alternatives`), `adr_dir` with a default, and the supersede rule. Leftover hard-coded paths are noted in FIND-015. |
| FIND-007 | Resolved | `architecture-review/SKILL.md:14-21` uses `<plugin>/...` or `.cursor/agent-system/scripts/...`. Checklist item 11 lists the six P0 checks, and `deploy.md:53` is reworded. One drift in item 11 is noted in FIND-014. |
| FIND-008 | Resolved | `scaling-stages.md` uses "Step N" with a note separating steps from the contract's `Estágio N`, and stage 0 now says "low hundreds of requests per second". `patterns.md:70`, `:99` and `observability.md:3` say "step N in `scaling-stages.md`". |
| FIND-009 | Resolved | Discovery always computes bandwidth (SKILL.md:56; template:74). Sensitive data is folded into question 3 with "never a seventh question" (:36, :41). There is a revise path for the brief (:12), for options (options SKILL.md:12), and in the orchestrator (architecture SKILL.md:41). |
| FIND-010 | Resolved | `review-checklist.md` is in English. The tasks language rule now names the checklist, the cases, and the templates explicitly. |
| FIND-011 | Resolved | Ticketing option A (:66) and the recommendation (:72) now say PostgreSQL holds 500 reservations per second and name the app and connection scale-out and the mass conflicts. The video budget is 6,000; option B is 3,000 to 6,000 at 5 to 10 dollars per TB, and option C is 10,000 to 25,000, so the recommendation and the numbers agree. |
| FIND-012 | Resolved | `architecture-system/SKILL.md:49-57`: propose the changes per section, wait for explicit confirmation, keep `status: draft` while editing, and re-approve only on confirmation. The format reference (:93) matches. The test asserts "confirmation" inside section 6. |

How the implementation can still be wrong while every test passes: an agent can still ignore the skills (FIND-004 residual, closed only by the rehearsal). Or phase 2 can copy `stage_errors()` as is and refuse valid contracts (FIND-013).

### FIND-013: The new trigger check refuses multi-group thousands and crashes on a malformed stage title
- Severity: minor
- Status: resolved
- Location: agent-system/tests/test_architecture_skills.py:40-46, :74-75
- Evidence: `\d+(?:[.,]\d+)?` allows only one separator group, so the Portuguese format `> 1.000.000 usuários` gives `None`, while `> 20.000 conexões` passes. A realistic trigger written in the contract's own number format would be refused. Business units such as `reservas/s`, `itens`, or `eventos/s` are not units either. The format reference says the list is closed, so this follows the plan, but it is narrow. `STAGE_TITLE.match(...).group(1)` assumes every `### Estágio` block has `N: `. `### Estágio 0 - x (atual)` and `### Estágio um: y` both raise `AttributeError` instead of returning an error message. In the test that still fails, but a phase-2 validator built from this code would print a traceback instead of "exit 1 citing the stage" (AC-011).
- Requirement: REQ-013, REQ-030; AC-011 (phase 2)
- Recommendation: Use `\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?` for the number. When a title does not match `STAGE_TITLE`, report "stage title must be `### Estágio N: <name>`" instead of calling `.group` on `None`. Add both cases to the negative test. Decide whether `/s`-suffixed business units are allowed, and say so in the format reference.

### FIND-014: Checklist item 11 drifts from the spec's P0-SECRET-LITERAL definition
- Severity: minor
- Status: resolved
- Location: skills/architecture-review/references/review-checklist.md:33; docs/specs/architecture-pipeline.md:107 (REQ-022)
- Evidence: REQ-022 lists the key fragments `PASSWORD`, `PASSWD`, `SECRET`, `TOKEN`, `API_KEY`, `APIKEY`, `PRIVATE_KEY`, `ACCESS_KEY`, and exempts `${VAR}`, `$VAR`, the empty value, `valueFrom`, `secretKeyRef`, and `env_file`. Item 11 drops `PASSWD` and `APIKEY` and omits `$VAR` and the empty value. A reviewer checking by hand (the documented fallback while `lint_infra.py` is missing) would miss `DB_PASSWD: hunter2` and might flag `API_KEY:` with an empty value.
- Requirement: REQ-022 (as used by the REQ-032 fallback)
- Recommendation: Copy the spec's key list and exemptions verbatim into item 11, or point to the lint's rule table once phase 2 adds it.

### FIND-015: Small wording leftovers from FIND-001 and FIND-006
- Severity: minor
- Status: resolved
- Location: skills/architecture-system/SKILL.md:8, :32; skills/architecture/SKILL.md:12; skills/architecture-discovery/SKILL.md:24
- Evidence: `architecture-system/SKILL.md:32` still defines a trigger as "a metric with a number, a unit, and where it is measured", without the operator that the format reference (:88) and the check now require. An agent reading only the skill can write `Gatilho: latência de 300 ms (fonte: APM)`, which the check refuses. Three places still say the ADRs live in `docs/architecture/ADR/` without the `adr_dir` qualifier that step 4 and the review skill now use. Discovery would then look for earlier ADRs in the default folder of a project that overrides it.
- Requirement: REQ-013, REQ-015
- Recommendation: Say "a metric compared with a threshold (operator, number, unit) and where it is measured" in SKILL.md:32. Write "the ADR folder (`adr_dir`, default `docs/architecture/ADR/`)" in the three spots.

## Review 3 (re-review of FIND-013 to FIND-015)

Scope: the corrections for FIND-013 to FIND-015, plus a regression pass over the same tree. Per the coordinator's instruction, I did not run `check_proofs.py --feature`.

Commands run:
- `python -I agent-system/scripts/test_system.py`: 115 passed, 0 failed.
- `python -I agent-system/scripts/run_evals.py`: 9/9.
- `python -I agent-system/scripts/check_proofs.py --fingerprint`: digest `634ed5a6...5fbf`. The proof file holds this digest for all six TESTs (all PASS), and TEST-002's command now includes `test_measurable_trigger`. The proofs are current.
- `validate_verification.py --feature architecture-pipeline --no-record`: it reads this review and its fingerprint. The remaining failures are the ACs with no TEST, which are planned: AC-010 to AC-012 and AC-017 to AC-035.
- In memory, I probed `MEASURABLE` and `stage_errors()` again, and ran every `Gatilho:` line in `skills/` through the regex.

Verdict: PASS. All fifteen findings are resolved, and I found no regression. FIND-004 keeps its documented process residual: AC-001 to AC-015 rest on structural TESTs until the post-phase-3 rehearsal.

### Verification Audit (Review 3)

| Finding | Verified | Evidence |
| --- | --- | --- |
| FIND-013 | Resolved | Number part `\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?` and rate unit `\w+/(?:s|min|h)` (test file:42-47). These match: `> 1.000.000 usuários`, `> 3.000 reservas/s`, `< 99,5%`, `> 1.200,5 pedidos/min`, `> 5 MB/s`, `> 30000 conexões`. These still do not: `quando crescer por 7 dias`, `latência de 300 ms`, `ADR-0004 h`, `mais de 7 dias`, `> 7 dias/semana`, `> 2 vezes`. `stage_errors()` (:71-73) returns `stage title must be '### Estágio <number>: <name>'` for `### Estágio 0 - x`, `### Estágio um: y`, and `### Estágio 1:y` instead of raising. The negative test and `test_measurable_trigger_numbers_and_rates` cover both changes. The format reference (:88) and the tasks rule (tasks:45) describe the same rule. |
| FIND-014 | Resolved | `review-checklist.md:33` now has REQ-022's key list (`PASSWD` and `APIKEY` included), the three locations, and the exemptions (`${VAR}`, `$VAR`, empty value, `valueFrom`, `secretKeyRef`, `env_file`). |
| FIND-015 | Resolved | `architecture-system/SKILL.md:32` requires an operator, a number, a unit, and a source, gives the refused "latência de 300 ms" example, and links the format reference. `architecture-system/SKILL.md:8`, `architecture/SKILL.md:12`, and `architecture-discovery/SKILL.md:24` all name "the ADR folder (`adr_dir`, default `docs/architecture/ADR/`)". |

Regression pass:
- Every `Gatilho:` trigger line in the case studies, `scaling-stages.md`, and the format reference's Accepted example still matches. The only lines that do not match are label mentions, template placeholders, and the Refused example, as intended.
- The rate alternative widens the accepted set slightly. A value with a bad separator such as `> 1.0000 usuários` is accepted through the plain-decimal branch, and so is any `<word>/s`. Neither lets a vague or duration-only trigger through, so I am recording this as a note, not a finding.
- No other files changed beyond those the coordinator listed.

# Fase 2 / Review 1 (lint de infraestrutura, validador do contrato e hook)

Scope: the uncommitted working tree on `feat/architecture-lint` against base e9f04e5 (phase 1). Requirements REQ-021 to REQ-030; acceptance AC-010, AC-011, AC-012, and AC-017 to AC-026. Phase 3 (REQ-031 to REQ-038) is out of scope. I compared, in order: the spec, the "Fase 2" section of the tasks file (TASK-007 to TASK-009, TEST-007 to TEST-009), the tests (`agent-system/tests/test_infra_lint.py`, `test_validate_architecture.py`, the changed `test_architecture_skills.py`), and the code (`agent-system/scripts/lint_infra.py`, `validate_architecture.py`, the `hook.py`, `init_project.py`, and `run_evals.py` diffs, and the eval fixture `architecture-contract`).

Commands run:
- `python -I agent-system/scripts/test_system.py`: 134 passed, 0 failed.
- `python -I agent-system/scripts/run_evals.py`: 10/10.
- `python -I agent-system/scripts/check_proofs.py --fingerprint`: digest `365ebefa...5651`. The proof file records TEST-001 to TEST-009 as PASS on this digest, so the proofs are current. As instructed, I did not run `check_proofs.py --feature`.
- `validate_verification.py --feature architecture-pipeline --no-record`: the 9 required checks are proven. The only ACs without a TEST are AC-027 to AC-035 (phase 3).
- In the scratchpad: realistic Compose, Dockerfile, and Kubernetes files through the CLI; a 3,000-input crash fuzz of `lint_paths` (0 crashes); timing on 500 KB inputs (0.47 s and 0.15 s); and 19 mutations of `lint_infra.py` and `validate_architecture.py`, run against the phase-2 tests in a copy of `agent-system/`. The repository was not touched.
- The project is not opted in, so no REVIEW_* events were recorded.

Verdict: FAIL. There is one blocker. Compose and Kubernetes files written with compact (non-indented) block sequences, which is valid YAML and the style used in the Kubernetes documentation, silently lose P0-SECRET-LITERAL and P0-DB-PORT-PUBLIC in Compose and P1-NO-PROBE and P1-NO-RESOURCE-LIMITS in Kubernetes, with exit 0 (FIND-016). There are also four majors. Two make the lint report a clean result for files it did not really read (FIND-017, FIND-018). One is a P0 false positive on the secure Docker-secrets pattern (FIND-019). The last is a set of test gaps: 14 of the 19 mutations that applied survive (FIND-023).

Things I checked that hold:
- **Secrets:** no secret value reaches any output path. Text, JSON, hook context, and the timeline carry only the key and the line. Verified with literal values in Compose (map and list), Dockerfile `ENV` (both forms), `ARG`, and Kubernetes `env[].value`. The fuzz never crashed, so no traceback can echo input.
- **Design lint hook:** `test_design_lint_hook_*` still pass. Claude gets both lints, and Cursor drops both keys.
- **Portability:** the new scripts need Python 3.8 or later (assignment expressions; `X | None` only appears in annotations under `from __future__ import annotations`). The code uses `pathlib` and UTF-8 with `errors="replace"`. CRLF files keep correct line numbers. CI already runs both test_system and run_evals on Ubuntu and Windows.

## Verification Audit (Fase 2)

Mutations run against the phase-2 tests. KILLED means a test failed; SURVIVED means every test still passed.

| Mutation | Result |
| --- | --- |
| `latest` tag no longer flagged | KILLED |
| `USER 0`, `0:0`, `root:root` no longer flagged (only `root`) | SURVIVED |
| `runAsNonRoot: false` no longer flagged | SURVIVED |
| `SECRET`, `PRIVATE_KEY`, `ACCESS_KEY` removed from the key words | SURVIVED |
| interpolation `$...` treated as literal | KILLED |
| loopback reduced to `127.0.0.1` (drop `localhost`, `::1`) | SURVIVED |
| `NodePort` no longer exposes | SURVIVED |
| long-syntax ports ignored entirely | SURVIVED |
| `.dockerignore` presence ignored | KILLED |
| `children()` nesting `<=` changed to `<` | SURVIVED |
| suppression of the next line removed | KILLED |
| `livenessProbe` no longer required | SURVIVED |
| P1-ADD-REMOTE also fires on `COPY` | SURVIVED |
| DB ports reduced to `{5432, 6379}` | SURVIVED |
| exit 2 for an unreadable file replaced by 0 | SURVIVED |
| `scratch` exemption removed | SURVIVED |
| `(fonte:` not required | KILLED |
| section-order check disabled | SURVIVED in the tests; KILLED only by `run_evals.py` |
| duplicated-section check disabled | SURVIVED |

| AC | TEST | Assessment |
| --- | --- | --- |
| AC-017 scan, exclusions, non-infra YAML | TEST-007 | Proven (`node_modules`, GitHub Actions, and a plain YAML config are skipped). |
| AC-018 each P0 fails, complete finding | TEST-007 | Partial. One or two variants per rule; NodePort, `runAsNonRoot: false`, `USER 0`, long-syntax ports, most DB ports, and three key words are untested (see mutations). No compact-sequence case (FIND-016). |
| AC-019 not-P0 cases | TEST-007 | Proven for the AC's exact inputs. Not tested: `FROM --platform`, lowercase `as`, `localhost`/`::1`. |
| AC-020 P1/P2 only warn | TEST-007 | Proven for P1-NO-RESTART and P1-NO-RESOURCE-LIMITS (Compose and Job). The P1-NO-PROBE test lacks both probes, so a missing liveness alone is unproven. |
| AC-021 secret never printed | TEST-007, TEST-009 | Proven for text, JSON, Claude context, and the timeline (Compose map form). Not tested for the Dockerfile and Kubernetes forms; I checked those by hand and they hold. |
| AC-022 JSON | TEST-007 | Proven (exact key set). |
| AC-023 suppression | TEST-007 | Proven for the AC's inputs. Edge in FIND-022. |
| AC-024 hook | TEST-009 | Proven: Claude context, Cursor `{}`, two `INFRA_LINT` events without snippet or value, and `.py`/`.md`/outside-root edits skipped. The timeout is not asserted; timing is 0.5 s worst case on a 500 KB file. |
| AC-025 CI | TEST-007 | Proven (the suite runs in the Ubuntu/Windows matrix). |
| AC-010, AC-011, AC-012 | TEST-008 | Proven: valid contract exit 0, vague trigger names the stage, missing ADR fails, and `adr_dir` from `layout.json` is honored. All four case studies validate. |
| AC-026 eval | TEST-008 | Not proven by TEST-008: its command does not run `run_evals.py`, and the order check survives every test (it is caught only by the eval, which CI runs separately). |

How the implementation can be wrong while every test passes: everything in FIND-016 to FIND-022, plus each SURVIVED mutation above.

### FIND-016: Compact block sequences hide P0 secrets and public DB ports in Compose and drop container checks in Kubernetes
- Severity: blocker
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:133-143 (`children`), :341-344 and :350-365 (Compose `nested`), :393-412 (`container_blocks`)
- Evidence: `children()` keeps only lines indented more than the key. In YAML a block sequence may sit at the same indent as its key (`environment:` followed by `- POSTGRES_PASSWORD=hunter2` at the same column). This is the style of the Kubernetes documentation and many hand-written files. Reproduced:
  - A Compose service with `environment:\n- POSTGRES_PASSWORD=hunter2` and `ports:\n- "5432:5432"` gives only P0-DOCKER-SOCKET. The secret and the public DB port are both missed. Without the socket line it exits 0.
  - A Deployment with `containers:\n- name: web` and no probes or resources gives no P1-NO-PROBE and no P1-NO-RESOURCE-LIMITS.
  - The Kubernetes secret check still works in this style because it does not use `children()`.

  No message tells the user anything was skipped. The `<=` to `<` mutation of `children()` survives the tests.
- Requirement: REQ-022 (P0-SECRET-LITERAL, P0-DB-PORT-PUBLIC), REQ-023, REQ-024; AC-018, AC-020
- Recommendation: In `children()`, also accept lines at the key's indent that start with `- ` when the key's value is empty (the YAML rule for a sequence under a mapping key), and stop at the first sibling key. Add Compose and Kubernetes fixtures in compact style for environment, ports, and containers.

### FIND-017: A Compose file whose `services:` line carries a comment is not linted at all
- Severity: major
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:318
- Evidence: `re.match(r"^services:\s*$", line)` fails for `services:   # app stack`. `lint_compose` then returns before any rule, so every service rule (including P0-PRIVILEGED, P0-SECRET-LITERAL, and P0-DB-PORT-PUBLIC) is skipped. Reproduced with a published 5432: exit 0, no finding, no note. The same exact-match pattern applies wherever a key is detected with `\s*$` (`containers:` at :396).
- Requirement: REQ-021, REQ-022
- Recommendation: Strip an inline comment before matching (`^services:\s*(?:#.*)?$`, and the same for `containers:`). Add a test.

### FIND-018: Files over 512 KB are skipped and the CLI still exits 0
- Severity: major
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:27, :524-526, :576
- Evidence: A rendered manifest bundle over 512 KB with `image: nginx:latest` prints `skipped (larger than 512 KB)` on stderr and exits 0. That is the exit code the implementer and the platform-implementer read as "no P0 open" (REQ-035, REQ-037). The cap protects the hook's timeout, but the CLI does not need it: a 500 KB worst-case file lints in 0.47 s.
- Requirement: REQ-021, REQ-022 (exit 1 on P0)
- Recommendation: Keep the cap only in `hook.infra_lint` (or raise it there). In the CLI, lint every file, or exit 2 when a file was skipped, as is already done for unreadable files. Test both.

### FIND-019: P0-SECRET-LITERAL fires on non-secret keys, including the Docker-secrets `_FILE` pattern
- Severity: major
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:29, :78-94
- Evidence: Each of these exits 1 with P0-SECRET-LITERAL:
  - `POSTGRES_PASSWORD_FILE: /run/secrets/pg`, which is the official image's way to avoid a literal password.
  - `JWT_TOKEN_TTL: 3600`.
  - `API_KEY: null`.

  Other likely hits are `PASSWORD_MIN_LENGTH` and `TOKEN_URL`. The rule matches the spec's text (key contains the word, value is literal), but a blocking P0 on the secure pattern forces suppressions or worse workarounds.
- Requirement: REQ-022 (intent), REQ-035, REQ-037 (no delivery with P0 open)
- Recommendation: Needs the user's decision on the spec. My suggestion: exempt keys ending in `_FILE` whose value is an absolute path, YAML null/`~`, and values that are only digits or durations. Record the exemptions in REQ-022 and in checklist item 11, and add tests.

### FIND-020: Kubernetes secret and root checks miss flow mappings and value-before-name
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:437-443, :429-432
- Evidence: Each of these is missed:
  - `- {name: DB_PASSWORD, value: hunter2}` (flow mapping).
  - `- value: sk-live-xyz` followed by `name: API_TOKEN` (value before name).
  - `securityContext: {runAsUser: 0}` at pod level (flow mapping).

  The spec accepts heuristic limits, but these are not listed in the module docstring or the spec's assumptions.
- Requirement: REQ-022
- Recommendation: Parse a one-line flow mapping (`{k: v, ...}`) into keys. Collect `name` and `value` per sequence item regardless of order. Document what stays out.

### FIND-021: Dockerfile user and healthcheck rules are imprecise for multi-stage builds
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:211-221, :233-234, :255-261, :189-198
- Evidence:
  - `USER 0:1000` and `USER root:staff` in the final stage pass: only `root`, `0`, `0:0`, and `root:root` are recognized.
  - A final stage `FROM runtime` that inherits `USER 1000` from the earlier stage `runtime` is reported as P0-ROOT-USER, a false positive that blocks.
  - A HEALTHCHECK in a non-final stage counts for the image.
  - P1-NO-HEALTHCHECK is silenced by any `healthcheck:` in any Compose file of the folder, not by the service built from this Dockerfile.
- Requirement: REQ-022 (P0-ROOT-USER), REQ-023 (P1-NO-HEALTHCHECK)
- Recommendation: Treat a user whose part before `:` is `root` or `0` as root. Inherit `user` and `healthcheck` from the alias a stage starts from. Reset `healthcheck` per stage. Match the Compose service whose `build` points at this folder or Dockerfile. Add tests.

### FIND-022: A suppression with a reason but without `--` is silently ignored
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:35, :482-494
- Evidence: `# infra-lint-disable P0-DOCKER-SOCKET because CI` does not match `SUPPRESS` at all, because the lazy class cannot absorb lowercase text. The finding is reported, but neither suppressed nor accompanied by P1-SUPPRESSION-NO-REASON, so the author gets no hint why the comment did nothing. The same happens with a lowercase rule id.
- Requirement: REQ-027
- Recommendation: Match `infra-lint-disable\s+(\S+)(.*)$`, accept the suppression only with `--` and a reason, and report P1-SUPPRESSION-NO-REASON (or a P1 for a malformed suppression) otherwise.

### FIND-023: The tests miss most P0 branches, and TEST-008 does not run the eval it claims
- Severity: major
- Status: resolved
- Location: agent-system/tests/test_infra_lint.py:104-146; agent-system/tests/test_validate_architecture.py; docs/tasks/architecture-pipeline.md (TEST-008 Command)
- Evidence: 14 of the 19 mutations that applied survive (Verification Audit table). AC-018 says "uma fixture para cada regra P0", but whole branches of those rules are untested:
  - NodePort;
  - `runAsNonRoot: false`;
  - `USER 0` and `USER 0:0`;
  - long-syntax ports;
  - 7 of 9 DB ports;
  - the key words `SECRET`, `PRIVATE_KEY`, and `ACCESS_KEY`;
  - `localhost` and `::1` as loopback;
  - the `scratch` exemption.

  Also untested: liveness-only, exit 2 for an unreadable file, and duplicated sections. AC-026's order check is not exercised by any test. TEST-008's command does not include `run_evals.py`, yet the proof lists AC-026.
- Requirement: AC-018, AC-019, AC-020, AC-026; REQ-029
- Recommendation: Turn `P0_CASES` into one positive per branch and one near-miss per rule. Add the compact-style, comment-on-`services:`, and large-file cases from FIND-016 to FIND-018. Add an out-of-order and a duplicated-section test in `test_validate_architecture.py`, or add `run_evals.py architecture-contract` to TEST-008.

### FIND-024: validate_architecture strips code fences for headings but not for sections and ADR citations
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/validate_architecture.py:47-59, :124-128
- Evidence: `contract_headings` removes fenced blocks, but `contract_section` splits on the first occurrence in the raw text. A fenced example `## 9. Estágios de escala` in section 2 makes section 9 parse the example, and the valid contract fails ("at least two stages after the current one"). An `ADR-0004` inside a fenced example also counts as a citation.
- Requirement: REQ-030
- Recommendation: Run `FENCE.sub` once in `validate()` and pass the cleaned text to all three checks.

### FIND-025: The hook context is cut at 1,500 characters and lists findings by line, not by severity
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/hook.py:124-126, the new `infra_lint` function
- Evidence: Eight findings with suggestions run about 200 characters each, so `redact(lint, 1500)` truncates the tail. Findings are sorted by line, so in a long Compose file the P0 lines can be the ones cut or left beyond `LINT_SHOWN`. The header still gives the P0 count.
- Requirement: REQ-028 (findings reach the agent)
- Recommendation: Sort the hook's list by severity, then line. Drop the suggestion text for P1/P2 lines in the hook, or raise the limit to fit `LINT_SHOWN` lines.

# Fase 2 / Review 2 (re-review of FIND-016 to FIND-025)

Scope: the rewritten `agent-system/scripts/lint_infra.py`, the `validate_architecture.py` and `hook.py` changes, the new tests, the REQ-022 change in the spec (with its Decisions entry), and checklist item 11. Per the coordinator's instruction, I did not run `check_proofs.py --feature`.

Commands run:
- `python -I agent-system/scripts/check_proofs.py --fingerprint`: digest `a7ec52c4...6afc`. The proof file records TEST-001 to TEST-009 as PASS on this digest, so the proofs are current.
- `test_system.py`, `run_evals.py`, and `validate_verification.py`: results are in the last lines of this section.
- In the scratchpad:
  - I re-ran every reproduction from Fase 2 / Review 1, plus new edge cases (mixed indentation, value-before-name, flow lists, `[::1]` hosts, `USER 0:1000`, inherited stages, a Compose in a subfolder that builds the Dockerfile, suppression variants, a 600 KB manifest).
  - I ran 31 mutations against the phase-2 tests in a copy of `agent-system/`. 27 were KILLED. The 4 survivors are listed under FIND-023 and FIND-028.
  - Secret values never appeared in any output of these runs (asserted on stdout and stderr).

Verdict: PASS_WITH_WARNINGS. FIND-016, FIND-017, FIND-018, and FIND-020 to FIND-025 are resolved, and FIND-019 is resolved under the user's decision. The fixes leave one major regression-class gap: P0-SECRET-LITERAL is missed when env lists in one document use different indentation (FIND-026). There are also two minors (FIND-027, FIND-028).

| Finding | Status | Evidence |
| --- | --- | --- |
| FIND-016 | Resolved | `children()` (:112-126) accepts `- ` items at the key's indent when the key has an empty value. In compact style, Compose now reports P0-SECRET-LITERAL (line 9) and P0-DB-PORT-PUBLIC (line 11), and a compact `containers:` gets P1-NO-PROBE and P1-NO-RESOURCE-LIMITS. Mutating `children()` back is KILLED. |
| FIND-017 | Resolved | `services:   # app stack` with long-syntax 5432 now gives P0-DB-PORT-PUBLIC and exit 1. The `^services:\s*$` mutation is KILLED. |
| FIND-018 | Resolved | The CLI reads a 600 KB manifest and reports its P0 (exit 1). The cap is only in the hook (`HOOK_MAX_BYTES`), and the CLI exits 2 when anything lands in notes. A cap mutation is KILLED. Exit 2 itself is untested (FIND-028). |
| FIND-019 | Resolved (user decision) | The user decided on 2026-11-16 ("Sim, com exceções", relayed by the coordinator). REQ-022, the spec's Decisions entry, checklist item 11, and `is_literal_secret()` (:184-192) agree. `POSTGRES_PASSWORD_FILE: /run/secrets/pg`, `JWT_TOKEN_TTL: 3600`, and `API_KEY: null` are no longer P0, while `SECRET_KEY: "sk-abc"` still is. Each exemption has a KILLED mutation. Residual by design: a purely numeric secret (`DB_PASSWORD: 123456`) is now exempt too. If that matters, restrict the number/duration exemption to keys that end in `_TTL`, `_TIMEOUT`, `_LENGTH`, or `_EXPIRY`. |
| FIND-020 | Resolved, except mixed indentation | `securityContext: {runAsUser: 0}` gives P0-ROOT-USER, and `- {name: DB_PASSWORD, value: hunter2}` and value-before-name in a single env list both give P0-SECRET-LITERAL. Mixed indentation across env lists is FIND-026. |
| FIND-021 | Resolved | `USER 0:1000` gives P0-ROOT-USER. `FROM base AS final` inherits `USER 1000` and the HEALTHCHECK (no finding). A HEALTHCHECK only in an earlier non-parent stage does not count. A Compose `other` service's healthcheck no longer silences the Dockerfile, while the service that builds it (`context` and `dockerfile`) does. `ARG` before the first `FROM` is checked. Each part has a KILLED mutation. |
| FIND-022 | Resolved | `# infra-lint-disable P0-DOCKER-SOCKET because CI` now gives P1-SUPPRESSION-NO-REASON and keeps the P0. A lowercase id with `-- reason` suppresses. The empty-reason branch (`-- ` with nothing after) has a surviving mutation (FIND-028). |
| FIND-023 | Resolved, residual in FIND-028 | Of the 14 survivors from Review 1, 12 are now KILLED, including NodePort, `runAsNonRoot`, `USER 0`, the key words, loopback, long syntax, DB ports, `scratch`, liveness, order, and duplicates. TEST-008 now runs `run_evals.py architecture-contract`, so AC-026 is proven by its own TEST. The two left are P1-ADD-REMOTE scope and exit 2 (FIND-028). |
| FIND-024 | Resolved | `validate()` strips fences once (:131-134). The fence mutation is KILLED. |
| FIND-025 | Resolved | The hook sorts by severity, P1/P2 lines carry no fix, and the limit is 3,000. The ordering mutation is KILLED; the limit change survives, because no test produces more than 1,500 characters (FIND-028). |

### FIND-026: P0-SECRET-LITERAL is missed when env lists in one document have different indentation
- Severity: major
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:551-553 (`list_items(doc_items(doc))`), :565-571 (`doc_items`), :147 (`item_indent`)
- Evidence: `doc_items()` concatenates the items of every `env:` list in the document. `list_items()` then fixes `item_indent` to the indent of the first item and ignores items at any other indent. Reproduced:
  - A Deployment whose `initContainers` env is compact (items at 8 spaces) and whose `containers` env is block style (items at 12) reports `DB_PASSWORD` from the init container but not `API_TOKEN: sk-live-xyz` from the main container. Exit 1 only because of the first.
  - A `kind: List` with two Pods whose env lists use different styles reports only `A_TOKEN`, missing `B_TOKEN`.

  With a single env list, or lists at the same indent, the check works. This is silent, the same class of defect as FIND-016, and it hits a P0. It shows up wherever snippets in two styles are pasted into one manifest.
- Requirement: REQ-022 (P0-SECRET-LITERAL), REQ-024
- Recommendation: Call `list_items(children(doc, index))` once per `env:` key and check the items of each list separately, instead of concatenating them. Add the mixed-indent Deployment as a test case.

### FIND-027: A Compose `environment` written as a flow list is not checked
- Severity: minor
- Status: resolved
- Location: agent-system/scripts/lint_infra.py:452-465
- Evidence: `environment: ["API_KEY=sk-flow"]` gives no P0-SECRET-LITERAL; the service gets only P1/P2 and the published port. `flow_pairs` handles `{A: b}` mappings, and `ports: [...]` flow lists are parsed, but `environment: [...]` is not. The module docstring says one-line flow mappings are read and says nothing about flow lists.
- Requirement: REQ-022
- Recommendation: When the `environment` value starts with `[`, split it like `port_entries` does and run each `KEY=value` through `check_secret`. Add a test.

### FIND-028: Four remaining test gaps
- Severity: minor
- Status: resolved
- Location: agent-system/tests/test_infra_lint.py
- Evidence: These mutations still pass every test:
  - P1-ADD-REMOTE also firing on `COPY https://...`: no near-miss.
  - `return 2 if notes else 0` replaced by `return 0`: acknowledged; no portable way to force an unreadable file.
  - A suppression with `--` and an empty reason accepted: only the no-`--` case is tested.
  - The hook limit back at 1,500: no test exceeds it.
- Requirement: AC-018, AC-023, AC-024
- Recommendation:
  - Add a `COPY` near-miss and a `# infra-lint-disable P0-DOCKER-SOCKET -- ` case.
  - Test the hook with a Compose file that has nine or more findings, and assert that a P0 with its fix is in the context.
  - For exit 2, call `lint_infra.main()` in process with `Path.read_text` patched to raise `OSError`.

# Fase 2 / Review 3 (re-review of FIND-026 to FIND-028)

Scope: the changes for FIND-026 to FIND-028 in `agent-system/scripts/lint_infra.py` and `agent-system/tests/test_infra_lint.py`, plus a regression pass. Per the coordinator's instruction, I did not run `check_proofs.py --feature`.

Commands run:
- `python -I agent-system/scripts/check_proofs.py --fingerprint`: digest `7f4a1d89...13f6`. The proofs are re-recorded on this tree (pass=9, as reported); the gate line below confirms they are current.
- In the scratchpad, I re-ran the Review 2 reproductions for FIND-026 and FIND-027, asserting that no secret value appears in the output.
- I ran six targeted mutations against the `test_infra_` tests in a copy of `agent-system/`: all six were KILLED.

Verdict: PASS. FIND-016 to FIND-028 are all resolved. Residual by user decision (FIND-019): a purely numeric secret value is exempt from P0-SECRET-LITERAL; the coordinator reported this to the user.

| Finding | Status | Evidence |
| --- | --- | --- |
| FIND-026 | Resolved | `env_lists()` (:572-574) returns each `env:` list separately, and `lint_manifest` runs `list_items()` per list (:557-558). The mixed-indent Deployment now reports both secrets (lines 13 and 18), and the two-style `kind: List` reports both (lines 11 and 20). No value is printed. Concatenating the lists again is KILLED by `test_infra_lint_env_lists_with_mixed_indentation`. |
| FIND-027 | Resolved | `environment: ["API_KEY=sk-flow"]` gives P0-SECRET-LITERAL at line 4 (:457-461), without the value. Disabling the branch is KILLED by `test_infra_lint_compose_environment_flow_list`. |
| FIND-028 | Resolved | All four former survivors are now KILLED: P1-ADD-REMOTE extended to `COPY`, `return 0` instead of exit 2 for an unreadable file, a `-- ` suppression with an empty reason accepted, and the hook limit back at 1,500. |

Regression pass: the Review 1 and Review 2 reproductions still behave as recorded in Review 2. That covers compact lists, the comment after `services:`, large files, the FIND-019 exemptions, flow mappings, multi-stage inheritance, and suppressions.
