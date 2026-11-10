# ADR-0002: Proofs, fingerprint, and command policy

Status: accepted
Date: 2026-11-03

## Context

`afterShellExecution` does not carry an exit code, so the hook's test result is inferred. The user reviews the diff before authorizing git, so the proof cannot require a commit. `check_proofs.py` executes commands written in an artifact, which is a risk surface.

## Decision

- `check_proofs.py` is the only source of a deterministic result. It writes `.cursor/agent-system/proofs/<slug>.json` (source of truth) and `<slug>.md` (view).
- Each proof stores the workspace fingerprint from before the run: the content of each project file, as a git blob id (the index for an unchanged file, `git hash-object` for a modified or untracked file, with the same line-ending normalization as `git add`), limited to the project folder when it is a subfolder of the repository. HEAD is not part of the calculation: committing the same content keeps the fingerprint, so a review recorded before the commit stays valid after it. It excludes `.cursor/`, caches, and the harness's doc directories, so writing a review or checkpoint does not invalidate the proof. Without git: a hash of the project's files, with a limit. If the workspace changes during the run, the proofs become stale for the gate (the tested code is not guaranteed to be the current one); `--strict` exits with 1.
- Execution without a shell, with `shlex` or a JSON list. The executable is resolved with `shutil.which`. An allowlist of executables and refusal of subcommands that install, publish, or remove packages, including in each part of a shell command. Extension only with `--allow <exe>`. Shell only with `Shell: yes` in the TEST and `--allow-shell` on the CLI. Inline code (`python -c`, `node -e`, `ruby -e`, `php -r`, `deno eval`, `deno run <URL>`, `bash -c`, `python -m` outside the test modules and the project's own, shell substitution, and heredocs) is refused by default, also when a wrapper (`uv run`, `poetry run`, `bundle exec`, `yarn node`...) starts it: the inner command goes through the same policy. An approved TEST calls the project's runner or a versioned test file, which is visible in the diff and in the review; inline code in the tasks artifact is an arbitrary command. `--allow-inline` lifts it for one run, only with the user's authorization. Proofs in `.cursor/agent-system/proofs/` are local evidence and are not versioned.
- Status: PASS, FAIL (exit ≠ 0), TIMEOUT, ERROR (environment, missing executable), REFUSED (policy). TIMEOUT, ERROR, and REFUSED are not treated as an application failure in the report.

## Alternatives

- Require a commit and use the SHA: contradicts human review before git.
- A real sandbox: out of scope and not portable. The list is protection against accidents, not isolation; the commands come from a versioned, approved artifact.

## Consequences

- A test that writes a tracked file changes the fingerprint; the script warns when the fingerprint before and after differs.
- A runner command outside the list requires an explicit `--allow`.
