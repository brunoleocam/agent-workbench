"""The graph reaches the rest of the harness: README diagram without drift, orchestrator and CLAUDE.md text, and the init copy."""

from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SYSTEM, run, write  # noqa: E402

sys.path.insert(0, str(SYSTEM / "scripts"))

import workflow  # noqa: E402

PLUGIN = SYSTEM.parent
GRAPH = json.loads((SYSTEM / "workflow.json").read_text(encoding="utf-8"))
BLOCK = re.compile(r"<!-- workflow:begin -->\n```mermaid\n(.*?)```\n<!-- workflow:end -->", re.DOTALL)


def readme_diagram() -> str:
    found = BLOCK.search((SYSTEM / "README.md").read_text(encoding="utf-8"))
    assert found, "agent-system/README.md has no workflow block"
    return found.group(1)


def test_readme_diagram_matches_graph() -> None:
    generated = run("validate_workflow.py", ["--mermaid"])
    assert generated.returncode == 0, generated.stderr
    assert readme_diagram() == generated.stdout, "regenerate the block with validate_workflow.py --mermaid"
    changed = copy.deepcopy(GRAPH)
    next(edge for edge in changed["edges"] if edge["from"] == "test")["to"] = "gate"
    assert workflow.mermaid(changed) != readme_diagram()


def test_orchestrator_and_claude_follow_the_graph() -> None:
    orchestrator = (PLUGIN / "agents" / "orchestrator.md").read_text(encoding="utf-8")
    template = (SYSTEM / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
    for text in (orchestrator, template):
        assert "next_step.py" in text
        assert "needs_decision" in text
        assert "M or larger" in text
        assert "--interface" in text
    registry = {item["name"] for item in json.loads((SYSTEM / "agents.json").read_text(encoding="utf-8"))["agents"]}
    used = {node["agent"] for node in GRAPH["nodes"] if node["kind"] == "agent"}
    cited = {name for name in re.findall(r"`([a-z-]+)`", orchestrator) if name in registry and name != "orchestrator"}
    assert cited, "the orchestrator cites no agent"
    assert cited <= used, cited - used


def test_init_copies_graph_and_router() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write(root, "README.md", "# demo\n")
        done = run("init_project.py", ["--root", str(root), "--claude"])
        assert done.returncode == 0, done.stderr
        system = root / ".cursor" / "agent-system"
        for name in ("workflow.py", "validate_workflow.py", "next_step.py"):
            assert (system / "scripts" / name).is_file(), name
        assert json.loads((system / "workflow.json").read_text(encoding="utf-8")) == GRAPH
        state = json.loads((system / "state.json").read_text(encoding="utf-8"))
        assert state["revisions"] == {}
        assert "next_step.py" in (root / "CLAUDE.md").read_text(encoding="utf-8")

        project = subprocess.run([PYTHON, str(system / "scripts" / "validate_workflow.py")], capture_output=True, text=True, check=False)
        assert project.returncode == 0, project.stdout + project.stderr
        routed = subprocess.run(
            [PYTHON, str(system / "scripts" / "next_step.py"), "--root", str(root), "--from", "gate", "--result", "fail", "--feature", "x", "--interface", "none"],
            capture_output=True, text=True, check=False,
        )
        assert routed.returncode == 0, routed.stderr
        assert json.loads(routed.stdout)["next"] == ["implement"]

        # An older state without `revisions` gains it on the next init; other values are kept.
        state.pop("revisions")
        state["next_step"] = "keep me"
        (system / "state.json").write_text(json.dumps(state), encoding="utf-8")
        assert run("init_project.py", ["--root", str(root), "--claude"]).returncode == 0
        migrated = json.loads((system / "state.json").read_text(encoding="utf-8"))
        assert migrated["revisions"] == {} and migrated["next_step"] == "keep me"


def test_docs_cite_the_new_scripts() -> None:
    docs = {
        "agent-system/docs/cli.md": SYSTEM / "docs" / "cli.md",
        "agent-system/README.md": SYSTEM / "README.md",
        "README.md": PLUGIN / "README.md",
        "README.pt-BR.md": PLUGIN / "README.pt-BR.md",
        "skills/help/SKILL.md": PLUGIN / "skills" / "help" / "SKILL.md",
    }
    for label, path in docs.items():
        text = path.read_text(encoding="utf-8")
        for script in ("validate_workflow.py", "next_step.py", "metrics.py"):
            assert script in text, (label, script)
    for label in ("README.md", "README.pt-BR.md", "skills/help/SKILL.md"):
        assert "global" in docs[label].read_text(encoding="utf-8").lower(), label
