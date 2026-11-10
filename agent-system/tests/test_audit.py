"""Consistency and robustness checks added after the repository audit."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
from pathlib import Path

SYSTEM = Path(__file__).resolve().parents[1]
PLUGIN = SYSTEM.parent
sys.path.insert(0, str(SYSTEM / "scripts"))

import hook  # noqa: E402
import init_project  # noqa: E402
import lib  # noqa: E402


def frontmatter(path: Path) -> dict:
    parts = path.read_text(encoding="utf-8").split("---")
    fields = {}
    for line in parts[1].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_registry_matches_agent_files() -> None:
    registry = {item["name"] for item in json.loads((SYSTEM / "agents.json").read_text(encoding="utf-8"))["agents"]}
    files = {path.stem for path in (PLUGIN / "agents").glob("*.md")}
    assert registry == files, (registry ^ files)
    for path in (PLUGIN / "agents").glob("*.md"):
        assert frontmatter(path)["name"] == path.stem, path.name


def test_init_skill_list_matches_skills_folder() -> None:
    folders = sorted(path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md"))
    assert init_project.SKILLS == folders
    for name in folders:
        assert frontmatter(PLUGIN / "skills" / name / "SKILL.md")["name"] == name


def test_readme_names_both_hook_files() -> None:
    text = (SYSTEM / "README.md").read_text(encoding="utf-8")
    assert "hooks/hooks.json" in text and "hooks/claude-hooks.json" in text


def test_reviewers_cannot_edit_code() -> None:
    for name in ("reviewer", "security-reviewer"):
        tools = {item.strip() for item in frontmatter(PLUGIN / "agents" / f"{name}.md")["tools"].split(",")}
        assert tools and not tools & {"Edit", "MultiEdit", "NotebookEdit"}, (name, tools)


def test_failure_detection_uses_summaries_not_log_noise() -> None:
    failing = [
        "1 failed, 5 passed in 0.3s",
        "Tests: 2 failed, 8 passed",
        "FAILED tests/test_a.py::test_x - assert 1 == 2",
        "--- FAIL: TestThing (0.00s)",
        "not ok 3 - handles empty input",
        "Failed!  - Failed:     1, Passed:    10",
        "[ERROR] BUILD FAILURE",
        "ran 4 tests, errors=2",
    ]
    passing = [
        "5 passed in 0.3s",
        "0 failed, 5 passed",
        "failed=0",
        "WARNING error: retrying connection (expected in this test)",
        "logged 'request failed' and recovered; all tests passed",
        "BUILD SUCCESS",
        "",
    ]
    for text in failing:
        assert hook.re_failed(text), text
    for text in passing:
        assert not hook.re_failed(text), text


def test_append_event_is_one_line_per_event_under_concurrency() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        threads = [threading.Thread(target=lambda n=n: [lib.append_event(root, {"event": "X", "n": n, "i": i}) for i in range(25)]) for n in range(8)]
        for item in threads:
            item.start()
        for item in threads:
            item.join()
        lines = (root / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 200
        assert all(json.loads(line)["event"] == "X" for line in lines)


def test_file_lock_serializes_and_recovers_from_stale_lock() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "agg.json"
        with lib.file_lock(target) as first:
            assert first is True
            with lib.file_lock(target, timeout=0.1) as second:
                assert second is False  # fails open instead of blocking
        assert not target.with_name("agg.json.lock").exists()
        stale = target.with_name("agg.json.lock")
        stale.write_text("", encoding="utf-8")
        old = stale.stat().st_mtime - lib.LOCK_STALE_S - 5
        import os

        os.utime(stale, (old, old))
        with lib.file_lock(target) as held:
            assert held is True


def test_duplicate_edit_filter_survives_corrupt_state_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        agg = root / ".cursor" / "agent-system" / "agg.json"
        agg.parent.mkdir(parents=True)
        agg.write_text("{not json", encoding="utf-8")
        assert lib.should_skip_duplicate_edit(root, "a.py") is False
        assert lib.should_skip_duplicate_edit(root, "a.py") is True


def test_roadmap_position_accepts_english_and_portuguese_markers() -> None:
    for marker in ("You are here:", "Você está aqui:"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / lib.ROADMAP_REL
            path.parent.mkdir(parents=True)
            path.write_text(f"# Roadmap\n\n> {marker} Phase 1 · TASK-001\n\n- [x] TASK-001 A\n- [ ] TASK-002 B\n", encoding="utf-8")
            assert lib.roadmap_summary(root) == "Phase 1 · TASK-001 | 1/2 done", marker


# Agent Skills specification (https://agentskills.io/specification, also in anthropics/skills).
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
# Claude Code extension that this plugin uses on purpose; any other unknown field is a typo.
HOST_FIELDS = {"disable-model-invocation"}
SKILL_NAME = __import__("re").compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LINK = __import__("re").compile(r"\]\((?!https?:|#|mailto:)([^)#\s]+)")


def test_skills_follow_the_agent_skills_specification() -> None:
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert skills
    for path in skills:
        folder = path.parent.name
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---"), folder
        header = text.split("---")[1]
        fields = frontmatter(path)
        unknown = set(fields) - SPEC_FIELDS - HOST_FIELDS
        assert not unknown, (folder, unknown)
        name = fields["name"]
        assert name == folder, (folder, name)
        assert len(name) <= 64 and SKILL_NAME.fullmatch(name), (folder, name)
        description = fields.get("description", "")
        assert 1 <= len(description) <= 1024, (folder, len(description))
        if "compatibility" in fields:
            assert 1 <= len(fields["compatibility"]) <= 500, folder
        assert "\n---" in text[3:], folder  # frontmatter is closed
        assert len(text.splitlines()) < 500, (folder, "SKILL.md must stay under 500 lines")
        body = text.split("---", 2)[2]
        for target in LINK.findall(body):
            assert (path.parent / target).exists(), (folder, "broken link", target)
        assert header.strip(), folder


def test_security_review_has_a_refutation_pass_and_a_refute_mode() -> None:
    skill = (PLUGIN / "skills/security-review/SKILL.md").read_text(encoding="utf-8")
    assert "## Refutation pass" in skill and "## Rejected Candidates" in skill
    for verdict in ("confirmed", "refuted", "unresolved"):
        assert f"`{verdict}`" in skill, verdict
    agent = (PLUGIN / "agents/security-reviewer.md").read_text(encoding="utf-8")
    assert "mode: refute" in agent and "verdict:" in agent
    assert "mode: refute" in (SYSTEM / "docs/contracts.md").read_text(encoding="utf-8")


def test_smallest_change_ladder_keeps_its_exclusions() -> None:
    for relative in ("rules/00-core-engineering.mdc", "agent-system/templates/CLAUDE.md"):
        text = (PLUGIN / relative).read_text(encoding="utf-8").lower()
        assert "smallest sufficient change" in text, relative
        assert "validation at trust boundaries" in text and "security" in text and "accessibility" in text, relative
    assert "ladder" in (PLUGIN / "agents/implementer.md").read_text(encoding="utf-8")


def test_security_report_with_rejected_candidates_still_parses() -> None:
    import artifacts

    report = """---
status: PASS_WITH_WARNINGS
scope: feat
reviewer: security-reviewer
fingerprint:
---
# Security Assessment
## Medium Findings
### SEC-001: Open question on session cookie flags
- Severity: MEDIUM
- Confidence: low
- Classification: suspected
- Status: open
- Location: src/app.py:10
- Verification: check the proxy sets Secure
## Rejected Candidates
- Claim: SQL injection in src/db.py:20. Stopped by the parameterized query at src/db.py:18 (refuted by a fresh run).
## Recommendations
"""
    frontmatter, blocks, _, _ = artifacts.parse_text(report)
    assert frontmatter["status"] == "PASS_WITH_WARNINGS"
    assert [block.id for block in blocks] == ["SEC-001"]
    assert blocks[0].get("classification") == "suspected" and blocks[0].get("severity") == "MEDIUM"
    assert "Rejected Candidates" not in blocks[0].text
