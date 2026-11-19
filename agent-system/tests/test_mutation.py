"""Mutation proof: operators, in-place safety, and the gate criterion."""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_mutation  # noqa: E402
from support import PYTHON, SCRIPTS, run, write  # noqa: E402

FIXTURES = SCRIPTS.parent / "evals" / "fixtures"


def project(tmp: str, name: str = "mutation-strong-tests") -> Path:
    root = Path(tmp) / "p"
    shutil.copytree(FIXTURES / "complete-feature" / "project", root)
    shutil.copytree(FIXTURES / name / "project", root, dirs_exist_ok=True)
    for path in root.rglob("*.md"):
        path.write_text(path.read_text(encoding="utf-8").replace("__PYTHON__", PYTHON.replace("\\", "/")), encoding="utf-8")
    return root


def test_mutation_operators_each_change_one_site() -> None:
    source = "def f(a, b):\n    if a < b and not a:\n        return a + 1\n    return True\n"
    found = check_mutation.sites(ast.parse(source))
    kinds = [description.split(": ", 1)[1] for _, description in found]
    assert "Lt -> LtE (#0)" in kinds and "And -> Or" in kinds and "remove not" in kinds and "negate if condition" in kinds
    assert "Add -> Sub" in kinds and "1 -> 2" in kinds and "True -> False" in kinds and "return None" in kinds
    mutants = {check_mutation.mutate(source, index, description) for index, description in found}
    assert len(mutants) == len(found)
    for mutant in mutants:
        ast.parse(mutant)
        assert mutant != ast.unparse(ast.parse(source))


def test_mutation_restores_files_byte_for_byte() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        target = root / "src" / "coupon.py"
        target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
        before = target.read_bytes()
        done = run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert done.returncode == 0, done.stdout + done.stderr
        assert target.read_bytes() == before
        assert not (root / ".agent-system" / "mutation").exists()


def test_mutation_restores_an_interrupted_run_first() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        target = root / "src" / "coupon.py"
        original = target.read_bytes()
        write(root, ".agent-system/mutation/backup.py", original.decode("utf-8"))
        write(root, ".agent-system/mutation/pending.json", json.dumps({"src/coupon.py": "backup.py"}))
        target.write_text("def apply(*args):\n    return None\n", encoding="utf-8")
        done = run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "restored files left mutated" in done.stdout
        assert target.read_bytes().replace(b"\r\n", b"\n") == original.replace(b"\r\n", b"\n")


def test_mutation_refuses_unmutated_failure_and_non_python() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        (root / "src" / "coupon.py").write_text("def apply(total, percent, expired):\n    return 0, None\n", encoding="utf-8")
        done = run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert done.returncode == 1 and "does not pass unmutated" in done.stdout
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        tasks = root / "docs" / "tasks" / "feat.md"
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("- Mutate: src/coupon.py", "- Mutate: src/app.ts"), encoding="utf-8")
        done = run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record", "--json"])
        data = json.loads(done.stdout)
        assert done.returncode == 1 and data["status"] == "ERROR" and "only existing .py files" in data["reason"]


