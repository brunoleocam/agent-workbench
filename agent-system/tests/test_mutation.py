"""Mutation proof: operators, in-place safety, and the gate criterion."""

from __future__ import annotations

import ast
import json
import shutil
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
