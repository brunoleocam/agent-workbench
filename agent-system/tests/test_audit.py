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
