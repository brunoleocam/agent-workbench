"""Fixtures for the agent-system tests. Every project lives in a temporary directory."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
SCRIPTS = SYSTEM / "scripts"
PYTHON = sys.executable


def run(script: str, args: list[str], cwd: Path | None = None, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script), *args],
        input=stdin,
        text=True,
        capture_output=True,
        cwd=cwd,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def opt_in(root: Path) -> None:
    write(root, ".cursor/agent-system/state.json", json.dumps({"version": 1, "active_agent": "orchestrator", "phase": "idle"}))


def py_command(code: str) -> str:
    """A TEST Command as a JSON list, so the interpreter path never depends on PATH or shell quoting."""
    return json.dumps([PYTHON, "-c", code])


SPEC = """---
status: approved
complexity: M
security_risk: LOW
---
# Spec: reset

## Requirements

### REQ-001: Reset token
WHEN the user requests a password reset THE SYSTEM SHALL generate a unique token valid for 15 minutes.

### REQ-002: Audit
THE SYSTEM SHALL log the reset request without the token.

## Acceptance Criteria

### AC-001: Token expires
- Requirements: REQ-001
Given a token When 15 minutes pass Then it is rejected.

### AC-002: Audit line
- Requirements: REQ-002
Given a reset When it is logged Then the log has no token.

## Assumptions

- Clock is UTC.

## Open Questions

- [x] Token length: 32 bytes.
"""


def tasks(status1: str = "todo", status2: str = "todo", cmd1: str | None = None, cmd2: str | None = None) -> str:
    cmd1 = cmd1 or py_command("raise SystemExit(0)")
    cmd2 = cmd2 or py_command("raise SystemExit(0)")
    return f"""# Tasks: reset

### TASK-001: Generate token
- Requirements: REQ-001
- Acceptance: AC-001
- Files: src/reset.py
- Depends on: none
- Verification: TEST-001
- Done when: TEST-001 passes
- Gate: check_proofs TEST-001
- Status: {status1}

### TASK-002: Audit log
- Requirements: REQ-002
- Acceptance: AC-002
- Depends on: TASK-001
- Verification: TEST-002
- Done when: TEST-002 passes
- Gate: check_proofs TEST-002
- Status: {status2}

## Checks

### TEST-001: token expires
- Acceptance: AC-001
- Task: TASK-001
- Command: {cmd1}
- Timeout: 60

### TEST-002: audit has no token
- Acceptance: AC-002
- Task: TASK-002
- Command: {cmd2}
"""


REVIEW_PASS = """---
status: PASS
reviewer: reviewer
---
# Review: reset

## Verification Audit

TEST-001 fails if the expiry is removed.

### FIND-001: naming
- Severity: minor
- Status: resolved
"""


def feature_project(root: Path, **kwargs) -> Path:
    write(root, "docs/specs/reset.md", SPEC)
    write(root, "docs/tasks/reset.md", tasks(**kwargs))
    write(root, "src/reset.py", "TOKEN_TTL = 15\n")
    return root
