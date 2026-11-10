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

## validate_verification.py

```powershell
python .cursor/agent-system/scripts/validate_verification.py --feature reset-password
```

Includes the structural failures of `validate_spec` and `validate_tasks`. FAIL: required AC without a TEST, required TEST without a proof, a proof other than PASS, a proof from another fingerprint, TEST command changed after the proof, a task that is neither `done` nor `cancelled`, missing review at M+ or one with status FAIL, missing security review with HIGH/CRITICAL risk or one with status FAIL, a required review or security review without a `fingerprint` or with a fingerprint different from the current workspace (exact comparison), open blocking finding, accepted risk without justification.
WARN: a non-required review or security review with a fingerprint from another state, open `major`/`MEDIUM` finding, AC covered only by an optional TEST.

## lessons.py

```powershell
python .cursor/agent-system/scripts/lessons.py add --category testing --title "..." --description "..." [--context "..."] [--evidence TEST-004]
python .cursor/agent-system/scripts/lessons.py list [--status confirmed] [--category testing] [--json] [--verbose]
python .cursor/agent-system/scripts/lessons.py confirm --id LESSON-001
python .cursor/agent-system/scripts/lessons.py reject --id LESSON-002 --reason "..."
python .cursor/agent-system/scripts/lessons.py render
```

Categories: architecture, requirements, implementation, testing, security, performance, debugging, workflow, tooling. Exit `1` for a duplicate (normalized title) or text containing a secret; `2` for an uninitialized project, invalid argument, nonexistent ID, or invalid JSON. `lessons.json` is the source of truth; `LESSONS.md` is regenerated on every change.

## run_evals.py (plugin only)

```powershell
python agent-system/scripts/run_evals.py [--json]
```

Runs the fixtures in `agent-system/evals/fixtures/` and compares the exit code and output excerpts with `expect.json`. Exit `0` if all match, `1` if any diverges, `2` if a fixture is invalid.

## Others

`record_event.py --event <EVENT> --summary "..." [--feature SLUG] [--result ...]`, `status_cmd.py`, `timeline_view.py --write-md`, and `init_project.py --root . [--for-cloud] [--claude]` keep the previous contract.
