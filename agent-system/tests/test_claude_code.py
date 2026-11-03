"""Claude Code support: manifests, hook payload adapter, and the CLAUDE.md block written by the init."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SCRIPTS, SYSTEM, opt_in, run, write  # noqa: E402

PLUGIN = SYSTEM.parent
HOOK = SCRIPTS / "hook.py"
BEGIN = "<!-- agent-workbench:begin"
END = "<!-- agent-workbench:end -->"


def claude_hook(payload: dict, project_dir: str | None = None) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in {"CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"}}
    if project_dir:
        env["CLAUDE_PROJECT_DIR"] = project_dir
    done = subprocess.run([PYTHON, str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, check=False, env=env)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def events(root: Path) -> list[dict]:
    path = root / ".cursor" / "timeline" / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_claude_manifests() -> None:
    cursor = json.loads((PLUGIN / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert claude["name"] == cursor["name"] == "agent-workbench"
    assert claude["version"] == cursor["version"]
    assert claude["hooks"] == "./hooks/claude-hooks.json"
    market = json.loads((PLUGIN / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    entry = market["plugins"][0]
    assert entry["name"] == claude["name"] and entry["source"] == "./"

    hooks = json.loads((PLUGIN / "hooks" / "claude-hooks.json").read_text(encoding="utf-8"))["hooks"]
    for name in ("SessionStart", "SessionEnd", "SubagentStart", "SubagentStop", "PostToolUse", "PostToolUseFailure", "Stop"):
        assert name in hooks, name
        for group in hooks[name]:
            for handler in group["hooks"]:
                assert handler["type"] == "command"
                assert '"${CLAUDE_PLUGIN_ROOT}/agent-system/scripts/hook.py"' in handler["command"]

    # One agents/ folder serves both hosts, so model must be a value both accept.
    for path in (PLUGIN / "agents").glob("*.md"):
        header = path.read_text(encoding="utf-8").split("---")[1]
        models = [line.split(":", 1)[1].strip() for line in header.splitlines() if line.startswith("model:")]
        assert all(model == "inherit" for model in models), (path.name, models)


def test_claude_hook_adapter() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        opt_in(root)
        # A Cursor-only project hook must not silence the plugin hook under Claude Code.
        write(root, ".cursor/hooks.json", '{"version":1,"hooks":{"stop":[{"command":"python .cursor/agent-system/scripts/hook.py"}]}}')
        write(root, "docs/progress/ROADMAP.md", "# Roadmap\n\n> Você está aqui: Fase 1 · TASK-001\n\n- [~] TASK-001 Modelo\n- [ ] TASK-002 API\n")
        common = {"session_id": "sess-1", "cwd": str(root / "src"), "transcript_path": "/tmp/t.jsonl"}

        started = claude_hook({**common, "hook_event_name": "SessionStart", "source": "startup"}, str(root))
        context = started["hookSpecificOutput"]
        assert context["hookEventName"] == "SessionStart"
        assert "Fase 1 · TASK-001 | 0/2 feitas, 1 em andamento" in context["additionalContext"]
        assert "additional_context" not in started

        edit = {**common, "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(root / ".env"), "content": "API_KEY=secret"}, "tool_response": {"success": True}}
        assert claude_hook(edit, str(root)) == {}
        bash = {
            **common,
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest tests --token=abc123secretvalue"},
            "tool_response": {"stdout": "2 failed, 5 passed", "stderr": "", "interrupted": False},
        }
        assert claude_hook(bash, str(root)) == {}
        assert claude_hook({**common, "hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": "x"}}, str(root)) == {}
        assert claude_hook({**common, "hook_event_name": "SubagentStart", "agent_id": "a1", "agent_type": "agent-workbench:planner"}, str(root)) == {}
        assert claude_hook({**common, "hook_event_name": "SubagentStop", "agent_id": "a1", "agent_type": "agent-workbench:planner", "last_assistant_message": "password=hunter2"}, str(root)) == {}
        assert claude_hook({**common, "hook_event_name": "PostToolUseFailure", "tool_name": "Bash", "error": "boom"}, str(root)) == {}
        assert claude_hook({**common, "hook_event_name": "Stop", "last_assistant_message": "token=super-secret-value"}, str(root)) == {}
        assert claude_hook({**common, "hook_event_name": "SessionEnd", "reason": "prompt_input_exit"}, str(root)) == {}

        logged = events(root)
        kinds = [item["event"] for item in logged]
        assert kinds == [
            "SESSION_STARTED",
            "FILE_EDIT",
            "TEST_FAILED",
            "SUBAGENT_STARTED",
            "SUBAGENT_STOPPED",
            "TOOL_FAILURE",
            "AGENT_RESPONSE",
            "SESSION_ENDED",
        ], kinds
        assert all(item["session"] == "sess-1" for item in logged)
        assert logged[3]["agent"] == "agent-workbench:planner"
        assert logged[-1]["result"] == "prompt_input_exit"
        text = (root / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        for secret in ("API_KEY", "abc123secretvalue", "hunter2", "super-secret-value"):
            assert secret not in text, secret
        assert "[redacted-path]" in text
        state = json.loads((root / ".cursor" / "agent-system" / "state.json").read_text(encoding="utf-8"))
        assert state["active_agent"] == "orchestrator"
        assert state["session_id"] == "sess-1"

        # Without CLAUDE_PROJECT_DIR the payload cwd is the root; a project that never ran the init is left alone.
        assert claude_hook({**common, "cwd": str(root), "hook_event_name": "Stop"}) == {}
        assert len(events(root)) == len(logged) + 1
        other = Path(tempfile.mkdtemp())
        assert claude_hook({**common, "cwd": str(other), "hook_event_name": "SessionStart"}) == {}
        assert not (other / ".cursor").exists()

        # Cursor payloads keep their own reply shape.
        cursor = subprocess.run(
            [PYTHON, str(HOOK)],
            input=json.dumps({"hook_event_name": "subagentStart", "workspace_roots": [str(other)]}),
            text=True,
            capture_output=True,
            check=False,
        )
        assert json.loads(cursor.stdout) == {"permission": "allow"}


def test_init_claude_md_block() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        first = run("init_project.py", ["--root", str(root), "--claude"])
        assert first.returncode == 0, first.stderr
        report = json.loads(first.stdout)
        assert report["claude_md"] == "created"
        assert report["hooks"] == "plugin hooks (Claude Code)"
        assert not (root / ".cursor" / "hooks.json").exists()
        assert (root / ".cursor" / "agent-system" / "state.json").exists()
        assert (root / ".cursor" / "agent-system" / "scripts" / "check_proofs.py").exists()
        text = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.startswith(BEGIN) and text.rstrip().endswith(END)
        for section in ("### 00 · Princípios", "### 01 · Classificação", "### 05 · Revisão", "### 08 · Segurança"):
            assert section in text, section

        again = json.loads(run("init_project.py", ["--root", str(root), "--claude"]).stdout)
        assert again["claude_md"] == "unchanged"

        # User text around the block survives; edits inside the block are reverted on the next init.
        managed = text.strip()
        path = root / "CLAUDE.md"
        path.write_text("# Meu projeto\n\nRode `npm test`.\n\n" + managed.replace("TDD preferido", "TDD opcional") + "\n\n## Notas\nfim\n", encoding="utf-8")
        refreshed = json.loads(run("init_project.py", ["--root", str(root), "--claude"]).stdout)
        assert refreshed["claude_md"] == "refreshed"
        updated = path.read_text(encoding="utf-8")
        assert updated.startswith("# Meu projeto\n\nRode `npm test`.\n\n" + BEGIN)
        assert updated.endswith(END + "\n\n## Notas\nfim\n")
        assert "TDD preferido" in updated and "TDD opcional" not in updated
        assert updated.count(BEGIN) == 1

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "CLAUDE.md", "# Existente\n\nSem bloco.")
        report = json.loads(run("init_project.py", ["--root", str(root), "--claude"]).stdout)
        assert report["claude_md"] == "appended"
        text = (root / "CLAUDE.md").read_text(encoding="utf-8")
        assert text.startswith("# Existente\n\nSem bloco.\n\n" + BEGIN)

        write(root, "CLAUDE.md", "# Quebrado\n" + BEGIN + " -->\nsem fim\n")
        broken = json.loads(run("init_project.py", ["--root", str(root), "--claude"]).stdout)
        assert broken["claude_md"].startswith("skipped")
        assert (root / "CLAUDE.md").read_text(encoding="utf-8") == "# Quebrado\n" + BEGIN + " -->\nsem fim\n"

    # Cursor init never writes CLAUDE.md.
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        report = json.loads(run("init_project.py", ["--root", str(root)]).stdout)
        assert "claude_md" not in report
        assert not (root / "CLAUDE.md").exists()
        assert (root / ".cursor" / "hooks.json").exists()
