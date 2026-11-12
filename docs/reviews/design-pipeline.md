---
status: FAIL
reviewer: reviewer
fingerprint: 10556e2069024084a33f4818a635bafbc1765c4b68addb4943ee9c3be6bfce40
---
# Review: design pipeline (skills, agents, anti-slop lint)

Scope: uncommitted working tree on `feat/design-pipeline` against HEAD 7b51fb8. Compared, in order: spec `docs/specs/design-pipeline.md`, plan `docs/tasks/design-pipeline.md`, acceptance report `docs/reviews/design-pipeline-acceptance.md`, tests (`agent-system/tests/test_design_lint.py`, `agent-system/tests/test_design_skills.py`), and the implementation (`agent-system/scripts/lint_design.py`, `agent-system/scripts/hook.py`, skills, agents, docs).

Commands run:
- `python -I agent-system/scripts/check_proofs.py --feature design-pipeline`: 16/16 PASS, fingerprint `10556e20...ce40`, same as the handoff (the proofs are current).
- `python -I agent-system/scripts/validate_verification.py --feature design-pipeline --no-record`: proofs current; WARN that AC-002, AC-004, AC-008, AC-009, AC-013, and AC-020 are covered only by optional tests; FAIL only because this review did not exist yet.
- I ran the lint against my own fixtures in the scratchpad (JSX/TSX, Tailwind, CSS-in-JS, SVG, anchors, prose, Portuguese copy), timed it on adversarial and realistic inputs, and ran the hook on binary, missing, directory, outside-workspace, and large minified files.

The project is not opted in (`record_event.py` returned "Project is not initialized"), so no REVIEW_* events were recorded.

