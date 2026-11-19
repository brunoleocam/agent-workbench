"""Deterministic enforcement: classification floor, skill events, the Claude Code Stop gate, the CI gate, metrics."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SCRIPTS, opt_in, run, write  # noqa: E402

FIXTURE = SCRIPTS.parent / "evals" / "fixtures" / "complete-feature" / "project"


def git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "test")
    git(root, "config", "core.autocrlf", "false")
    write(root, "README.txt", "base\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return root


def events(root: Path) -> list[dict]:
    path = root / ".agent-system" / "timeline" / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def state(root: Path) -> dict:
    return json.loads((root / ".agent-system" / "state.json").read_text(encoding="utf-8"))


def hook(payload: dict, project: Path, env_extra: dict | None = None) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in {"CLAUDE_PROJECT_DIR", "AGENT_WORKBENCH_STOP_GATE"}}
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.update(env_extra or {})
    done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps(payload), text=True, capture_output=True, env=env, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def stop(project: Path, active: bool = False, env_extra: dict | None = None, transcript: str = "") -> dict:
    return hook({"hook_event_name": "Stop", "session_id": "s1", "cwd": str(project), "stop_hook_active": active,
                 "transcript_path": transcript, "last_assistant_message": "done"}, project, env_extra)


def seven_files(root: Path) -> None:
    for index in range(7):
        write(root, f"src/module_{index}.py", f"VALUE = {index}\n")


def failing_feature(root: Path) -> Path:
    """Opted-in git project with an M feature `feat` whose gate fails (proofs never ran)."""
    shutil.copytree(FIXTURE, root)
    for path in root.rglob("*.md"):
        path.write_text(path.read_text(encoding="utf-8").replace("__PYTHON__", PYTHON.replace("\\", "/")), encoding="utf-8")
    repo(root)
    opt_in(root)
    seven_files(root)
    done = run("classify_floor.py", ["--root", str(root), "--feature", "feat", "--declared", "M"])
    assert done.returncode == 0, done.stdout + done.stderr
    return root


def pass_gate(root: Path) -> None:
    assert run("check_proofs.py", ["--root", str(root), "--feature", "feat"]).returncode == 0
    digest = json.loads(run("check_proofs.py", ["--root", str(root), "--fingerprint"]).stdout)["digest"]
    review = root / "docs" / "reviews" / "feat.md"
    lines = [line for line in review.read_text(encoding="utf-8").splitlines() if not line.startswith("fingerprint:")]
    review.write_text("\n".join([lines[0], f"fingerprint: {digest}", *lines[1:]]) + "\n", encoding="utf-8")
    assert run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 0


def test_floor_rejects_declared_below_floor() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        seven_files(root)
        done = run("classify_floor.py", ["--root", str(root), "--declared", "S", "--no-record"])
        assert done.returncode == 1, done.stdout
        assert "floor M" in done.stdout and "7 files" in done.stdout


def test_floor_attack_surface_raises_to_m() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        write(root, "src/auth/login.py", "X = 1\n")
        done = run("classify_floor.py", ["--root", str(root), "--declared", "XS", "--json", "--no-record"])
        assert done.returncode == 1, done.stdout
        data = json.loads(done.stdout)
        assert data["floor"] == "M" and "authentication" in data["measure"]["surfaces"]


def test_floor_small_change_records_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        opt_in(root)
        write(root, "README.txt", "base changed\n")
        done = run("classify_floor.py", ["--root", str(root), "--feature", "f", "--declared", "XS"])
        assert done.returncode == 0, done.stdout
        saved = state(root)["classification"]
        assert saved["feature"] == "f" and saved["effective"] == "XS" and saved["base"] == git(root, "rev-parse", "HEAD")
        assert [event["event"] for event in events(root)] == ["CLASSIFICATION_RECORDED"]


def test_floor_justified_downgrade() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        opt_in(root)
        seven_files(root)
        done = run("classify_floor.py", ["--root", str(root), "--feature", "f", "--declared", "S", "--justification", "generated files"])
        assert done.returncode == 0, done.stdout
        assert "[WARN]" in done.stdout
        last = events(root)[-1]
        assert last["event"] == "CLASSIFICATION_DOWNGRADED" and "generated files" in last["result"]
        assert state(root)["classification"]["effective"] == "S"


def test_floor_without_git_is_unknown() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        write(root, "a.py", "x = 1\n")
        done = run("classify_floor.py", ["--root", str(root), "--declared", "XS", "--no-record"])
        assert done.returncode == 0 and "floor unknown" in done.stdout


def test_skill_events_hold_names_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        opt_in(root)
        common = {"session_id": "s1", "cwd": str(root)}
        assert hook({**common, "hook_event_name": "PostToolUse", "tool_name": "Skill",
                     "tool_input": {"skill": "agent-workbench:tdd", "args": "password=hunter2"}, "tool_response": "ok"}, root) == {}
        assert hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "/agent-workbench:code-review secret text"}, root) == {}
        assert hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "plain question with /path/in/it"}, root) == {}
        assert hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "/not-a-plugin-skill hello"}, root) == {}
        found = [event for event in events(root) if event["event"] == "SKILL_USED"]
        assert [event["summary"] for event in found] == ["tdd", "code-review"]
        raw = (root / ".agent-system" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        assert "hunter2" not in raw and "secret text" not in raw


def test_stop_blocks_while_gate_fails_and_releases_when_it_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        reply = stop(root)
        assert reply.get("decision") == "block", reply
        assert "validate_verification.py --feature feat" in reply["reason"]
        assert events(root)[-1]["event"] == "STOP_GATE_BLOCKED"
        pass_gate(root)
        assert stop(root) == {}


def test_stop_asks_for_classification_once_per_state() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        opt_in(root)
        seven_files(root)
        first = stop(root)
        assert first.get("decision") == "block" and "classify_floor.py" in first["reason"]
        assert stop(root, active=True) == {}
        small = repo(Path(tmp) / "small")
        opt_in(small)
        write(small, "README.txt", "tiny\n")
        assert stop(small) == {}


def test_stop_escalates_without_progress() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        assert stop(root).get("decision") == "block"
        reply = stop(root, active=True)
        assert "decision" not in reply and "systemMessage" in reply
        last = events(root)[-1]
        assert last["event"] == "STOP_GATE_ESCALATED" and last["result"] == "no_progress"


def test_stop_escalates_at_block_limit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        for index in range(3):
            write(root, "src/progress.py", f"STEP = {index}\n")
            assert stop(root, active=index > 0).get("decision") == "block", index
        write(root, "src/progress.py", "STEP = 99\n")
        reply = stop(root, active=True)
        assert "decision" not in reply and "3 times" in reply["systemMessage"]
        assert events(root)[-1]["result"] == "max_blocks"


def test_stop_escalates_at_budget() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        layout = root / ".agent-system" / "layout.json"
        layout.write_text(json.dumps({"overrides": {"stop_gate": {"max_usd_per_feature": 1}}}), encoding="utf-8")
        usage = {"input_tokens": 100_000, "output_tokens": 100_000, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
        transcript = write(Path(tmp), "t/main.jsonl", json.dumps({"type": "assistant", "message": {"id": "m1", "usage": usage}}) + "\n")
        reply = stop(root, transcript=str(transcript))
        assert "decision" not in reply and "budget" in reply["systemMessage"], reply
        assert events(root)[-1]["result"] == "budget"


def test_stop_escape_hatches() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        assert stop(root, env_extra={"AGENT_WORKBENCH_STOP_GATE": "off"}) == {}
        assert run("record_event.py", ["--root", str(root), "--event", "STOP_GATE_WAIVED", "--summary", "user says ship"]).returncode == 2
        assert run("record_event.py", ["--root", str(root), "--event", "STOP_GATE_WAIVED", "--feature", "feat", "--summary", "user says ship"]).returncode == 0
        assert stop(root) == {}


def test_stop_gate_ignores_projects_not_opted_in_and_small_features() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        seven_files(root)
        assert stop(root) == {}
        opt_in(root)
        assert run("classify_floor.py", ["--root", str(root), "--feature", "f", "--declared", "S", "--justification", "vendored"]).returncode == 0
        assert stop(root) == {}


def test_ci_gate_checks_changed_large_features() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        base = git(root, "rev-parse", "HEAD")
        shutil.copytree(FIXTURE / "docs", root / "docs")
        shutil.copytree(FIXTURE / "checks", root / "checks")
        shutil.copytree(FIXTURE / "src", root / "src")
        for path in (root / "docs").rglob("*.md"):
            path.write_text(path.read_text(encoding="utf-8").replace("__PYTHON__", PYTHON.replace("\\", "/")), encoding="utf-8")
        (root / "docs" / "reviews" / "feat.md").unlink()  # no review: the M gate must fail
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "feature")
        done = run("ci_gate.py", ["--root", str(root), "--base", base])
        assert done.returncode == 1 and "feat" in done.stdout, done.stdout + done.stderr
        small = repo(Path(tmp) / "small")
        small_base = git(small, "rev-parse", "HEAD")
        write(small, "docs/specs/tiny.md", "---\nstatus: approved\ncomplexity: S\n---\n# Spec: tiny\n")
        git(small, "add", "-A")
        git(small, "commit", "-q", "-m", "s")
        done = run("ci_gate.py", ["--root", str(small), "--base", small_base])
        assert done.returncode == 0 and "no M+ feature" in done.stdout
        assert run("ci_gate.py", ["--root", str(small)]).returncode == 2


def test_init_with_ci_installs_workflow_once() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        root.mkdir()
        done = run("init_project.py", ["--root", str(root), "--with-ci", "--claude"])
        assert done.returncode == 0, done.stdout + done.stderr
        workflow = root / ".github" / "workflows" / "agent-workbench-gate.yml"
        assert "ci_gate.py" in workflow.read_text(encoding="utf-8")
        for name in ("classify_floor.py", "stop_gate.py", "ci_gate.py"):
            assert (root / ".agent-system" / "scripts" / name).is_file(), name
        workflow.write_text("custom\n", encoding="utf-8")
        assert run("init_project.py", ["--root", str(root), "--with-ci", "--claude"]).returncode == 0
        assert workflow.read_text(encoding="utf-8") == "custom\n"


def test_metrics_report_skills_classifications_and_stop_gate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        opt_in(root)
        base = {"timestamp": "2026-11-19T10:00:00+00:00", "agent": "orchestrator", "session": "s"}
        lines = [
            {**base, "event": "SKILL_USED", "summary": "tdd"},
            {**base, "event": "SKILL_USED", "summary": "tdd"},
            {**base, "event": "SKILL_USED", "summary": "debug"},
            {**base, "event": "CLASSIFICATION_RECORDED", "feature": "a", "classification": {"declared": "M", "floor": "S", "effective": "M", "downgraded": False}},
            {**base, "event": "CLASSIFICATION_DOWNGRADED", "feature": "b", "classification": {"declared": "S", "floor": "M", "effective": "S", "downgraded": True}},
            {**base, "event": "STOP_GATE_BLOCKED", "feature": "a"},
            {**base, "event": "STOP_GATE_BLOCKED", "feature": "a"},
            {**base, "event": "STOP_GATE_ESCALATED", "feature": "a", "result": "max_blocks"},
            {**base, "event": "STOP_GATE_WAIVED", "feature": "a"},
        ]
        write(root, ".agent-system/timeline/events.jsonl", "\n".join(json.dumps(line) for line in lines) + "\n")
        report = json.loads(run("metrics.py", ["--root", str(root), "--json"]).stdout)
        assert report["skills"] == {"debug": 1, "tdd": 2}
        assert [(item["feature"], item["downgraded"]) for item in report["classifications"]] == [("a", False), ("b", True)]
        assert report["stop_gate"] == {"blocked": 2, "escalated": {"max_blocks": 1}, "waived": 1}


# Review findings (docs/reviews/enforcement.md): each test fails on the first 0.7.0 draft.

def test_floor_counts_staged_renames() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        for index in range(7):
            write(root, f"f{index}.py", "x = 1\ny = 2\n")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "files")
        (root / "src" / "auth").mkdir(parents=True)
        for index in range(7):
            git(root, "mv", f"f{index}.py", f"src/auth/g{index}.py")
            with (root / "src" / "auth" / f"g{index}.py").open("a", encoding="utf-8") as handle:
                handle.write("z = 3\n")
        git(root, "add", "-A")
        data = json.loads(run("classify_floor.py", ["--root", str(root), "--declared", "XS", "--json", "--no-record"]).stdout)
        assert data["floor"] == "M" and "authentication" in data["measure"]["surfaces"], data


def test_floor_thresholds_on_tracked_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        for index in range(6):
            write(root, f"m{index}.py", "a = 0\n")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "six")

        def floor() -> dict:
            return json.loads(run("classify_floor.py", ["--root", str(root), "--declared", "XS", "--json", "--no-record"]).stdout)

        for index in range(5):
            write(root, f"m{index}.py", "a = 1\n")
        found = floor()
        assert (found["floor"], len(found["measure"]["files"])) == ("S", 5), found
        write(root, "m5.py", "a = 1\n")
        assert floor()["floor"] == "M"
        git(root, "checkout", "--", ".")
        write(root, "m0.py", "".join(f"v{i} = {i}\n" for i in range(149)))  # 1 removed + 149 added = 150 lines
        assert floor()["floor"] == "S"
        write(root, "m0.py", "".join(f"v{i} = {i}\n" for i in range(299)))  # 1 removed + 299 added = 300 lines
        assert floor()["floor"] == "M"


def test_floor_measures_committed_work_against_the_default_branch() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        git(root, "branch", "-M", "main")
        git(root, "checkout", "-q", "-b", "feature")
        seven_files(root)
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "work")
        data = json.loads(run("classify_floor.py", ["--root", str(root), "--declared", "S", "--json", "--no-record"]).stdout)
        assert data["floor"] == "M" and len(data["measure"]["files"]) == 7, data


def test_floor_word_matching_and_binary_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        write(root, "AUTHORS", "someone\n")
        write(root, "docs/secretary_notes.txt", "x\n")
        (root / "logo.png").write_bytes(b"\x89PNG\0" + b"\n" * 500)
        data = json.loads(run("classify_floor.py", ["--root", str(root), "--declared", "S", "--json", "--no-record"]).stdout)
        assert data["measure"]["surfaces"] == {} and data["floor"] == "S", data
        write(root, "src/AuthService.ts", "export {}\n")
        data = json.loads(run("classify_floor.py", ["--root", str(root), "--declared", "S", "--json", "--no-record"]).stdout)
        assert "authentication" in data["measure"]["surfaces"]


def test_floor_requires_a_feature_for_m() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        opt_in(root)
        assert run("classify_floor.py", ["--root", str(root), "--declared", "M"]).returncode == 2


def test_stop_blocks_once_per_state_across_turns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        assert stop(root).get("decision") == "block"
        second = stop(root)  # a new user turn, nothing changed: tell the user once, do not block
        assert "decision" not in second and "systemMessage" in second
        assert stop(root) == {}  # and stay quiet afterwards
        assert state(root)["stop_gate"]["features"]["feat"]["blocks"] == 1


def test_stop_keeps_an_older_failing_feature_after_a_new_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        assert run("classify_floor.py", ["--root", str(root), "--feature", "other", "--declared", "S", "--justification", "docs only"]).returncode == 0
        reply = stop(root)
        assert reply.get("decision") == "block" and "--feature feat" in reply["reason"], reply


def test_reclassifying_drops_a_waiver() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        assert run("record_event.py", ["--root", str(root), "--event", "STOP_GATE_WAIVED", "--feature", "feat", "--summary", "user: ship it"]).returncode == 0
        assert stop(root) == {}
        assert run("classify_floor.py", ["--root", str(root), "--feature", "feat", "--declared", "M"]).returncode == 0
        assert stop(root).get("decision") == "block"


def test_skill_events_skip_builtins_and_duplicates() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        opt_in(root)
        common = {"session_id": "s1", "cwd": str(root)}
        hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "/help"}, root)
        hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "/security-review"}, root)
        hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "/agent-workbench:tdd go"}, root)
        hook({**common, "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_input": {"skill": "agent-workbench:tdd"}, "tool_response": "ok"}, root)
        hook({**common, "hook_event_name": "UserPromptSubmit", "prompt": "/agent-workbench:help"}, root)
        assert [event["summary"] for event in events(root) if event["event"] == "SKILL_USED"] == ["tdd", "help"]


def test_ci_gate_keeps_the_base_complexity_and_follows_task_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        shutil.copytree(FIXTURE / "docs", root / "docs")
        shutil.copytree(FIXTURE / "checks", root / "checks")
        shutil.copytree(FIXTURE / "src", root / "src")
        for path in (root / "docs").rglob("*.md"):
            path.write_text(path.read_text(encoding="utf-8").replace("__PYTHON__", PYTHON.replace("\\", "/")), encoding="utf-8")
        tasks = root / "docs" / "tasks" / "feat.md"
        text = tasks.read_text(encoding="utf-8")
        heading = next(line for line in text.splitlines() if line.startswith("### TASK-001"))
        tasks.write_text(text.replace(heading, heading + "\n- Files: src/coupon.py", 1), encoding="utf-8")
        (root / "docs" / "reviews" / "feat.md").unlink()
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "feature")
        base = git(root, "rev-parse", "HEAD")
        source = root / "src" / "coupon.py"
        source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        git(root, "commit", "-qam", "code only")
        done = run("ci_gate.py", ["--root", str(root), "--base", base])
        assert done.returncode == 1 and "feat" in done.stdout, done.stdout  # code changed, spec did not
        spec = root / "docs" / "specs" / "feat.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("complexity: M", "complexity: S"), encoding="utf-8")
        git(root, "commit", "-qam", "lower it")
        done = run("ci_gate.py", ["--root", str(root), "--base", base])
        assert done.returncode == 1 and "feat" in done.stdout, done.stdout  # lowering its own complexity does not skip it


# Second review (docs/reviews/enforcement.md, FIND-012 to FIND-016).

def test_stop_asks_again_when_the_change_outgrows_an_early_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        opt_in(root)
        write(root, "README.txt", "tiny\n")
        assert run("classify_floor.py", ["--root", str(root), "--feature", "early", "--declared", "XS"]).returncode == 0
        for index in range(10):
            write(root, f"src/grown_{index}.py", "x = 1\n")
        reply = stop(root)
        assert reply.get("decision") == "block" and "classify_floor.py" in reply["reason"], reply


def test_stop_limit_escalates_once_per_feature() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = failing_feature(Path(tmp) / "p")
        for index in range(3):
            write(root, "src/progress.py", f"STEP = {index}\n")
            assert stop(root).get("decision") == "block"
        messages = []
        for index in range(3):
            write(root, "src/progress.py", f"STEP = {10 + index}\n")
            messages.append(stop(root))
        assert "systemMessage" in messages[0] and messages[1] == {} and messages[2] == {}, messages


def test_ci_gate_fails_a_removed_or_superseded_large_spec() -> None:
    for action in ("delete", "supersede"):
        with tempfile.TemporaryDirectory() as tmp:
            root = repo(Path(tmp) / "p")
            shutil.copytree(FIXTURE / "docs", root / "docs")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "feature")
            base = git(root, "rev-parse", "HEAD")
            spec = root / "docs" / "specs" / "feat.md"
            if action == "delete":
                spec.unlink()
            else:
                spec.write_text(spec.read_text(encoding="utf-8").replace("status: approved", "status: superseded"), encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", action)
            done = run("ci_gate.py", ["--root", str(root), "--base", base])
            assert done.returncode == 1 and "feat" in done.stdout, (action, done.stdout)
            assert run("ci_gate.py", ["--root", str(root), "--base", base, "--allow-downgrade"]).returncode == 0


def test_ci_gate_runs_the_mutation_proof() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = repo(Path(tmp) / "p")
        base = git(root, "rev-parse", "HEAD")
        for source in (FIXTURE, SCRIPTS.parent / "evals" / "fixtures" / "mutation-catches-weak-test" / "project"):
            shutil.copytree(source, root, dirs_exist_ok=True)
        for path in (root / "docs").rglob("*.md"):
            path.write_text(path.read_text(encoding="utf-8").replace("__PYTHON__", PYTHON.replace("\\", "/")), encoding="utf-8")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "feature")
        done = run("ci_gate.py", ["--root", str(root), "--base", base])
        assert done.returncode == 1 and "mutation score 0.0" in done.stdout, done.stdout


def test_skill_events_count_two_real_uses() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "p"
        opt_in(root)
        common = {"session_id": "s1", "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "Skill", "tool_response": "ok"}
        hook({**common, "tool_input": {"skill": "agent-workbench:debug"}}, root)
        hook({**common, "tool_input": {"skill": "agent-workbench:debug"}}, root)
        assert [event["summary"] for event in events(root) if event["event"] == "SKILL_USED"] == ["debug", "debug"]
