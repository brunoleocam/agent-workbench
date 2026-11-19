# ADR-0004: A test runner declared once instead of a command policy per TEST

Status: proposed
Date: 2026-11-19
Supersedes (if accepted): the command-policy part of ADR-0002

## Context

ADR-0002 lets each TEST carry a full `Command` and guards it with an allowlist of executables plus a denylist of install subcommands and inline-code flags. About 320 of the 646 lines of `check_proofs.py` parse interpreter flags (`python -Bc`, `node --import data:`, `uv run`, `yarn node -e`, `pwsh -EncodedCommand`...). Every new runner or wrapper reopens the list. The README already calls the guardrails "best-effort" and "not a sandbox". A test file still runs whatever it contains. The policy blocks accidents. It does not stop a determined author, who can write the same code into a test file.

## Decision (proposed)

1. The project declares its runner once, in `.agent-system/layout.json`:

   ```json
   { "test_runners": { "py": ["python", "-m", "pytest", "{target}", "-q"], "js": ["npm", "test", "--", "{target}"] } }
   ```

2. A TEST names only what to run: `- Target: tests/test_reset.py::test_expiry` and optionally `- Runner: py` (default: the only runner, or the one whose key matches the target's extension).
3. `check_proofs.py` builds the argv from the template, substitutes `{target}` as one argument, and checks only that the target is a path inside the project (plus an optional `::node` suffix). No flag parsing.
4. The runner template is reviewed once, as configuration, when it is added or changed. A change to it invalidates every proof (it enters the fingerprint inputs).
5. `Command` stays accepted for compatibility, under the current ADR-0002 policy, and `validate_tasks.py` warns "prefer Target" for new TESTs. After two minor versions, `Command` requires `--allow-command`.

## Alternatives

- **Keep the allowlist and denylist (today).** It works and is tested. The cost is ongoing: each new wrapper needs a parser, and an uncovered case looks protected when it is not.
- **A real sandbox per TEST (container, seccomp).** It is the only real protection against hostile test code. It is not portable to every developer machine and is out of scope for the plugin (see ADR-0006).
- **No policy at all.** It is honest about the limits but loses the accident protection: the agent would no longer be stopped from proving a criterion with an arbitrary `python -c "exit(0)"`.

## Consequences

- About 300 lines of policy code become a compatibility path and can be deleted later.
- The proof of a criterion becomes "the project's runner, on this target", which is also what a reviewer reads.
- Projects that call many ad-hoc scripts need one runner entry per kind, or keep `Command`.
- Migration: existing tasks keep working unchanged. `init_project.py` proposes `test_runners` from the detected stack (pytest, npm test, dotnet test, go test) and writes it only with the user's approval.

## Open question for the user

- Accept the target-only model, keep ADR-0002 as is, or accept it only for new projects.