Verdict: FAIL. There is one blocker (FIND-001: a DESIGN.md that follows the skill's own section-9 guidance turns P0-INDIGO off) and several majors. The skill and agent ACs are mostly proven by string-presence tests or by the manual report alone. Four ACs have no behavioral evidence at all.

## Verification Audit

Legend: Q1 test matches the criterion; Q2 checks behavior; Q3 mutation that would slip through; Q4 negative cases; Q5 boundaries; Q6 assertion specificity; Q7 result vs implementation detail; Q8 untested condition; Q9 proof current.

Q9 holds for every TEST: `check_proofs.py` re-ran all 16 on fingerprint `10556e20...ce40` and `validate_verification.py` reported no stale proofs.

### Lint ACs (deterministic, real tests)

| AC | TEST | Q1-Q2 | Q3: mutation that passes | Q4-Q5 | Q8: untested |
| --- | --- | --- | --- | --- | --- |
| AC-023 scan and exclusions | TEST-003 | Yes, behavioral (runs the CLI on a tree). | Dropping `.htm`, `.scss`, `.vue`, or `.svelte` from `EXTENSIONS` passes. | All 5 skip dirs covered. | Extension coverage beyond `.tsx`/`.html`. |
| AC-024 each P0 fails | TEST-001, TEST-002 | Yes, exit 1 plus rule id. | Only one variant per rule. Each of these passes: shrinking `AI_INDIGO` to `{"#6366f1"}`; deleting `TW_GRADIENT`, `CLIP_TEXT`, the Tailwind `TW_SIDE` branch, the `icon`-class branch of `ICON_TEXT`, or every Portuguese alternative in `METRIC`; reducing `CDN` to `unsplash`. | No negative P0 cases (near misses that must stay clean) apart from the clean fixture. | Gradient text, Tailwind gradients, `button`/`icon` emoji, PT metrics, 4 of the 5 CDNs. |
| AC-025 P1/P2 only warn | TEST-005 | Yes. | P2 thresholds are untested at the boundary: changing `> 6` to `> 5` or `> 3` to `> 2` passes. | No boundary cases (6 accents and 3 scales should be clean). | CSS-in-JS forms (`transition: "all ..."`). |
| AC-026 declared purple brand | TEST-003 | **Partial.** The AC says the component uses `#7c3aed`; the test uses the class `bg-violet-600`. | Removing `and value not in allowed` from the hex branch of `check_p0` passes. Gradient allowlisting (REQ-030 also covers P0-GRADIENT) is untested. | Negative half (no tokens means P0) is covered. | Hex allowlist, gradient allowlist, the default `design/tokens.css` discovery without `--tokens`. |
| AC-027 JSON | TEST-002 | Yes, exact key set, line, and severity. | None material. | n/a | n/a |
| AC-028 hook does not block | TEST-007 | Partial. Claude context and the `.md` skip are covered. | Removing `.py` handling passes (only `.md` is tested). No test enforces the timeout (see FIND-002). | No large, binary, or unreadable file case. | The "finding reaches the agent" half for Cursor is asserted as `{}`, the opposite of the AC (FIND-003). |
| AC-029 CI | TEST-006 | Yes (full suite). | n/a | n/a | n/a |
| AC-030 suppression | TEST-004 | Yes, exact lines. | A suppression that also covered N+2 would pass; neither suppressing the wrong rule id nor a lowercase id is tested. | Reason and no-reason cases covered. | Block comments `/* */` and JSX `{/* */}` forms. |

### Skill and agent ACs (string-presence contract tests)

`test_design_skills.py` checks that phrases exist in Markdown. It proves the instructions exist, not that an agent following them behaves as required. Any rewrite that keeps the phrases passes. For example, "at most 5 questions" can sit in a sentence that says the opposite, or the order check in `test_design_orchestration_and_ui_ux` can pass in a skill that never skips a stage.

| AC | Automated evidence | Behavioral evidence | Assessment |
| --- | --- | --- | --- |
| AC-001 | TEST-009 strings | Acceptance report (observed) | Rests on the manual run |
| AC-002 | none required (TEST-016 is ID presence) | Report | Manual only |
| AC-003 | TEST-009 template strings; TEST-015 checks the sample has `Do not copy` | Report | Template proven; the brief's "origin mark on every item" is not checked |
| AC-004 | ID presence | Report | Manual only |
| AC-005 | TEST-010 strings; TEST-015 checks the comment prefix only | Report | **The pairwise "differs in at least two axes" is not checked**, though the `axes:` field in each comment would make it checkable |
| AC-006 | TEST-015 (no `https?:` script/img, no P0) | Report | Mostly proven; protocol-relative `//` sources slip through |
| AC-007 | TEST-010 strings | Report | Manual only |
| AC-008 | ID presence | Report (hashes) | Manual only |
| AC-009 | ID presence | Report | Manual only |
| AC-010 | TEST-011 strings; TEST-015 headings | Report | Section order proven on the sample; "section 9 lists the P0s" not checked |
| AC-011 | TEST-015 | Report | Hex, spacing multiple of 4, `-ink` contrast, and font count proven. **Font and spacing values cited in DESIGN.md are not compared with tokens** (only hex) |
| AC-012 | TEST-011 (the word "confirmation") | **None** (report: not exercised) | Unproven |
| AC-013 | ID presence | Report | Manual only |
| AC-014 | TEST-012 strings (5 of 6 axes; "stance/postura" not asserted) | Report | Manual only |
| AC-015 | TEST-013 (order of names, `status: approved` present) | **None** (not in the report) | Unproven |
| AC-016 | TEST-015 asserts no P0 only | Report | **The AC is about P1-RAW-COLOR and P1-FONT-LITERAL; the test does not assert them.** The sample is currently clean (verified: 0 P0, 0 P1, 0 P2), so this is a regression gap, not a failure |
| AC-017 | TEST-013 strings | **None** | Unproven |
| AC-018 | TEST-008 | n/a | Proven, except the `nextlevelbuilder` license check is `"" in line`, which is always true |
| AC-019 | TEST-014 (one phrase) | **None**. The designer has `Write, Edit, Bash` | Unproven; the restriction is prose only |
| AC-020 | ID presence | Report (inline, not a subagent) | Manual only |
| AC-021 | TEST-014 (`design-reviewer` has no `Edit`) | Report (inline, not a subagent) | Tool restriction proven; verdict behavior manual |
| AC-022 | TEST-014 (registry order, names in `orchestrator.md`) | **None** | Registration proven; routing unproven |

Summary: 10 ACs rest only on the manual report. Four (AC-012, AC-015, AC-017, AC-019) have no behavioral evidence, and AC-022 routing has none. The report says the run used the 0.4.0 plugin, so skill triggering by `description`, subagent dispatch, the orchestrator routing, and the hook were not exercised at all.

How the implementation can be wrong while every test passes: any of the FIND-001, FIND-002, FIND-004, and FIND-005 defects below. Each reproduces with all 16 TESTs green.

## Findings

### FIND-001: A DESIGN.md that lists the P0 hexes as forbidden allowlists them and disables P0-INDIGO
- Severity: blocker
- Status: open
- Location: agent-system/scripts/lint_design.py:116-121 (`declared_colors`), :128, :131; skills/design/references/design-md-format.md:62; skills/design/references/anti-slop.md:18
- Evidence: `declared_colors` takes every hex anywhere in `DESIGN.md` as a declared brand color. REQ-013 and `design-md-format.md` section 9 tell the designer to include "The lint P0 list from anti-slop.md, always", and that list (`anti-slop.md:18`) spells out the seven indigo hexes. Reproduction: a `DESIGN.md` containing `## 9. Anti-padrões` / `- Nunca use #6366f1 nem #7c3aed.` plus `src/B.tsx` with `style={{color:"#6366f1"}} className="bg-indigo-500"` gives `0 P0`, exit 0 (only a P1-RAW-COLOR). Without that DESIGN.md line, both are P0. The sample happens to word section 9 without hexes, so no test sees it.
- Requirement: REQ-028, REQ-030 (allowlist is for a color *declared* as brand, not one mentioned as forbidden), REQ-013
- Recommendation: Read allowed colors only from `tokens.css` custom properties and from the DESIGN.md "2. Cor" section (or from `--*: #hex` declarations), never from section 9 or prose. Add a test where DESIGN.md forbids `#6366f1` in section 9 and the component still gets P0-INDIGO.

### FIND-002: Quadratic regexes make the hook exceed its 20 s timeout on realistic files
- Severity: major
- Status: open
- Location: agent-system/scripts/lint_design.py:40 (`TW_GRADIENT`), :43-46 (`ICON_TEXT`); agent-system/scripts/hook.py:136-150
- Evidence: `TW_GRADIENT`'s lazy `[^"'`\n]*?` rescans to the end of the line for every `from-*` with no `to-*`, and `ICON_TEXT`'s `<(\w+)[^>]*\bclass` rescans for every `<`. Timings: `"from-blue-500 " * 8000` (112 KB) took 35 s; `"<h1 " * 8000` took 10.6 s; growth is about 4x per doubling. A realistic 324 KB minified Tailwind-like file (`.from-blue-N00{--tw-gradient-from:#3b82f6;...}` × 3000, one line) run through `hook.py` as a Claude `PostToolUse` Write took **31.3 s**, beyond the 20 s hook timeout in `hooks/claude-hooks.json`. `MAX_BYTES` (512 KB) does not prevent it, and `public/`/`static/` are not skipped. The hook still exits 0, but every such edit stalls the agent until the host kills it, and the finding is lost.
- Requirement: REQ-032 ("dentro do timeout do hook"); spec constraint that the hook never blocks
- Recommendation: Bound the scans, for example by restricting `TW_GRADIENT` to class-attribute contents, using `[^>"'`\n]{0,400}?`, and limiting `ICON_TEXT` with `[^>]{0,500}`. Skip files with very long lines (minified) in the hook, and give the hook a time budget. Add a performance test (for example 300 KB minified CSS under 2 s).

### FIND-003: REQ-032 and AC-028 are not met for Cursor, and the spec was not amended
- Severity: major
- Status: open
- Location: agent-system/scripts/hook.py:325-327; docs/specs/design-pipeline.md REQ-032, AC-028; docs/tasks/design-pipeline.md:26 and TASK-003 `Stop if`
- Evidence: REQ-032 says the findings are shown to the agent and "Isso vale para Claude Code e Cursor". In Cursor, `main()` pops `design_lint` and emits `{}`. The finding only reaches the timeline, and only in opted-in projects. The plan recorded this as a known limitation and said to open a `change-request` before TASK-003 if the timeline was not enough. No change request exists, the spec is still `approved` with the original wording, and TEST-007 asserts the Cursor reply is `{}`. So the test encodes the deviation as expected behavior.
- Requirement: REQ-032, AC-028
- Recommendation: Run `change-request`. Either amend REQ-032 and AC-028 to "Claude Code: shown to the agent; Cursor: timeline event, and the `frontend-implementer`/`ui-ux` run the lint themselves", with user approval, or find a Cursor channel. If it stays as is, it needs the user's explicit acceptance, recorded as `accepted` with a Justification.

### FIND-004: P0 false negatives on common real front-end code, including forms the spec names
- Severity: major
- Status: open
- Location: agent-system/scripts/lint_design.py:39 and :133-137 (gradient), :43-46 and :153-159 (emoji), :53 and :150-152 (side stripe), :57-63 (metric)
- Evidence (each reproduced, exit 0 with no P0):
  - Gradient stops other than hex: `linear-gradient(135deg, rgb(139,92,246), rgb(59,130,246))`, `linear-gradient(to right, purple, blue)`, and `hsl(...)` stops. REQ-028 defines the rule by hue, not by hex notation.
  - Emoji in a child or after inline markup: `<button><span>🚀</span> Enviar</button>`, `<h2>Título <em>x</em> 🎉</h2>`, `<span className={styles.icon}>⚡</span>`. `ICON_TEXT` reads only the text right after the opening tag, and only for a quoted `class`.
  - Side stripe with `className={cn("border-l-4 ...", "rounded-lg")}`: `CLASS_ATTR` stops at the first quote after `{`, so `cn`/`clsx` class lists, which are very common in TSX, are never inspected.
  - Portuguese and common metric forms: "99,9% de disponibilidade" (the `de` breaks the match), "mais de 10 mil empresas", "100% uptime", "Join 10,000+ developers". REQ-028 explicitly requires "equivalentes em português", and the natural PT phrasing is missed.
  - REQ-030 asymmetry: `from-violet-600 to-pink-500` is still P0-GRADIENT when both colors are declared in tokens (`TW_GRADIENT` ignores `allowed`), while the CSS gradient branch honors the allowlist.
- Requirement: REQ-028, REQ-030
- Recommendation: Extract stop colors from `rgb()`/`hsl()`/named colors as well. Scan emoji in the element's inner text up to the closing tag, bounded. Read class strings inside `{...}` expressions. Allow optional `de` and `mil` in PT metrics. Apply `allowed` through the `TAILWIND` hex map in `TW_GRADIENT`. Add one fixture per variant.

### FIND-005: P0 false positives that block review on legitimate UI
- Severity: minor
- Status: open
- Location: agent-system/scripts/lint_design.py:42 (`EMOJI` range `☀-➿`), :55, :56-63
- Evidence (each exit 1): `<button aria-label="Fechar">✕</button>` and `<li>✓ Sem cartão</li>` (dingbats, not emoji, both standard glyphs); "Over 3 users can edit this doc." and "Plano de 2x mais barato" (P0-METRIC); `className="border-l-4 rounded-none"` (P0-SIDE-STRIPE, though `rounded-none` removes the radius); `\bacme\b` also matches identifiers such as `acme-challenge`. With the `design-reviewer` rule that any open P0 is FAIL, these force suppressions on correct code. The spec accepts heuristic error "within what the fixtures cover", which is why this is minor.
- Requirement: REQ-028
- Recommendation: Restrict `EMOJI` to emoji-presentation code points (exclude U+2713/2714/2715/2717 and similar dingbats). Exclude `rounded-none`. Require marketing context for "over N users" and the PT "Nx mais" form, or demote them. Add negative fixtures.

### FIND-006: P1 false positives and false negatives in JSX, SVG, and prose
- Severity: minor
- Status: open
- Location: agent-system/scripts/lint_design.py:169 (`CSS_HEX`), :172-175, :201
- Evidence: `<p>A smooth transition between your old tool and ours.</p>` gives P1-NO-REDUCED-MOTION, because `MOTION` matches the bare word `transition` followed by a space. `href={"#add"}`, `fill="url(#bad)"`, and "Veja a issue #123" give P1-RAW-COLOR: the `href="` exclusion misses the JSX `{"` form, `url(#id)` references, and three-hex-letter or digit words in prose. CSS-in-JS misses: `{ transition: "all 0.2s" }` gives no P1-TRANSITION-ALL, and `{ outline: "none" }` gives no P1-OUTLINE-NONE (the quotes defeat both regexes).
- Requirement: REQ-029
- Recommendation: Limit `MOTION`'s bare-`transition` branch to class attributes. Exclude `url(#` and `href={"#`. Require CSS context for three-digit hex. Allow an optional quote before the value in `TRANSITION_ALL` and `OUTLINE_NONE`. Add fixtures.

### FIND-007: Lint tests cover one variant per rule; the AC-026 hex path and gradient allowlist are untested
- Severity: major
- Status: open
- Location: agent-system/tests/test_design_lint.py:14-22, :70-81
- Evidence: AC-026 says "um componente que usa `#7c3aed`", but the test uses `className="bg-violet-600"`. Deleting the `value not in allowed` check on the hex branch (lint_design.py:128) keeps every test green. In the same way, these all go undetected: deleting `TW_GRADIENT`, `CLIP_TEXT`, the Tailwind side-stripe branch, or the `icon`-class emoji branch; shrinking `AI_INDIGO` to one value; removing the PT metric alternatives; off-by-one changes in the P2 thresholds. No test covers the hook timeout, `.py` skipping, or binary and unreadable files.
- Requirement: REQ-033 ("fixtures que reproduzem cada regra"), AC-024, AC-026, AC-028
- Recommendation: Turn `P0_CASES` into a list of variants per rule (hex, class, CSS-in-JS; CSS and Tailwind gradient; gradient text; emoji in `h*`, `button`, `li`, `icon`; CSS and Tailwind stripe; EN and PT metrics; each CDN). Make AC-026 use the hex literally, and add a gradient-allowlist case and P2 boundary cases (6 and 7, 3 and 4).

### FIND-008: Behavioral ACs rest on string-presence tests or the manual report; four have no behavioral evidence
- Severity: major
- Status: open
- Location: agent-system/tests/test_design_skills.py:71-148, :199-205; docs/reviews/design-pipeline-acceptance.md
- Evidence: See the audit table. TEST-016 asserts only that the AC IDs appear in the report. AC-012 was not exercised (the report says so). AC-015, AC-017, AC-019, and AC-022 routing do not appear in the report and have only phrase checks. The acceptance run used the installed 0.4.0 plugin, so skill triggering, subagent dispatch (`designer`, `frontend-implementer`, `design-reviewer` as real subagents), orchestrator routing, and the hook were never exercised end to end. `validate_verification.py` already warns for six of these ACs.
- Requirement: REQ-014, REQ-018, REQ-020, REQ-023, REQ-026 (and the manual-only ACs listed in the audit)
- Recommendation: Rerun the acceptance with this branch's plugin installed, covering AC-012, AC-015, AC-017, AC-019, and AC-022 and the real subagents and hook. Record each in the report. Where deterministic checks are cheap, add them: parse the `axes:` field of each direction comment and assert pairwise differences on 2 or more axes (AC-005), and assert section 9 of the sample names the P0s (AC-010). Alternatively, the user explicitly accepts manual evidence for those ACs, recorded with a Justification.

### FIND-009: Smaller assertion gaps in the sample and contract tests
- Severity: minor
- Status: open
- Location: agent-system/tests/test_design_skills.py:60, :100, :174-176, :195-196
- Evidence: (1) TEST-015 maps AC-016, but asserts only "no P0"; P1-RAW-COLOR and P1-FONT-LITERAL in `src/` would pass. (2) AC-011 requires font and spacing values cited in DESIGN.md to match tokens; only hexes are compared. (3) `("nextlevelbuilder/ui-ux-pro-max-skill", "")` makes the license assertion vacuous (`"" in line`). (4) `test_design_review_contract` asserts 5 of the 6 axes ("stance"/"postura" is missing).
- Requirement: AC-011, AC-016, AC-018, REQ-016
- Recommendation: Assert no P1-RAW-COLOR or P1-FONT-LITERAL under `src/` of the sample. Compare `px` and font-family values cited in DESIGN.md against tokens. Assert `MIT` for nextlevelbuilder. Add `stance`.

### FIND-010: Hook and CLI robustness details
- Severity: minor
- Status: open
- Location: agent-system/scripts/hook.py:136-147; agent-system/scripts/lint_design.py:264-267
- Evidence: Fail-open holds (verified exit 0 for binary, missing, directory, and relative paths). The timeline gets only the count line and no file text (verified, and asserted by TEST-007). However: (1) a file outside every workspace root is still linted and reported, using the file's own folder to find DESIGN.md. (2) In the CLI, `lint_paths` has no guard around `stat()`/`read_text()`: an unreadable file or a broken symlink raises a traceback and exits 1, which the documented exit codes read as "P0 found". (3) Files over 512 KB are skipped silently, with no notice, so a CLI run can report "0 P0" on a file it never read.
- Requirement: REQ-027, REQ-031, REQ-032
- Recommendation: In the hook, lint only files under a workspace root. In the CLI, catch `OSError` per file, report it on stderr, and exit 2. Print a "skipped (size)" line for oversized files.

### FIND-011: Documentation placement and consistency
- Severity: minor
- Status: open
- Location: README.md:369; README.pt-BR.md:392; agents/design-reviewer.md (output); skills/design-review/references/review-checklist.md:39
- Evidence: (1) In both READMEs, the lint paragraph is inserted inside the "User interface" command list, between `/ui-ux` and the `/apple-design` bullet, which splits the list. (2) `design-reviewer` writes `<reviews_dir>/<slug>-design.md` without the `fingerprint` front matter that `artifacts.md` requires for reviews, and the `-design` suffix breaks the one-slug-per-feature convention, so the gate never reads it. That is fine if intentional, but it should be stated. (3) The `design-review` done-condition is "the checklist has no 'yes'", but item 27 ("on focus with a delay, or on hover with none?") is not a yes/no question.
- Requirement: maintainability; agent-system/docs/artifacts.md review format
- Recommendation: Move the lint paragraph after the list. Say in `contracts.md` and `artifacts.md` that the design review is a separate, non-gating artifact, or add the fingerprint. Rephrase checklist item 27 as a yes/no question.
