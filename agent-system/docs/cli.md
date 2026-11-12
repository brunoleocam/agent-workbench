# CLI contracts

All scripts use only the Python 3.10+ standard library, run on Windows, macOS, and Linux, and make no network calls, commits, pushes, or installs. In a project, run the copies in `.cursor/agent-system/scripts/` from the root. In the plugin, the same files live in `agent-system/scripts/`.

## Common validator contract

| Option | Effect |
| --- | --- |
| `--root PATH` | project root (default: current directory) |
| `--feature SLUG` | file name shared by spec, tasks, reviews, and security |
| `--spec`, `--tasks`, `--tests`, `--review`, `--security` | explicit path, relative to the root; wins over `--feature` |
| `--json` | structured output (`ok`, `failures`, `warnings`, `results[]`) |
| `--strict` | warnings also fail |
| `--no-record` | do not write an event to the timeline |
| `--help` | argparse help |

Exit codes: `0` success, `1` validation or gate failed, `2` configuration error, bad argument, missing file, invalid JSON, or a path outside the root.

Text output: one line per result (`[PASS]`, `[WARN]`, `[FAIL]`, `[INFO]`) and the final line `<check> passed.` or `<check> failed.`.

In an initialized project, each validator writes its own event (`SPEC_VALIDATION_COMPLETED`, `TASK_VALIDATION_COMPLETED`, `PROOF_EXECUTION_STARTED`/`COMPLETED`, `VERIFICATION_COMPLETED`) with `feature` and the result, and updates `state.json → verification.<slug>`. A failure to write the timeline does not change the exit code.

## validate_spec.py

```powershell
python .cursor/agent-system/scripts/validate_spec.py --feature reset-password --require-approval
```

FAIL: front matter without `status` or with an invalid value, invalid `complexity` or `security_risk`, no REQ or AC, duplicate ID, AC without a REQ, AC with a nonexistent REQ, item without text, `--require-approval` without `status: approved`.
WARN: REQ without an AC, no assumptions or constraints section, approved spec with an open `- [ ]` question, REQ or AC cited but not defined, ADR cited without a file, `security_risk` missing for M+, NONE with triggers.
INFO: how many requirements use EARS.

## validate_tasks.py

```powershell
python .cursor/agent-system/scripts/validate_tasks.py --feature reset-password
```

FAIL: duplicate ID, task without a title, without a REQ or AC, with a REQ/AC outside the spec, without verification, without `Done when`, missing or unknown status, nonexistent or circular dependency, `blocked` without a cause, `done` without a PASS proof or `Evidence`; TEST without `Command` (if required), without an AC, with a nonexistent AC or task.
WARN: task without an AC, without `Gate`, `done` before its dependency, AC without a task or without a TEST, spec not found.

## check_proofs.py

```powershell
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password --task TASK-002
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password --only TEST-003 --timeout 300
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password --dry-run
python .cursor/agent-system/scripts/check_proofs.py --fingerprint
```

