"""Lessons, hook honesty, init compatibility, evals, and wiring."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SCRIPTS, SYSTEM, opt_in, run, write  # noqa: E402

PLUGIN = SYSTEM.parent


def hook(script: Path, payload: dict) -> dict:
    done = subprocess.run([PYTHON, str(script)], input=json.dumps(payload), text=True, capture_output=True, check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def test_lessons_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        assert run("lessons.py", ["--root", str(root), "list"]).returncode == 2
        opt_in(root)
        base = ["--root", str(root), "add", "--category", "testing", "--description", "Assert observable behavior."]
        added = run("lessons.py", [*base, "--title", "Avoid testing implementation details", "--evidence", "TEST-004"])
        assert added.returncode == 0 and "LESSON-001" in added.stdout, added.stderr
        duplicate = run("lessons.py", [*base, "--title", "avoid testing implementation details!"])
        assert duplicate.returncode == 1 and "Duplicate of LESSON-001" in duplicate.stderr
        secret = run("lessons.py", [*base, "--title", "Use the staging key", "--context", "api_key=sk_live_abcdefghijklmnop"])
        assert secret.returncode == 1 and "secret" in secret.stderr
        assert run("lessons.py", [*base, "--title", "Bad category"]).returncode == 0
        assert run("lessons.py", ["--root", str(root), "add", "--category", "nope", "--title", "xxxxx", "--description", "y"]).returncode == 2

        started = hook(SCRIPTS / "hook.py", {"hook_event_name": "sessionStart", "workspace_roots": [str(root)]})
        assert "Confirmed lessons" not in started.get("additional_context", "")
        assert run("lessons.py", ["--root", str(root), "confirm", "--id", "LESSON-001"]).returncode == 0
        assert run("lessons.py", ["--root", str(root), "reject", "--id", "LESSON-002", "--reason", "not general"]).returncode == 0
        assert run("lessons.py", ["--root", str(root), "confirm", "--id", "LESSON-099"]).returncode == 2
        listed = json.loads(run("lessons.py", ["--root", str(root), "list", "--status", "confirmed", "--json"]).stdout)
        assert [item["id"] for item in listed] == ["LESSON-001"] and listed[0]["confirmed_at"]
        started = hook(SCRIPTS / "hook.py", {"hook_event_name": "sessionStart", "workspace_roots": [str(root)]})
        context = started["additional_context"]
        assert "Avoid testing implementation details" in context and "Bad category" not in context
        rendered = (root / ".cursor/agent-system/LESSONS.md").read_text(encoding="utf-8")
        assert "LESSON-001" in rendered and "Bad category" not in rendered.split("## Candidates")[0]
        events = (root / ".cursor/timeline/events.jsonl").read_text(encoding="utf-8")
        assert "LESSON_PROPOSED" in events and "LESSON_CONFIRMED" in events and "sk_live_" not in events
        write(root, ".cursor/agent-system/lessons.json", "{broken")
        assert run("lessons.py", ["--root", str(root), "list"]).returncode == 2



def test_lessons_edited_by_hand_stay_redacted() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        opt_in(root)
        base = ["--root", str(root)]
        assert run("lessons.py", [*base, "add", "--category", "testing", "--title", "Run proofs before review", "--description", "Stale proofs fail the gate."]).returncode == 0
        path = root / ".cursor/agent-system/lessons.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["lessons"][0]["description"] = "use password=hunter2 for the fixture"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert run("lessons.py", [*base, "confirm", "--id", "LESSON-001"]).returncode == 1
        for flags in (["--json"], ["--verbose"]):
            assert "hunter2" not in run("lessons.py", [*base, "list", *flags]).stdout
        evidence_only = json.loads(json.dumps(data))
        evidence_only["lessons"][0].update(description="Stale proofs fail the gate.", evidence=["password=hunter2"])
        path.write_text(json.dumps(evidence_only), encoding="utf-8")
        assert run("lessons.py", [*base, "confirm", "--id", "LESSON-001"]).returncode == 1
        path.write_text(json.dumps(data), encoding="utf-8")
        assert run("lessons.py", [*base, "render"]).returncode == 0
        data["lessons"][0]["status"] = "confirmed"
        path.write_text(json.dumps(data), encoding="utf-8")
        assert run("lessons.py", [*base, "render"]).returncode == 0
        assert "hunter2" not in (root / ".cursor/agent-system/LESSONS.md").read_text(encoding="utf-8")


def test_hook_marks_inferred_and_redacts() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        opt_in(root)
        base = {"hook_event_name": "afterShellExecution", "workspace_roots": [str(root)]}
        hook(SCRIPTS / "hook.py", {**base, "command": "pytest --token sekret-value-123 -q", "output": "1 failed"})
        hook(SCRIPTS / "hook.py", {**base, "command": "python .cursor/agent-system/scripts/check_proofs.py --feature x", "output": "pytest 1 failed"})
        hook(SCRIPTS / "hook.py", {**base, "command": "mvn test -Ddb.url=https://admin:hunter2@db.local", "output": "BUILD SUCCESS"})
        events = [json.loads(line) for line in (root / ".cursor/timeline/events.jsonl").read_text(encoding="utf-8").splitlines()]
        assert len(events) == 2, events
        assert all(item["inferred"] is True for item in events)
        assert events[0]["event"] == "TEST_FAILED" and events[0]["result"].startswith("inferred from output")
        text = json.dumps(events)
        assert "sekret-value-123" not in text and "hunter2" not in text
        sys.path.insert(0, str(SCRIPTS))
        from lib import redact

        for line in ('curl -H "Authorization: Bearer abcdef123456opaque" https://x', "npm test -- --header 'Authorization: Basic dXNlcjpwYXNzd29yZA=='", "Bearer abcdef123456opaque"):
            masked = redact(line)
            assert "abcdef123456opaque" not in masked and "dXNlcjpwYXNzd29yZA" not in masked, masked
        assert redact("token validation failed") == "token validation failed"
        for line in ("curl -u admin:s3nhaSecreta https://x", "curl --user=admin:s3nhaSecreta https://x"):
            assert "s3nhaSecreta" not in redact(line) and "admin" in redact(line), redact(line)
        assert redact("python -u tests/run.py") == "python -u tests/run.py"
        assert hook(SCRIPTS / "hook.py", {"hook_event_name": "subagentStart", "workspace_roots": ["\0bad"]}) == {"permission": "allow"}


def test_init_stack_detection_migration_and_cloud() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "api/pyproject.toml", '[project]\ndependencies = ["fastapi>=0.110"]\n')
        write(root, "web/package.json", '{"dependencies": {"express": "^4.19.0"}}')
        write(root, "composer.json", '{"require": {"php": "^8.2", "laravel/framework": "^11.0"}}')
        write(root, "svc/Api.csproj", '<Project Sdk="Microsoft.NET.Sdk.Web"></Project>')
        write(root, "pom.xml", "<artifactId>spring-boot-starter-web</artifactId>")
        write(root, "src/uploads/handler.py", "")
        write(root, "src/payments/stripe_client.py", "")
        write(root, "src/auth/login.py", "")
        write(root, "docs/tests/strategy.md", "# strategy\n")
        write(root, ".cursor/agent-system/state.json", json.dumps({"version": 1, "phase": "review", "next_step": "keep me"}))
        write(root, ".cursor/agent-system/layout.json", json.dumps({"version": 1, "overrides": {"specs_dir": "product/specs"}, "proof_allow": ["bats"]}))
        done = run("init_project.py", ["--root", str(root)])
        assert done.returncode == 0, done.stderr
        report = json.loads(done.stdout)
        assert {"fastapi", "express", "laravel", "aspnetcore", "spring"} <= set(report["layout"]["frameworks"])
        assert "python-fastapi-security.md" in report["layout"]["security_references"]
        assert "java-spring-security.md" in report["layout"]["security_references"]
        layout = json.loads((root / ".cursor/agent-system/layout.json").read_text(encoding="utf-8"))
        assert layout["overrides"] == {"specs_dir": "product/specs"} and layout["proof_allow"] == ["bats"]
        assert layout["tests_dir"] == "docs/tests"
        surfaces = layout["signals"]["attack_surfaces"]
        assert {"authentication", "file_upload", "payments"} <= set(surfaces)
        state = json.loads((root / ".cursor/agent-system/state.json").read_text(encoding="utf-8"))
        assert state["phase"] == "review" and state["next_step"] == "keep me" and state["verification"] == {}
        assert "verification" in report["migrated_state_keys"]
        suggestions = (root / ".cursor/agent-system/SUGGESTIONS.md").read_text(encoding="utf-8")
        assert "Sensitive surfaces" in suggestions
        for name in ("validate_spec.py", "check_proofs.py", "validate_verification.py", "lessons.py", "artifacts.py"):
            assert (root / ".cursor/agent-system/scripts" / name).exists(), name
        copied = root / ".cursor/agent-system/scripts"
        write(root, "docs/specs/x.md", "---\nstatus: draft\n---\n## Requirements\n### REQ-001: a\nTHE SYSTEM SHALL a.\n## Acceptance Criteria\n### AC-001: a\n- Requirements: REQ-001\nok\n")
        write(root, ".cursor/agent-system/layout.json", json.dumps({**layout, "overrides": {}}))
        from_project = subprocess.run([PYTHON, str(copied / "validate_spec.py"), "--root", str(root), "--feature", "x", "--no-record"], capture_output=True, text=True, check=False)
        assert from_project.returncode == 0, from_project.stdout + from_project.stderr

        assert not (root / ".cursor/rules/08-security-engineering.mdc").exists()
        write(root, ".cursor/agents/reviewer.md", "---\nname: reviewer\ndescription: local\n---\nlocal reviewer\n")
        cloud = run("init_project.py", ["--root", str(root), "--for-cloud"])
        assert cloud.returncode == 0, cloud.stderr
        assert (root / ".cursor/rules/08-security-engineering.mdc").exists()
        assert (root / ".cursor/agents/security-reviewer.md").exists()
        assert "local reviewer" in (root / ".cursor/agents/reviewer.md").read_text(encoding="utf-8")


def test_layout_ignores_code_folders_named_spec_or_tasks() -> None:
    sys.path.insert(0, str(SCRIPTS))
    from artifacts import resolve_layout
    from init_project import discover_layout

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "spec/models/user_spec.rb", "describe User do\nend\n")
        write(root, "lib/tasks/db.rake", "task :seed do\nend\n")
        write(root, "app/tasks/jobs.py", "def run():\n    pass\n")
        layout = discover_layout(root)
        assert layout["specs"] == [] and layout["tasks_dir"] is None, layout
        resolved = resolve_layout(root, layout)
        assert resolved["specs_dir"] == "docs/specs" and resolved["tasks_dir"] == "docs/tasks", resolved
        write(root, "design/specs/login.md", "# login\n")
        write(root, "docs/tasks/login.md", "# tasks\n")
        write(root, "a/tasks/notes.md", "# notes\n")
        layout = discover_layout(root)
        assert layout["specs"] == ["design/specs"] and layout["tasks_dir"] == "docs/tasks", layout


def test_deterministic_evals() -> None:
    done = run("run_evals.py", ["--json"])
    assert done.returncode == 0, done.stdout + done.stderr
    results = json.loads(done.stdout)
    assert len(results) >= 8 and all(item["ok"] for item in results)
    assert {item["fixture"] for item in results} >= {"complete-feature", "proof-fails", "stale-proof", "security-blocking", "weak-test-passes-gate"}


def test_registry_and_new_layers_are_wired() -> None:
    registry = json.loads((SYSTEM / "agents.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in registry["agents"]]
    assert "security-reviewer" in names
    orchestrator = (PLUGIN / "agents/orchestrator.md").read_text(encoding="utf-8")
    for needle in ("security-reviewer", "validate_verification.py", "security_risk"):
        assert needle in orchestrator, needle
    planner = (PLUGIN / "agents/planner.md").read_text(encoding="utf-8")
    assert "EARS" in planner and "validate_spec.py" in planner
    assert "EARS" in (PLUGIN / "rules/02-spec-driven-development.mdc").read_text(encoding="utf-8")
    reviewer = (PLUGIN / "agents/reviewer.md").read_text(encoding="utf-8")
    assert "Verification Audit" in reviewer
    assert "Verification Audit" in (PLUGIN / "skills/code-review/SKILL.md").read_text(encoding="utf-8")
    tester = (PLUGIN / "agents/tester.md").read_text(encoding="utf-8")
    assert "check_proofs.py" in tester and "Expected result" in tester
    rule = (PLUGIN / "rules/08-security-engineering.mdc").read_text(encoding="utf-8")
    assert rule.startswith("---") and "alwaysApply: false" in rule
    for skill in ("security-best-practices", "security-review", "lessons"):
        text = (PLUGIN / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---") and f"name: {skill}" in text, skill
    refs = sorted((PLUGIN / "skills/security-best-practices/references").glob("*.md"))
    assert len(refs) >= 10
    for ref in refs:
        body = ref.read_text(encoding="utf-8")
        assert "Last reviewed:" in body and "## Sources" in body and "https://" in body, ref.name
    contracts = (SYSTEM / "docs/contracts.md").read_text(encoding="utf-8")
    for name in names:
        assert f"### {name}" in contracts, name
        assert "contracts.md" in (PLUGIN / "agents" / f"{name}.md").read_text(encoding="utf-8"), name
    manifest = json.loads((PLUGIN / ".cursor-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.5.0"
    for readme in ("README.md", "README.pt-BR.md"):
        assert f"version-{manifest['version']}-" in (PLUGIN / readme).read_text(encoding="utf-8"), readme


def test_readmes_cite_only_existing_commands_and_scripts() -> None:
    skills = {path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md")}
    scripts = {path.name for path in (SYSTEM / "scripts").glob("*.py")}
    for readme in (PLUGIN / "README.md", PLUGIN / "README.pt-BR.md", SYSTEM / "README.md"):
        text = readme.read_text(encoding="utf-8")
        for command in set(re.findall(r"`/(?:agent-workbench:)?([a-z][a-z0-9-]+)", text)) - {"nome", "plugin", "reload-plugins", "agent-workbench"}:
            assert command in skills, f"{readme.name}: /{command}"
        for script in set(re.findall(r"\b([a-z_]+\.py)\b", text)):
            assert script in scripts, f"{readme.name}: {script}"


def test_new_semantic_events_update_state() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        opt_in(root)
        for event in ("SPEC_VALIDATION_COMPLETED", "PROOF_EXECUTION_COMPLETED", "SECURITY_REVIEW_COMPLETED", "VERIFICATION_COMPLETED", "LESSON_PROPOSED"):
            done = run("record_event.py", ["--root", str(root), "--event", event, "--summary", "demo", "--feature", "demo", "--result", "passed"])
            assert done.returncode == 0, event + done.stderr
        state = json.loads((root / ".cursor/agent-system/state.json").read_text(encoding="utf-8"))
        entry = state["verification"]["demo"]
        assert entry["spec"] == entry["gate"] == entry["security"] == "passed"
        assert state["phase"] == "verified" and state["version"] == 1 and state["active_agent"] == "orchestrator"
        timeline = root / ".cursor/timeline/events.jsonl"
        legacy = {"timestamp": "2026-01-01T00:00:00+00:00", "event": "NOTE", "summary": "password=hunter2 used", "files": [".env"], "result": "ok"}
        timeline.write_text(timeline.read_text(encoding="utf-8") + json.dumps(legacy) + "\nnot json\n", encoding="utf-8")
        view = run("timeline_view.py", ["--root", str(root), "--write-md"])
        assert view.returncode == 0 and "hunter2" not in view.stdout and "[redacted-path]" in view.stdout, view.stdout + view.stderr
        assert "hunter2" not in (root / ".cursor/timeline/TIMELINE.md").read_text(encoding="utf-8")
