"""Validates the agent system and simulates greenfield, feature, bugfix, and change request."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BASE_DIR = ROOT.parent
PYTHON = sys.executable


def run(script: str, args: list[str], stdin: str = "", cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(SCRIPTS / script), *args],
        input=stdin,
        text=True,
        capture_output=True,
        cwd=cwd,
        check=False,
    )


def hook_at(script: Path, payload: dict) -> dict:
    result = subprocess.run(
        [PYTHON, str(script)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_static() -> None:
    hooks = json.loads((BASE_DIR / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert hooks["version"] == 1
    for name in (
        "workspaceOpen",
        "sessionStart",
        "sessionEnd",
        "subagentStart",
        "subagentStop",
        "afterFileEdit",
        "postToolUseFailure",
        "afterShellExecution",
        "afterAgentResponse",
        "stop",
    ):
        assert name in hooks["hooks"]
    registry = json.loads((ROOT / "agents.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in registry["agents"]]
    assert names == ["orchestrator", "planner", "implementer", "tester", "reviewer", "debugger"]
    for name in names:
        text = (BASE_DIR / "agents" / f"{name}.md").read_text(encoding="utf-8")
        assert text.startswith("---")
        assert f"name: {name}" in text
    for rule in (
        "00-core-engineering.mdc",
        "01-request-classification.mdc",
        "02-spec-driven-development.mdc",
        "03-testing-and-evals.mdc",
        "04-change-management.mdc",
        "05-code-review.mdc",
        "06-checkpoint-and-progress.mdc",
        "07-documentation.mdc",
    ):
        text = (BASE_DIR / "rules" / rule).read_text(encoding="utf-8")
        assert text.startswith("---")
        assert "alwaysApply:" in text


def test_workflows() -> None:
    with tempfile.TemporaryDirectory() as raw:
        project = Path(raw)
        home = run("init_project.py", ["--root", str(Path.home())])
        assert home.returncode == 2

        (project / ".cursor" / "rules").mkdir(parents=True)
        (project / ".cursor" / "rules" / "local.mdc").write_text("---\nalwaysApply: false\n---\n# local\n", encoding="utf-8")
        (project / ".cursor" / "skills" / "feature").mkdir(parents=True)
        (project / ".cursor" / "skills" / "feature" / "SKILL.md").write_text("---\nname: feature\ndescription: local\n---\n# local feature\n", encoding="utf-8")
        (project / ".cursor" / "hooks.json").write_text('{"version":1,"hooks":{"stop":[{"command":"python existing.py"}]}}\n', encoding="utf-8")
        (project / "product").mkdir()
        (project / "product" / "PDR.md").write_text("# Checkout\n", encoding="utf-8")
        (project / "decisions").mkdir()
        (project / "decisions" / "0001-auth.md").write_text("# Auth\n", encoding="utf-8")
        (project / "package.json").write_text('{"dependencies":{"react":"1.0.0"}}', encoding="utf-8")
        (project / "src").mkdir()
        (project / "src" / "App.tsx").write_text("export {}", encoding="utf-8")

        installed = run("init_project.py", ["--root", str(project)])
        assert installed.returncode == 0, installed.stderr
        report = json.loads(installed.stdout)
        assert "local.mdc" in report["detected"]["rules"]
        assert (project / ".cursor" / "rules" / "local.mdc").read_text(encoding="utf-8").startswith("---")
        assert "local feature" in (project / ".cursor" / "skills" / "feature" / "SKILL.md").read_text(encoding="utf-8")
        assert not (project / ".cursor" / "rules" / "01-request-classification.mdc").exists()
        assert not (project / ".cursor" / "agents" / "planner.md").exists()
        cloud = run("init_project.py", ["--root", str(project), "--for-cloud"])
        assert cloud.returncode == 0, cloud.stderr
        assert (project / ".cursor" / "rules" / "01-request-classification.mdc").exists()
        assert (project / ".cursor" / "agents" / "planner.md").exists()
        assert not (project / ".cursor" / "skills" / "init-agent-system").exists()
        assert "init-agent-system" in report["global_skills"]
        assert (project / "product" / "PDR.md").exists()
        assert not (project / "docs" / "product" / "PRD.md").exists()
        layout = json.loads((project / ".cursor" / "agent-system" / "layout.json").read_text(encoding="utf-8"))
        assert "product/PDR.md" in layout["prd"]
        assert "decisions" in layout["adr_dirs"]
        assert "decisions/0001-auth.md" in layout["adr_files"]
        assert "node" in layout["stack"]
        assert report["layout"]["adr_files"] == 1
        suggestions = (project / ".cursor" / "agent-system" / "SUGGESTIONS.md").read_text(encoding="utf-8")
        assert "frontend-reviewer" in suggestions
        assert "nenhum teste encontrado" in suggestions
        assert not (project / ".cursor" / "agents" / "frontend-reviewer.md").exists()
        assert "PRD ou PDR já existe" in suggestions
        assert (project / ".cursor" / "rules" / "local.mdc").exists()
        assert "existing.py" in (project / ".cursor" / "hooks.json").read_text(encoding="utf-8")
        assert (project / ".cursor" / "hooks.json.bak-agent-system").exists()

        untouched = Path(tempfile.mkdtemp())
        user_opened = hook_at(SCRIPTS / "hook.py", {"hook_event_name": "workspaceOpen", "workspace_roots": [str(untouched)]})
        assert user_opened == {}
        assert not (untouched / ".cursor").exists()

        (project / "docs" / "progress").mkdir(parents=True)
        (project / "docs" / "progress" / "ROADMAP.md").write_text(
            "# Roadmap\n\n> Você está aqui: Fase 2 — API · TASK-008\n\n"
            "## Fase 1\n- [x] TASK-001 Modelo\n\n## Fase 2\n- [~] TASK-008 Reserva\n- [!] TASK-009 Pagamento\n- [ ] TASK-010 Webhook\n",
            encoding="utf-8",
        )
        project_hook = project / ".cursor" / "agent-system" / "scripts" / "hook.py"
        started = hook_at(
            project_hook,
            {
                "hook_event_name": "sessionStart",
                "workspace_roots": [str(project)],
                "conversation_id": "conv-1",
                "session_id": "conv-1",
            }
        )
        assert "additional_context" in started
        assert "Fase 2 — API · TASK-008 | 1/4 feitas, 1 em andamento, 1 bloqueadas" in started["additional_context"]
        status = run("status_cmd.py", ["--root", str(project)])
        assert status.returncode == 0, status.stderr
        roadmap_line = next(line for line in status.stdout.splitlines() if line.startswith("Roadmap: "))
        assert "TASK-008 | 1/4 feitas, 1 em andamento, 1 bloqueadas" in roadmap_line

        edited = hook_at(
            project_hook,
            {
                "hook_event_name": "afterFileEdit",
                "workspace_roots": [str(project)],
                "conversation_id": "conv-1",
                "file_path": str(project / ".env"),
                "edits": [{"old_string": "API_KEY=secret", "new_string": "API_KEY=other"}],
            }
        )
        assert edited == {}

        allowed = hook_at(
            project_hook,
            {
                "hook_event_name": "subagentStart",
                "workspace_roots": [str(project)],
                "conversation_id": "conv-1",
                "subagent_type": "planner",
                "task": "Write checkout spec",
            }
        )
        assert allowed["permission"] == "allow"

        hook_at(
            project_hook,
            {
                "hook_event_name": "afterShellExecution",
                "workspace_roots": [str(project)],
                "conversation_id": "conv-1",
                "command": "pytest tests/test_checkout.py",
                "output": "2 failed, 27 passed",
            }
        )
        hook_at(
            project_hook,
            {
                "hook_event_name": "afterAgentResponse",
                "workspace_roots": [str(project)],
                "conversation_id": "conv-1",
                "text": "token=super-secret-value should not be stored",
            }
        )

        for args in (
            ["--root", str(project), "--event", "REQUIREMENT_CREATED", "--summary", "Checkout reserves inventory before payment", "--agent", "planner", "--task", "TASK-021"],
            ["--root", str(project), "--event", "SPEC_CREATED", "--summary", "Added checkout validation requirements", "--agent", "planner", "--task", "TASK-012", "--files", "docs/specs/SPEC-012.md"],
            ["--root", str(project), "--event", "CHANGE_REQUEST_CREATED", "--summary", "CR-004 Inventory must be reserved before payment", "--agent", "orchestrator", "--task", "TASK-021"],
            ["--root", str(project), "--event", "TASK_BLOCKED", "--summary", "TASK-021 depends on TASK-022", "--agent", "orchestrator", "--task", "TASK-021"],
            ["--root", str(project), "--event", "CHECKPOINT_CREATED", "--summary", "Next: implement TASK-022 inventory reservation", "--agent", "orchestrator", "--task", "TASK-021"],
        ):
            recorded = run("record_event.py", args)
            assert recorded.returncode == 0, recorded.stderr

        lines = (project / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        assert "super-secret-value" not in lines
        assert "API_KEY" not in lines
        assert "[redacted-path]" in lines
        assert "SPEC_CREATED" in lines
        assert "CHANGE_REQUEST_CREATED" in lines
        assert "TEST_FAILED" in lines
        state = json.loads((project / ".cursor" / "agent-system" / "state.json").read_text(encoding="utf-8"))
        assert "TASK-021" in state["blocked_tasks"]
        assert state["next_step"].startswith("Next:")

        status = run("status_cmd.py", ["--root", str(project)])
        assert status.returncode == 0
        assert "orchestrator" in status.stdout
        view = run("timeline_view.py", ["--root", str(project), "--write-md"])
        assert view.returncode == 0
        assert (project / ".cursor" / "timeline" / "TIMELINE.md").exists()

        conflict = run("create_agent.py", ["check", "--name", "orchestrator"])
        assert conflict.returncode == 2
        builtin = run("create_agent.py", ["check", "--name", "bugbot"])
        assert builtin.returncode == 2


if __name__ == "__main__":
    test_static()
    test_workflows()
    print("ok")