Extra options: `--only TEST-NNN` and `--task TASK-NNN` (repeatable), `--timeout` (default 600 s; the TEST's `Timeout` takes priority), `--allow EXE` (repeatable; also `proof_allow` in the layout), `--allow-shell`, `--allow-inline`, `--dry-run`, `--fingerprint`. `--allow-shell` and `--allow-inline` only with the user's authorization.

Status per TEST: `PASS` (exit 0), `FAIL` (exit ≠ 0), `TIMEOUT` (process tree terminated), `ERROR` (missing executable or failure to start: environment), `REFUSED` (policy). Exit: `1` if there is any FAIL or TIMEOUT, otherwise `2` if there is any ERROR or REFUSED, otherwise `0`.

Policy (ADR-0002): runs without a shell, from the root or from `Cwd`. Only executables on the list (python, python3, py, pytest, uv, poetry, tox, nox, hatch, node, npm, pnpm, yarn, bun, deno, vitest, jest, tsc, dotnet, go, cargo, mvn, mvnw, gradle, gradlew, java, php, composer, phpunit, pest, ruby, bundle, rake, rspec, make, ctest). `npx`, `dlx`, `npm exec`, `npm x`, and `bun x` are out because they download packages. The install refusal is best effort, by subcommand name: it refuses when the subcommand installs, publishes, or removes (`npm install`, `python -m pip install`, `uv pip install`, `make install`, `cargo publish`, `dotnet add`...), `yarn` and `bundle` without a subcommand, and shell operators without `Shell: yes`. On Windows, a `.cmd`/`.bat` (like `npm.cmd`) runs through `cmd.exe`, so arguments with `& | < > ^ %` are refused in that case. It refuses inline code (best effort, by argument analysis; an unknown flag whose value looks like a file, such as `node --env-file .env -e`, still hides the code): `python -c` (including `-Bc`), `python -m` outside the list of test modules (pytest, unittest, coverage, tox, mypy, ruff...) and the project's own modules, `node -e/--eval/-p`, `node --import data:/http:`, `bun -e`, `deno eval`, `deno run <URL>`, `ruby -e` (including `-we`), `rake -e`, `php -r`, `make --eval`, `bash/sh -c` (including `-ec`), `pwsh -Command` and `cmd /c`, `perl -e`, `deno run npm:/jsr:`, also when started by `npm`/`pnpm`/`yarn`/`bun` (`yarn run node -e`, `pnpm node -e`) or called by `uv run`, `poetry run`, `hatch run`, `pnpm exec`, `yarn exec/node`, or `bundle exec` (the inner command goes through the same policy). An approved TEST calls the project's runner (`pytest`, `npm test`, `dotnet test`, `python -m pytest`...) or a versioned test file (`python tests/check_x.py`). `--allow-inline` allows inline code in one run, with the user's authorization. With `Shell: yes` and `--allow-shell`, the install and inline-code refusals apply to each part of the command (also after `env`, `xargs`, and similar), and shell substitution (`$(...)`, backticks, `<(...)`), heredocs, and piping into an interpreter with no script (`curl x | sh`) are refused without `--allow-inline`. The policy separates a test from an arbitrary command, but it is not a sandbox: a test file executes whatever it contains.

The proof stores the fingerprint from before the run. If the workspace changes while the tests run (a parallel edit or a generated file outside `.gitignore`), the script warns and the gate treats the proofs as stale; with `--strict`, it exits with 1.

Output: `.cursor/agent-system/proofs/<slug>.json` (source of truth) and `<slug>.md`. Each proof stores TEST, REQ, AC, task, command (redacted), exit code, status, reason, timestamps, duration, the last 20,000 characters of stdout and stderr with secrets masked, and the fingerprint. Running only some TESTs keeps the proofs of the others. Proofs are local evidence, tied to the fingerprint: do not version the folder (the plugin ignores it in `.gitignore`; do the same in the project). In a project that is a subfolder of a git repository, the fingerprint considers only the subfolder's files.

Fingerprint: the git blob id of each project file (the index for an unchanged file, `git hash-object` for a modified or untracked one), excluding `.cursor/`, caches, and the Markdown of the harness's doc folders. It does not use HEAD: committing the same content keeps the fingerprint, and a review recorded before the commit stays valid. Without git, a hash of the project's files (up to 5,000 files). It does not require a commit.

## check_drift.py

```powershell
python .cursor/agent-system/scripts/check_drift.py --feature reset-password --stamp
python .cursor/agent-system/scripts/check_drift.py --feature reset-password --task TASK-002 --strict
python .cursor/agent-system/scripts/check_drift.py --feature reset-password --stamp --refresh --task TASK-002
```

Detects plan drift: files that a pending task will touch and that changed after the plan was written. `--stamp` writes a `- Baseline:` line (`path=digest`, 10 hex characters of a SHA-256 of the content; line-ending differences are ignored; `absent` for a file the task will create) after the `- Files:` line of each todo or blocked task that has none; `--refresh` rewrites existing ones after an intentional re-plan. The default run compares the digests with the working tree for todo and blocked tasks and takes the common validator options (`--task` is repeatable, `--json`, `--strict`).

A changed file is *expected* (INFO) when another task of the same plan that is done or in progress lists it in `Files:`; otherwise it is drift (WARN, FAIL with `--strict`, exit 1). A file added to `Files:` after the stamp is also a WARN. A task without a Baseline is INFO. The check reads files only and never writes a timeline event. Idea adapted from [shadcn/improve](https://github.com/shadcn/improve) (MIT).

## validate_verification.py

```powershell
python .cursor/agent-system/scripts/validate_verification.py --feature reset-password
```

Includes the structural failures of `validate_spec` and `validate_tasks`. FAIL: required AC without a TEST, required TEST without a proof, a proof other than PASS, a proof from another fingerprint, TEST command changed after the proof, a task that is neither `done` nor `cancelled`, missing review at M+ or one with status FAIL, missing security review with HIGH/CRITICAL risk or one with status FAIL, a required review or security review without a `fingerprint` or with a fingerprint different from the current workspace (exact comparison), open blocking finding, accepted risk without justification.
WARN: a non-required review or security review with a fingerprint from another state, open `major`/`MEDIUM` finding, AC covered only by an optional TEST.

## validate_workflow.py

```powershell
python .cursor/agent-system/scripts/validate_workflow.py [--json]
python .cursor/agent-system/scripts/validate_workflow.py --mermaid
```

Validates `workflow.json` (the execution graph; default: next to `scripts/`, `--workflow` to choose another file, `--agents` for the registry). FAIL (exit 1): duplicate node id, unknown kind or missing field, edge to an unknown node, unknown `start`, node unreachable from `start`, an agent of `agents.json` with `scope: user` (except `orchestrator`) without a node, a node using an agent that is not registered, a script node whose script is missing, a gate (`validate_verification.py`) without an `on: fail` or an `on: escalate` edge, a cycle made only of agent nodes, a `group` without a `join` or a branch with no edge to its join, an invalid `when` or `on`, `limits.max_revisions` outside 1 to 10, and, in the plugin, a `default_state()` key without an owner in `state_fields` (or the reverse, or an unknown writer). Exit `2`: missing file or invalid JSON. `--mermaid` prints the graph as a `flowchart` (exit 1 and no diagram when invalid).

Edge semantics: `on` (`pass`, `fail`, `escalate`; absent means any result) and `when` (`class`, `complexity_min`, `complexity_max`, `security_min`, `security_max`, `interface`, `design_approved`; all keys must hold). Edges are tried in file order and the first match wins; edges of the same `group` fan out together and meet at `join`.

## next_step.py

```powershell
python .cursor/agent-system/scripts/next_step.py --from classify --class FEATURE --complexity M --security HIGH
python .cursor/agent-system/scripts/next_step.py --from gate --result fail --feature reset-password --interface none
python .cursor/agent-system/scripts/next_step.py --from proofs --complexity M --security HIGH --interface new --text
```

Prints JSON: `next` (node ids), `nodes` (id, kind, and the agent, script, or question), `parallel`, `join`, `reason` (the conditions that held), and `status`: `continue`, `needs_decision` (a human node, with `question`), `done` (terminal node), or `no_match`. `--result` defaults to `pass`. `--class`, `--complexity`, `--security`, and `--interface` have no default: an edge that depends on one that was not given is an argument error (exit 2), so a forgotten `--interface new` cannot skip the design path. After a failed gate, `--feature` is required: it reads `state.json → revisions.<slug>` (incremented by each failed `validate_verification.py` run in an opted-in project, reset to 0 by a pass or by an event recorded with `--node escalate` once the user answers the escalation; `record_event.py` cannot record a script node such as `gate`, so the count moves only with the real gate), and at `limits.max_revisions` the result becomes `escalate`. Exit `0` with a next or terminal node, `1` when no edge holds, `2` for an unknown node, a condition whose argument is missing, or an invalid graph. It only recommends; it runs nothing and writes nothing.

## metrics.py

```powershell
python .cursor/agent-system/scripts/metrics.py [--feature reset-password] [--since 2026-11-01] [--json]
```

Reads `.cursor/timeline/events.jsonl` and prints, per agent (the `agent-workbench:` prefix is dropped): runs (`SUBAGENT_STOPPED`), total and median duration (each stop paired with the oldest open start of the same session and agent), response characters (`AGENT_RESPONSE`), and tokens; per feature: gates, failed gates, revisions until the first passing gate, and whether it passed. `--feature` keeps only that feature and limits the agents to the span between its first and last event, because subagent events carry no slug. `--since` drops older events (invalid value: exit 2). Malformed lines are skipped and counted in `skipped`. It never writes anything.

Tokens: in Claude Code, the `SubagentStop` hook reads the subagent's own transcript (`agent_transcript_path`, only inside a `subagents/` folder, up to 50 MB) and records only the numbers (`input`, `output`, `cache_read`, `cache_creation`; the last usage of each message id) on `SUBAGENT_STOPPED`. The transcript format is not a documented contract, so any surprise leaves the event without tokens. Cursor sends no usage. An agent without token data shows `unavailable`, never zero.

## lessons.py

```powershell
python .cursor/agent-system/scripts/lessons.py add --category testing --title "..." --description "..." [--context "..."] [--evidence TEST-004]
python .cursor/agent-system/scripts/lessons.py list [--status confirmed] [--category testing] [--json] [--verbose]
python .cursor/agent-system/scripts/lessons.py confirm --id LESSON-001
python .cursor/agent-system/scripts/lessons.py reject --id LESSON-002 --reason "..."
python .cursor/agent-system/scripts/lessons.py render
```

Global store: `promote --id LESSON-NNN` (a confirmed project lesson only) and `--scope global` on `add`, `list`, `confirm`, and `reject` use `$AGENT_WORKBENCH_HOME/lessons.json` (default `~/.agent-workbench/lessons.json`). Exit `1` when the text contains the project's path or folder name, an absolute path, a URL, or a secret, or when the title already exists there; exit `2` when the project's `layout.json` has `"global_lessons": false`.

Categories: architecture, requirements, implementation, testing, security, performance, debugging, workflow, tooling. Exit `1` for a duplicate (normalized title) or text containing a secret; `2` for an uninitialized project, invalid argument, nonexistent ID, or invalid JSON. `lessons.json` is the source of truth; `LESSONS.md` is regenerated on every change.

## run_evals.py (plugin only)

```powershell
python agent-system/scripts/run_evals.py [--json]
```

Runs the fixtures in `agent-system/evals/fixtures/` and compares the exit code and output excerpts with `expect.json`. Exit `0` if all match, `1` if any diverges, `2` if a fixture is invalid.

## Others

`status_cmd.py`, `timeline_view.py --write-md`, and `init_project.py --root . [--for-cloud] [--claude]` keep the previous contract.

## Decision trace

```powershell
python .cursor/agent-system/scripts/record_event.py --event REVIEW_COMPLETED --summary "..." --feature reset-password --node review --inputs docs/reviews/reset-password.md,docs/specs/reset-password.md
python .cursor/agent-system/scripts/timeline_view.py --feature reset-password [--json]
```

The completion events of `validate_spec.py`, `validate_tasks.py`, `check_proofs.py`, and `validate_verification.py` carry `feature`, `node` (`spec_check`, `tasks_check`, `proofs`, `gate`), `inputs` (relative paths of the artifacts read), and `fingerprint` (the workspace digest the decision was made on; for `check_proofs.py`, the one from before the run, the same as the proofs). Only paths are recorded, never file content, test output, or prompt text; a secret-looking path becomes `[redacted-path]`.

`record_event.py --event <EVENT> --summary "..." [--feature SLUG] [--result ...]` keeps its contract and gains `--node <id>` (a node of `workflow.json`; an unknown id exits 2) and `--inputs a,b` (needs `--node`), so reviews, ADRs, and human decisions leave the same trace. `timeline_view.py --feature <slug>` prints every event of that feature, oldest first, with node, agent, result, inputs, and a 12-character fingerprint, and marks a verdict whose fingerprint differs from the previous verdict ("code changed since the previous verdict"). Without `--feature` the output is unchanged.
