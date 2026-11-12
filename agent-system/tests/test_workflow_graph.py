"""The declared execution graph: the plugin graph is valid, each structural error fails, state ownership, and Mermaid."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import SYSTEM, run, write  # noqa: E402

GRAPH = json.loads((SYSTEM / "workflow.json").read_text(encoding="utf-8"))
REGISTRY = json.loads((SYSTEM / "agents.json").read_text(encoding="utf-8"))
HUMAN_NODES = {"approve_spec", "approve_architecture", "choose_direction", "approve_design", "accept_risk", "escalate", "approve_commit"}


def check(graph: dict | None, raw: str | None = None, registry: dict | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        args = []
        if graph is not None or raw is not None:
            path = write(root, "workflow.json", raw if raw is not None else json.dumps(graph))
            args += ["--workflow", str(path)]
        else:
            args += ["--workflow", str(root / "missing.json")]
        if registry is not None:
            args += ["--agents", str(write(root, "agents.json", json.dumps(registry)))]
        done = run("validate_workflow.py", [*args, "--json"])
    data = json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}
    return done.returncode, data


def codes(data: dict) -> set[str]:
    return {item["code"] for item in data.get("errors", [])}


def mutated(change) -> dict:
    graph = copy.deepcopy(GRAPH)
    change(graph)
    return graph


def edge(graph: dict, source: str, target: str) -> dict:
    return next(item for item in graph["edges"] if item["from"] == source and item["to"] == target)


def test_plugin_graph_is_valid() -> None:
    code, data = check(GRAPH)
    assert code == 0, data
    assert data["ok"] and not data["errors"]
    used = {node["agent"] for node in GRAPH["nodes"] if node["kind"] == "agent"}
    for agent in REGISTRY["agents"]:
        if agent["name"] != "orchestrator":
            assert agent["name"] in used, agent["name"]
    humans = {node["id"] for node in GRAPH["nodes"] if node["kind"] == "human"}
    assert HUMAN_NODES <= humans, HUMAN_NODES - humans
    default = run("validate_workflow.py", [])
    assert default.returncode == 0, default.stdout + default.stderr


def test_each_structural_error_fails() -> None:
    def remove_node(graph: dict, node_id: str) -> None:
        graph["nodes"] = [node for node in graph["nodes"] if node["id"] != node_id]
        graph["edges"] = [item for item in graph["edges"] if node_id not in (item["from"], item["to"])]

    cases = {
        "duplicate-node": lambda g: g["nodes"].append(copy.deepcopy(g["nodes"][1])),
        "unknown-edge-node": lambda g: g["edges"].append({"from": "plan", "to": "ghost"}),
        "unknown-start": lambda g: g.update(start="ghost"),
        "unreachable": lambda g: g["nodes"].append({"id": "island", "kind": "agent", "agent": "planner", "description": "x"}),
        "agent-without-node": lambda g: remove_node(g, "design_review"),
        "unknown-agent": lambda g: g["nodes"][3].update(agent="ghost-agent"),
        "missing-script": lambda g: next(n for n in g["nodes"] if n["id"] == "spec_check").update(script="ghost.py"),
        "gate-without-fail": lambda g: g.update(edges=[e for e in g["edges"] if not (e["from"] == "gate" and e.get("on") == "fail")]),
        "gate-without-escalate": lambda g: g.update(edges=[e for e in g["edges"] if not (e["from"] == "gate" and e.get("on") == "escalate")]),
        "agent-only-cycle": lambda g: g["edges"].append({"from": "test", "to": "implement"}),
        "group-without-join": lambda g: edge(g, "proofs", "review").pop("join"),
        "group-branch-no-join": lambda g: g.update(edges=[e for e in g["edges"] if not (e["from"] == "design_review" and e["to"] == "gate")]
                                                    + [{"from": "design_review", "to": "approve_commit"}]),
        "bad-when": lambda g: edge(g, "classify", "plan").update(when={"complexity_min": "HUGE"}),
        "bad-on": lambda g: edge(g, "gate", "approve_commit").update(on="maybe"),
        "bad-limit": lambda g: g.update(limits={"max_revisions": 0}),
        "unknown-kind": lambda g: g["nodes"][1].update(kind="robot"),
    }
    for expected, change in cases.items():
        code, data = check(mutated(change))
        assert code == 1, (expected, data)
        assert expected in codes(data), (expected, codes(data))
        assert all(item["message"] for item in data["errors"])
        assert all(item["ref"] for item in data["errors"] if item["code"] == expected), (expected, data["errors"])

    for bad in ({"from": ["plan"], "to": "gate"}, {"from": "plan", "to": "gate", "group": ["g"], "join": "gate"}):
        code, data = check(mutated(lambda g, bad=bad: g["edges"].append(bad)))
        assert code == 1 and data, bad  # a JSON report, not a traceback
        assert "structure" in codes(data)

    missing_code, missing = check(None)
    assert missing_code == 2 and "config_error" in missing
    invalid_code, invalid = check(None, raw="{not json")
    assert invalid_code == 2 and "config_error" in invalid


def test_project_agents_do_not_need_nodes() -> None:
    registry = copy.deepcopy(REGISTRY)
    registry["agents"].append({"name": "data-migrator", "scope": "project", "status": "active"})
    code, data = check(GRAPH, registry=registry)
    assert code == 0, data


def test_state_field_ownership() -> None:
    code, data = check(mutated(lambda g: g["state_fields"].pop("verification")))
    assert code == 1
    assert any(item["code"] == "state-field-missing" and item["ref"] == "verification" for item in data["errors"])
    code, data = check(mutated(lambda g: g["state_fields"].update(foo=["hook"])))
    assert code == 1
    assert any(item["code"] == "state-field-unknown" and item["ref"] == "foo" for item in data["errors"])
    code, data = check(mutated(lambda g: g["state_fields"].update(phase=["ghost_writer.py"])))
    assert code == 1
    assert "state-writer-unknown" in codes(data)


def test_mermaid_has_every_node_and_edge() -> None:
    done = run("validate_workflow.py", ["--mermaid"])
    assert done.returncode == 0, done.stderr
    lines = done.stdout.splitlines()
    assert lines[0] == "flowchart TD"
    for node in GRAPH["nodes"]:
        opener = {"agent": '["', "script": '[["', "human": '{{"'}[node["kind"]]
        assert any(line.strip().startswith(node["id"] + opener) for line in lines), node["id"]
    arrows = [line for line in lines if "-->" in line or "-.->" in line]
    assert len(arrows) == len(GRAPH["edges"])
    assert any("-.->|fail|" in line for line in arrows)
    assert any("parallel verify" in line for line in arrows)
    broken = mutated(lambda g: g.update(start="ghost"))
    with tempfile.TemporaryDirectory() as tmp:
        path = write(Path(tmp), "workflow.json", json.dumps(broken))
        failed = run("validate_workflow.py", ["--workflow", str(path), "--mermaid"])
    assert failed.returncode == 1
    assert "flowchart" not in failed.stdout