def test_gate_requires_fresh_mutation_score() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        assert run("check_proofs.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 0
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert gate.returncode == 1 and "No mutation score for feat" in gate.stdout
        assert run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 0
        write(root, "src/extra.py", "X = 1\n")
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "Mutation score predates the current workspace" in gate.stdout


def test_gate_ignores_mutation_without_minimum() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        spec = root / "docs" / "specs" / "feat.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("mutation_min_score: 0.6\n", ""), encoding="utf-8")
        assert run("check_proofs.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 0
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "mutation" not in gate.stdout.lower()


def test_gate_fails_spec_minimum_without_declared_mutate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        tasks = root / "docs" / "tasks" / "feat.md"
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("- Mutate: src/coupon.py\n", ""), encoding="utf-8")
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert gate.returncode == 1 and "no required TEST declares Mutate" in gate.stdout


# Review findings (docs/reviews/mutation-proof.md): each test fails on the first 0.7.0 draft.

def clean_env() -> dict:
    """The environment of a normal shell or CI runner: bytecode caching on."""
    return {key: value for key, value in os.environ.items() if key not in {"PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX"}}


def same_size_project(tmp: str) -> Path:
    """One integer constant whose only mutant (5 -> 6) has the same size as the original."""
    root = Path(tmp) / "p"
    write(root, "src/m.py", "A = 5\n")
    write(root, "checks/test_m.py", "import sys\n\nsys.path.insert(0, 'src')\nimport m  # noqa: E402\n\nassert m.A == 5\n")
    command = json.dumps([PYTHON, "checks/test_m.py"])
    write(root, "docs/specs/feat.md", "---\nstatus: approved\ncomplexity: M\nsecurity_risk: LOW\nmutation_min_score: 1\n---\n# Spec: m\n\n## Requirements\n\n### REQ-001: A\nTHE SYSTEM SHALL keep A at 5.\n\n## Acceptance Criteria\n\n### AC-001: A is 5\n- Requirements: REQ-001\nGiven m When read Then A is 5.\n\n## Assumptions\n\n- none\n")
    write(root, "docs/tasks/feat.md", f"# Tasks: m\n\n### TASK-001: A\n- Requirements: REQ-001\n- Acceptance: AC-001\n- Verification: TEST-001\n- Done when: TEST-001 passes\n- Status: done\n\n### TEST-001: A is 5\n- Acceptance: AC-001\n- Task: TASK-001\n- Command: {command}\n- Mutate: src/m.py\n")
    return root


def test_mutation_ignores_stale_bytecode() -> None:
    for attempt in range(3):
        with tempfile.TemporaryDirectory() as tmp:
            root = same_size_project(tmp)
            env = clean_env()
            subprocess.run([PYTHON, "checks/test_m.py"], cwd=root, env=env, check=True)  # caches src/__pycache__/m.*.pyc
            original = (root / "src" / "m.py").read_bytes()
            done = subprocess.run([PYTHON, str(SCRIPTS / "check_mutation.py"), "--root", str(root), "--feature", "feat", "--no-record", "--json"],
                                  capture_output=True, text=True, env=env, check=False)
            data = json.loads(done.stdout)
            assert data["score"] == 1.0 and done.returncode == 0, (attempt, data)
            assert (root / "src" / "m.py").read_bytes() == original
            check = subprocess.run([PYTHON, "checks/test_m.py"], cwd=root, env=env, check=False)
            assert check.returncode == 0  # the restored module imports as the original


def test_mutation_restores_exact_bytes_after_an_interrupted_run() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        target = root / "src" / "coupon.py"
        original = target.read_bytes().replace(b"\n", b"\r\n")
        write(root, ".agent-system/mutation/backup.py", "")
        (root / ".agent-system" / "mutation" / "backup.py").write_bytes(original)
        write(root, ".agent-system/mutation/pending.json", json.dumps({"src/coupon.py": "backup.py"}))
        target.write_text("def apply(*args):\n    return None\n", encoding="utf-8")
        assert run("check_proofs.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 2
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "mutation-pending" in gate.stdout or "may still be mutated" in gate.stdout
        run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert target.read_bytes() == original
        assert not (root / ".agent-system" / "mutation").exists()


def test_mutation_restore_refuses_paths_outside_the_root() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        outside = Path(tmp) / "outside.txt"
        outside.write_text("keep\n", encoding="utf-8")
        write(root, ".agent-system/mutation/backup.py", "evil\n")
        write(root, ".agent-system/mutation/pending.json", json.dumps({"../outside.txt": "backup.py"}))
        assert check_mutation.restore_pending(root) == []
        assert outside.read_text(encoding="utf-8") == "keep\n"


def test_mutation_minimum_must_be_valid() -> None:
    for value in ("60", "0", "abc"):
        with tempfile.TemporaryDirectory() as tmp:
            root = project(tmp)
            spec = root / "docs" / "specs" / "feat.md"
            spec.write_text(spec.read_text(encoding="utf-8").replace("mutation_min_score: 0.6", f"mutation_min_score: {value}"), encoding="utf-8")
            gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
            assert gate.returncode == 1 and "mutation_min_score in the spec" in gate.stdout, (value, gate.stdout)
            assert run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 2


def test_gate_rejects_a_score_for_other_targets_or_commands() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        write(root, "src/other.py", "def g(x):\n    return x > 1\n")
        tasks = root / "docs" / "tasks" / "feat.md"
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("- Mutate: src/coupon.py", "- Mutate: src/coupon.py, src/other.py", 1), encoding="utf-8")
        assert run("check_proofs.py", ["--root", str(root), "--feature", "feat", "--no-record"]).returncode == 0
        run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("- Mutate: src/coupon.py, src/other.py", "- Mutate: src/coupon.py", 1), encoding="utf-8")
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "Mutate files changed" in gate.stdout, gate.stdout
        text = tasks.read_text(encoding="utf-8")
        command = next(line for line in text.splitlines() if line.startswith("- Command:"))
        tasks.write_text(text.replace(command, command.replace("]", ', "--extra"]'), 1), encoding="utf-8")
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "commands, changed" in gate.stdout, gate.stdout


def test_gate_reports_an_unmeasured_run_and_warns_for_layout_minimum() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        (root / "src" / "coupon.py").write_text("def apply(total, percent, expired):\n    return 0, None\n", encoding="utf-8")
        run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "Mutation run is FAIL" in gate.stdout, gate.stdout
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        spec = root / "docs" / "specs" / "feat.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("mutation_min_score: 0.6\n", ""), encoding="utf-8")
        tasks = root / "docs" / "tasks" / "feat.md"
        tasks.write_text(tasks.read_text(encoding="utf-8").replace("- Mutate: src/coupon.py\n", ""), encoding="utf-8")
        write(root, ".agent-system/layout.json", json.dumps({"mutation": {"min_score": 0.5}}))
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "feat", "--no-record"])
        assert "[WARN]" in gate.stdout and "no required TEST declares Mutate" in gate.stdout, gate.stdout


def test_mutation_refuses_non_utf8_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = project(tmp)
        target = root / "src" / "coupon.py"
        target.write_bytes(target.read_bytes() + "# caf\xe9\n".encode("latin-1"))
        data = json.loads(run("check_mutation.py", ["--root", str(root), "--feature", "feat", "--no-record", "--json"]).stdout)
        assert data["status"] == "ERROR" and "not UTF-8" in data["reason"], data
