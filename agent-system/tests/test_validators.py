"""validate_spec, validate_tasks, artifacts parser, and layout resolution."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from support import SPEC, feature_project, run, tasks, write  # noqa: E402

from artifacts import parse_text  # noqa: E402


def test_artifacts_parse_blocks_and_fields() -> None:
    text = "---\nstatus: draft\n---\n# T\n## Requirements\n### REQ-001: One\nWHEN x THE SYSTEM SHALL y\n- **Requisitos:** REQ-009\n```\n### REQ-002: inside a fence\n```\n## Other\n### AC-001 — Crit (REQ-001)\n- Requirements: REQ-001, REQ-003\n- Note: not a field\n"
    meta, blocks, _, _ = parse_text(text)
    assert meta == {"status": "draft"}
    assert [block.id for block in blocks] == ["REQ-001", "AC-001"], blocks
    assert [block.line for block in blocks] == [6, 13], [block.line for block in blocks]
    assert blocks[0].fields["requirements"] == "REQ-009"
    assert "inside a fence" in blocks[0].text
    assert blocks[1].ids("requirements") == ["REQ-001", "REQ-003"]
    assert "Note: not a field" in blocks[1].text


def test_validate_spec_valid() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw))
        done = run("validate_spec.py", ["--root", str(root), "--feature", "reset", "--require-approval"])
        assert done.returncode == 0, done.stdout + done.stderr
        assert "[PASS] Requirement and criterion identifiers are unique." in done.stdout
        data = json.loads(run("validate_spec.py", ["--root", str(root), "--feature", "reset", "--json"]).stdout)
        assert data["ok"] and data["counts"]["requirements"] == 2


def test_validate_spec_failures_and_strict() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        broken = SPEC.replace("### REQ-002: Audit", "### REQ-001: Audit").replace("- Requirements: REQ-002", "- Requirements: REQ-999")
        write(root, "docs/specs/bad.md", broken)
        done = run("validate_spec.py", ["--root", str(root), "--feature", "bad"])
        assert done.returncode == 1
        assert "[FAIL] REQ-001 is defined more than once" in done.stdout
        assert "[FAIL] AC-002 references unknown requirement REQ-999." in done.stdout

        orphan = SPEC.replace("### AC-002: Audit line\n- Requirements: REQ-002\nGiven a reset When it is logged Then the log has no token.\n", "")
        write(root, "docs/specs/orphan.md", orphan)
        loose = run("validate_spec.py", ["--root", str(root), "--feature", "orphan"])
        assert loose.returncode == 0, loose.stdout
        assert "[WARN] REQ-002 has no linked acceptance criterion." in loose.stdout
        strict = run("validate_spec.py", ["--root", str(root), "--feature", "orphan", "--strict"])
        assert strict.returncode == 1

        write(root, "docs/specs/draft.md", SPEC.replace("status: approved", "status: draft").replace("security_risk: LOW", "security_risk: SEVERE"))
        draft = run("validate_spec.py", ["--root", str(root), "--feature", "draft", "--require-approval"])
        assert draft.returncode == 1
        assert "approval is required" in draft.stdout and "Unknown security_risk" in draft.stdout


def test_validate_spec_layout_and_paths() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "product/requirements/reset.md", SPEC)
        write(root, ".cursor/agent-system/layout.json", json.dumps({"specs": ["spec"], "overrides": {"specs_dir": "product/requirements"}}))
        assert run("validate_spec.py", ["--root", str(root), "--feature", "reset"]).returncode == 0
        assert run("validate_spec.py", ["--root", str(root), "--feature", "../reset"]).returncode == 2
        outside = run("validate_spec.py", ["--root", str(root), "--spec", "../../etc/passwd"])
        assert outside.returncode == 2 and "outside the project root" in outside.stderr
        assert run("validate_spec.py", ["--root", str(root), "--feature", "missing"]).returncode == 2
        write(root, ".cursor/agent-system/layout.json", "{not json")
        invalid = run("validate_spec.py", ["--root", str(root), "--feature", "reset"])
        assert invalid.returncode == 2 and "Invalid JSON" in invalid.stderr


def test_validate_tasks_valid_and_invalid() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw))
        ok = run("validate_tasks.py", ["--root", str(root), "--feature", "reset"])
        assert ok.returncode == 0, ok.stdout + ok.stderr

        text = tasks()
        text = text.replace("- Acceptance: AC-001\n- Files", "- Files", 1).replace("- Requirements: REQ-001\n", "", 1)
        text = text.replace("- Depends on: TASK-001", "- Depends on: TASK-077")
        write(root, "docs/tasks/reset.md", text)
        bad = run("validate_tasks.py", ["--root", str(root), "--feature", "reset"])
        assert bad.returncode == 1
        assert "TASK-001 references no requirement or acceptance criterion." in bad.stdout
        assert "TASK-002 depends on unknown task TASK-077." in bad.stdout

        cycle = tasks().replace("- Depends on: none", "- Depends on: TASK-002")
        write(root, "docs/tasks/reset.md", cycle)
        looped = run("validate_tasks.py", ["--root", str(root), "--feature", "reset"])
        assert looped.returncode == 1 and "Circular dependency: TASK-001 -> TASK-002 -> TASK-001." in looped.stdout

        blocked = tasks(status1="blocked")
        write(root, "docs/tasks/reset.md", blocked)
        assert "TASK-001 is blocked without a dependency" in run("validate_tasks.py", ["--root", str(root), "--feature", "reset"]).stdout

        done = tasks(status1="done")
        write(root, "docs/tasks/reset.md", done)
        unproven = run("validate_tasks.py", ["--root", str(root), "--feature", "reset"])
        assert unproven.returncode == 1 and "TASK-001 is done without a passing proof for TEST-001." in unproven.stdout

        no_check = tasks().replace("- Verification: TEST-002\n- Done when: TEST-002 passes\n", "").replace("- Task: TASK-002\n", "")
        write(root, "docs/tasks/reset.md", no_check)
        missing = run("validate_tasks.py", ["--root", str(root), "--feature", "reset"])
        assert "TASK-002 has no verification." in missing.stdout and "TASK-002 has no completion criterion" in missing.stdout


def test_validate_tasks_duplicate_and_done_without_evidence() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw))
        extra = "\n### TASK-003: docs only\n- Requirements: REQ-001\n- Acceptance: AC-001\n- Done when: README updated\n- Status: done\n"
        extra += "\n### TASK-001: duplicated\n- Requirements: REQ-001\n- Acceptance: AC-001\n- Verification: TEST-001\n- Done when: x\n- Status: todo\n"
        write(root, "docs/tasks/reset.md", tasks().replace("## Checks", extra + "\n## Checks"))
        done = run("validate_tasks.py", ["--root", str(root), "--feature", "reset", "--json", "--no-record"])
        assert done.returncode == 1, done.stdout
        assert "duplicate-id" in done.stdout and "task-done-no-evidence" in done.stdout, done.stdout
        write(root, "docs/tasks/reset.md", tasks().replace("## Checks", extra.split("\n### TASK-001")[0].replace("- Status: done", "- Status: done\n- Evidence: README diff reviewed") + "\n## Checks"))
        fixed = run("validate_tasks.py", ["--root", str(root), "--feature", "reset", "--json", "--no-record"])
        assert "task-done-no-evidence" not in fixed.stdout and "duplicate-id" not in fixed.stdout, fixed.stdout
