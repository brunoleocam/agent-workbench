"""Metrics: subagent tokens read by the hook (numbers only) and the read-only metrics report."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SCRIPTS, opt_in, run, write  # noqa: E402


def claude_hook(payload: dict, project_dir: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in {"CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"}}
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps(payload), text=True, capture_output=True, env=env, check=False, timeout=60)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def events(root: Path) -> list[dict]:
    return [json.loads(line) for line in (root / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def transcript_line(message_id: str, inp: int, out: int, text: str) -> str:
    usage = {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 10, "service_tier": "standard"}
    return json.dumps({"type": "assistant", "message": {"id": message_id, "content": [{"type": "text", "text": text}], "usage": usage}})


def test_hook_records_subagent_tokens_only_as_numbers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "project"
        opt_in(root)
        transcript = write(Path(tmp), "home/projects/x/abc/subagents/agent-1.jsonl", "\n".join([
            json.dumps({"type": "user", "message": {"content": "password=hunter2 please"}}),
            transcript_line("msg_1", 50, 1, "partial"),
            transcript_line("msg_1", 50, 40, "SECRET-ANSWER first message"),  # same id: only the last usage counts
            transcript_line("msg_2", 70, 30, "second message"),
            "{not json",
        ]) + "\n")
        common = {"session_id": "s1", "cwd": str(root), "transcript_path": str(Path(tmp) / "main.jsonl")}
        claude_hook({**common, "hook_event_name": "SubagentStart", "agent_id": "a1", "agent_type": "agent-workbench:implementer"}, root)
        reply = claude_hook({**common, "hook_event_name": "SubagentStop", "agent_id": "a1", "agent_type": "agent-workbench:implementer",
                             "agent_transcript_path": str(transcript), "last_assistant_message": "SECRET-ANSWER"}, root)
        assert reply == {}
        stopped = [item for item in events(root) if item["event"] == "SUBAGENT_STOPPED"][-1]
        assert stopped["tokens"] == {"input": 120, "output": 70, "cache_read": 200, "cache_creation": 20}
        raw = (root / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        assert "SECRET-ANSWER" not in raw and "hunter2" not in raw and "agent-1.jsonl" not in raw

        # Outside a subagents/ folder, missing, or with no usage: no tokens, and the hook still succeeds.
        elsewhere = write(Path(tmp), "home/elsewhere.jsonl", transcript_line("m", 1, 1, "x") + "\n")
        for path in (str(elsewhere), str(Path(tmp) / "home/subagents/missing.jsonl")):
            claude_hook({**common, "hook_event_name": "SubagentStop", "agent_id": "a2", "agent_type": "agent-workbench:tester", "agent_transcript_path": path}, root)
            assert "tokens" not in [item for item in events(root) if item["event"] == "SUBAGENT_STOPPED"][-1]


def stamp(minute: int, second: int = 0) -> str:
    return f"2026-11-12T10:{minute:02d}:{second:02d}+00:00"


def timeline(with_tokens: bool) -> str:
    rows = [
        {"timestamp": stamp(0), "session": "s1", "agent": "agent-workbench:implementer", "event": "SUBAGENT_STARTED"},
        {"timestamp": stamp(0, 10), "session": "s1", "agent": "agent-workbench:implementer", "event": "SUBAGENT_STOPPED",
         **({"tokens": {"input": 1000, "output": 200, "cache_read": 50, "cache_creation": 5}} if with_tokens else {})},
        {"timestamp": stamp(1), "session": "s1", "agent": "agent-workbench:reviewer", "event": "SUBAGENT_STARTED"},
        {"timestamp": stamp(1, 5), "session": "s1", "agent": "agent-workbench:reviewer", "event": "SUBAGENT_STOPPED"},
        {"timestamp": stamp(2), "session": "s1", "agent": "orchestrator", "event": "VERIFICATION_COMPLETED", "feature": "feat", "result": "failed fail=2 warn=0"},
        {"timestamp": stamp(3), "session": "s1", "agent": "agent-workbench:implementer", "event": "SUBAGENT_STARTED"},
        {"timestamp": stamp(3, 30), "session": "s1", "agent": "agent-workbench:implementer", "event": "SUBAGENT_STOPPED",
         **({"tokens": {"input": 500, "output": 100, "cache_read": 0, "cache_creation": 0}} if with_tokens else {})},
        {"timestamp": stamp(4), "session": "s1", "agent": "orchestrator", "event": "VERIFICATION_COMPLETED", "feature": "feat", "result": "failed fail=1 warn=0"},
        {"timestamp": stamp(5), "session": "s1", "agent": "orchestrator", "event": "AGENT_RESPONSE", "summary": "Agent response (120 chars)"},
        {"timestamp": stamp(6), "session": "s1", "agent": "orchestrator", "event": "VERIFICATION_COMPLETED", "feature": "feat", "result": "passed"},
        {"timestamp": stamp(7), "session": "s1", "agent": "orchestrator", "event": "VERIFICATION_COMPLETED", "feature": "other", "result": "failed fail=1 warn=0"},
    ]
    return "\n".join([json.dumps(row) for row in rows] + ["{broken", "[1, 2]"]) + "\n"


def digest(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.rglob("*")) if path.is_file()}


def report(root: Path, *args: str) -> dict:
    done = run("metrics.py", ["--root", str(root), "--json", *args])
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def test_report_per_agent_and_feature_is_read_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        opt_in(root)
        write(root, ".cursor/timeline/events.jsonl", timeline(with_tokens=False))
        before = digest(root)
        data = report(root)
        implementer = data["agents"]["implementer"]
        assert implementer["runs"] == 2
        assert implementer["duration_s_total"] == 40.0 and implementer["duration_s_median"] == 20.0
        assert data["agents"]["reviewer"]["runs"] == 1 and data["agents"]["reviewer"]["duration_s_total"] == 5.0
        assert data["agents"]["orchestrator"]["response_chars"] == 120
        assert data["features"]["feat"] == {"gates": 3, "gates_failed": 2, "revisions_to_pass": 2, "passed": True}
        assert data["features"]["other"]["passed"] is False
        assert data["skipped"] == 2
        assert data["tokens"] == "unavailable" and implementer["tokens"] == "unavailable"
        text = run("metrics.py", ["--root", str(root)])
        assert "tokens: unavailable" in text.stdout and "revisions to pass 2" in text.stdout
        assert digest(root) == before

        only = report(root, "--feature", "feat")
        assert set(only["features"]) == {"feat"}
        assert "reviewer" not in only["agents"] and only["agents"]["implementer"]["runs"] == 1  # only runs inside feat's span (10:02 to 10:06)
        assert report(root, "--since", "2026-11-12T10:06:30+00:00")["features"] == {"other": {"gates": 1, "gates_failed": 1, "revisions_to_pass": 1, "passed": False}}
        assert run("metrics.py", ["--root", str(root), "--since", "yesterday"]).returncode == 2


def test_report_sums_tokens_when_present() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        opt_in(root)
        write(root, ".cursor/timeline/events.jsonl", timeline(with_tokens=True))
        data = report(root)
        assert data["tokens"] == "available"
        assert data["agents"]["implementer"]["tokens"] == {"input": 1500, "output": 300, "cache_read": 50, "cache_creation": 5, "total": 1855}
        assert data["agents"]["reviewer"]["tokens"] == "unavailable"
        empty = Path(tmp) / "fresh"
        empty.mkdir()
        assert run("metrics.py", ["--root", str(empty)]).stdout.strip() == "No timeline yet."
