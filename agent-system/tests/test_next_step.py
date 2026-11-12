"""The deterministic router: complexity and risk routing, fan-out, design, human nodes, and the revision limit."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import SYSTEM, feature_project, opt_in, run, write  # noqa: E402


def route(*args: str, root: Path | None = None):
    extra = ["--root", str(root)] if root else []
    done = run("next_step.py", [*extra, *args])
    data = json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}
    return done.returncode, data


def test_complexity_picks_plan_or_direct() -> None:
    code, data = route("--from", "classify", "--class", "FEATURE", "--complexity", "M", "--security", "LOW")
    assert code == 0, data
    assert data["next"] == ["plan"] and data["nodes"][0]["agent"] == "planner"
    code, data = route("--from", "classify", "--class", "FEATURE", "--complexity", "S", "--security", "LOW")
    assert data["next"] == ["implement_direct"] and data["nodes"][0]["agent"] == "implementer"
    code, data = route("--from", "classify", "--class", "BUG_FIX", "--complexity", "M", "--security", "LOW")
    assert data["next"] == ["debug"]
    assert any("class BUG_FIX" in reason for reason in data["reason"])


def test_high_risk_fans_out_to_security() -> None:
    base = ["--from", "proofs", "--result", "pass", "--class", "FEATURE", "--complexity", "M"]
    assert route(*base, "--security", "LOW")[0] == 2  # the design_review branch needs --interface
    code, data = route(*base, "--security", "HIGH", "--interface", "none")
    assert code == 0, data
    assert data["parallel"] is True
    assert data["next"] == ["review", "security_review"]
    assert data["join"] == "gate"
    code, data = route(*base, "--security", "LOW", "--interface", "none")
    assert data["next"] == ["review"]
    assert data["parallel"] is False and data["join"] == "gate"
    code, data = route(*base, "--security", "LOW", "--interface", "new")
    assert data["next"] == ["review", "design_review"]
    code, data = route(*base, "--security", "HIGH", "--interface", "new")
    assert data["next"] == ["review", "security_review", "design_review"] and data["parallel"] is True
    code, data = route("--from", "proofs", "--result", "fail")
    assert data["next"] == ["fix_failure"]


def test_new_interface_goes_to_designer() -> None:
    base = ["--from", "plan", "--class", "FEATURE", "--complexity", "M", "--security", "LOW"]
    assert route(*base)[0] == 2  # a forgotten --interface is an error, not "no UI"
    code, data = route(*base, "--interface", "existing")
    assert data["next"] == ["spec_check"]
    code, data = route(*base, "--interface", "new")
    assert data["next"] == ["design"] and data["nodes"][0]["agent"] == "designer"
    code, data = route("--from", "design")
    assert data["next"] == ["choose_direction"] and data["status"] == "needs_decision"
    code, data = route(*base, "--interface", "new", "--design-approved")
    assert data["next"] == ["spec_check"]
    code, data = route("--from", "tasks_check", "--interface", "new")
    assert data["next"] == ["frontend_implement"]


def test_human_node_stops_with_question() -> None:
    code, data = route("--from", "spec_check", "--result", "pass")
    assert code == 0
    assert data["next"] == ["approve_spec"]
    assert data["status"] == "needs_decision"
    assert data["question"].strip()
    code, data = route("--from", "plan", "--result", "escalate")
    assert data["next"] == ["approve_architecture"] and data["status"] == "needs_decision"
    code, data = route("--from", "checkpoint")
    assert code == 0 and data["status"] == "done" and data["next"] == []


def test_bad_arguments_exit_2() -> None:
    assert route("--from", "ghost")[0] == 2
    assert route("--from", "classify")[0] == 2  # the first classify edge needs --class
    assert route("--from", "gate", "--result", "fail", "--interface", "none")[0] == 2  # needs --feature
    assert route("--from", "gate", "--result", "maybe")[0] == 2
    with tempfile.TemporaryDirectory() as tmp:
        assert route("--from", "plan", "--workflow", str(Path(tmp) / "none.json"))[0] == 2


def test_no_matching_edge_exits_1() -> None:
    graph = json.loads((SYSTEM / "workflow.json").read_text(encoding="utf-8"))
    graph["edges"] = [edge for edge in graph["edges"] if not (edge["from"] == "test")] + [{"from": "test", "to": "proofs", "when": {"complexity_min": "L"}}]
    with tempfile.TemporaryDirectory() as tmp:
        path = write(Path(tmp), "workflow.json", json.dumps(graph))
        code, data = route("--from", "test", "--complexity", "M", "--workflow", str(path))
    assert code == 1 and data["status"] == "no_match"


def test_gate_failures_escalate_at_the_limit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = feature_project(Path(tmp))
        opt_in(root)
        gate = ["--from", "gate", "--result", "fail", "--feature", "reset", "--interface", "none"]
        for expected in (1, 2):
            done = run("validate_verification.py", ["--root", str(root), "--feature", "reset"])
            assert done.returncode == 1, done.stdout
            state = json.loads((root / ".cursor" / "agent-system" / "state.json").read_text(encoding="utf-8"))
            assert state["revisions"]["reset"] == expected
        code, data = route(*gate, root=root)
        assert code == 0 and data["next"] == ["implement"], data
        assert data["revisions"] == 2
        run("validate_verification.py", ["--root", str(root), "--feature", "reset"])
        code, data = route(*gate, root=root)
        assert data["next"] == ["escalate"], data
        assert data["status"] == "needs_decision" and data["result"] == "escalate"
        assert any("revisions 3 >= max_revisions 3" in reason for reason in data["reason"])

        state_path = root / ".cursor" / "agent-system" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["phase"] == "verification"
        # Manual events cannot move the counter: only validate_verification.py records the gate node.
        forged = run("record_event.py", ["--root", str(root), "--event", "VERIFICATION_COMPLETED", "--summary", "gate", "--result", "passed", "--feature", "reset"])
        assert forged.returncode == 0, forged.stderr
        assert json.loads(state_path.read_text(encoding="utf-8"))["revisions"]["reset"] == 3
        as_gate = run("record_event.py", ["--root", str(root), "--event", "VERIFICATION_COMPLETED", "--summary", "gate", "--feature", "reset", "--node", "gate"])
        assert as_gate.returncode == 2 and "script node" in as_gate.stderr
        # The user's answer to the escalation resets the count, so the next cycle gets max_revisions attempts again.
        answered = run("record_event.py", ["--root", str(root), "--event", "REWORK_STARTED", "--summary", "user: continue fixing", "--feature", "reset", "--node", "escalate"])
        assert answered.returncode == 0, answered.stderr
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert state["revisions"]["reset"] == 0
        code, data = route(*gate, root=root)
        assert data["next"] == ["implement"]


def custom_limit(tmp: Path, limits) -> Path:
    graph = json.loads((SYSTEM / "workflow.json").read_text(encoding="utf-8"))
    if limits is None:
        graph.pop("limits")
    else:
        graph["limits"] = limits
    return write(tmp, "workflow.json", json.dumps(graph))


def test_the_limit_comes_from_the_graph() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        root = tmp / "project"
        write(root, ".cursor/agent-system/state.json", json.dumps({"revisions": {"f": 1}}))
        gate = ["--from", "gate", "--result", "fail", "--feature", "f", "--interface", "none"]
        code, data = route(*gate, "--workflow", str(custom_limit(tmp / "one", {"max_revisions": 1})), root=root)
        assert data["next"] == ["escalate"], data
        default = custom_limit(tmp / "default", None)
        assert route(*gate, "--workflow", str(default), root=root)[1]["next"] == ["implement"]
        write(root, ".cursor/agent-system/state.json", json.dumps({"revisions": {"f": 3}}))
        assert route(*gate, "--workflow", str(default), root=root)[1]["next"] == ["escalate"]


def test_escalations_and_new_ui_reach_the_right_nodes() -> None:
    code, data = route("--from", "design_review", "--result", "escalate")
    assert data["next"] == ["accept_risk"] and data["status"] == "needs_decision"
    assert route("--from", "accept_risk", "--result", "fail", "--interface", "new")[1]["next"] == ["frontend_implement"]
    assert route("--from", "accept_risk", "--result", "fail", "--interface", "none")[1]["next"] == ["implement"]
    assert route("--from", "escalate", "--result", "pass", "--interface", "new")[1]["next"] == ["frontend_implement"]
    assert route("--from", "escalate", "--result", "fail", "--interface", "new")[1]["next"] == ["plan"]
