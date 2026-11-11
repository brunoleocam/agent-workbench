# Harness evals

Deterministic fixtures for the gates, with no external API or paid service. Model behavior (classification, spec quality, review) is not evaluated here.

`python agent-system/scripts/run_evals.py` copies each fixture to a temporary folder, replaces `__PYTHON__` with the current interpreter, runs the steps, and compares the exit code, `contains`, and `not_contains`. A `write` step changes a file (for example, to make a proof stale). A `stamp` step writes the current fingerprint (`check_proofs.py --fingerprint`) into a report's front matter, as the reviewer does. `base` inherits the project from another fixture. The fixtures' TESTs run test files in `checks/`, like a real project; nothing uses `python -c`.

| Fixture | What it proves |
| --- | --- |
| `complete-feature` | a complete M feature passes every gate |
| `ambiguous-spec` | an open question and a REQ without an AC become a warning; `--strict` fails |
| `dependency-cycle` | a cycle, a nonexistent dependency, and a block without a cause fail the plan |
| `proof-fails` | an application failure (FAIL) and an environment failure (ERROR) are kept separate |
| `stale-proof` | code changed after the proof; harness docs do not invalidate it |
| `security-blocking` | HIGH risk requires a review; an open HIGH finding and accepted risk without justification block |
| `criterion-without-test` | an AC without a TEST fails the gate |
| `weak-test-passes-gate` | known limit: a test without an assertion passes the gate; only the Verification Audit catches it |

`test_system.py` also runs `run_evals.py`.
