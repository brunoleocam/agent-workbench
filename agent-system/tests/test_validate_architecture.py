"""validate_architecture.py: sections in order, measurable stages, cited ADRs, and the layout's ADR folder."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import SYSTEM, run, write  # noqa: E402

FIXTURE = SYSTEM / "evals" / "fixtures" / "architecture-contract" / "project"
ARCH = "docs/architecture/ARCHITECTURE.md"


def project() -> tempfile.TemporaryDirectory:
    folder = tempfile.TemporaryDirectory()
    shutil.copytree(FIXTURE, folder.name, dirs_exist_ok=True)
    return folder


def check(root: Path, *args: str):
    done = run("validate_architecture.py", ["--root", str(root), *args, "--json"])
    return done.returncode, (json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}), done


def contract(root: Path) -> str:
    return (root / ARCH).read_text(encoding="utf-8")


def test_validate_architecture_accepts_a_valid_contract() -> None:
    with project() as raw:
        code, report, done = check(Path(raw))
        assert code == 0 and report["ok"] and report["errors"] == [], (report, done.stderr)


def test_validate_architecture_refuses_sections_out_of_order_or_missing() -> None:
    with project() as raw:
        root = Path(raw)
        text = contract(root)
        write(root, ARCH, text.replace("## 4. Cache", "## 4. Caching"))
        code, report, _ = check(root)
        assert code == 1
        assert "missing section: ## 4. Cache" in report["errors"], report
        assert "unknown or renamed section: ## 4. Caching" in report["errors"], report


def test_validate_architecture_refuses_a_vague_trigger_citing_the_stage() -> None:
    """AC-011: "quando crescer" is never accepted."""
    with project() as raw:
        root = Path(raw)
        text = contract(root).replace("CPU do banco > 60% por 7 dias (fonte: métricas do servidor)", "quando crescer por 7 dias (fonte: intuição)")
        write(root, ARCH, text)
        code, report, _ = check(root)
        assert code == 1
        assert "### Estágio 1: banco gerenciado: trigger without operator, number, and unit" in report["errors"], report


def test_validate_architecture_refuses_a_missing_adr() -> None:
    """AC-012: a cited ADR must exist."""
    with project() as raw:
        root = Path(raw)
        write(root, ARCH, contract(root).replace("RBAC com", "RBAC (ADR-0002) com"))
        code, report, _ = check(root)
        assert code == 1
        assert any(error.startswith("ADR-0002 is cited but not found") for error in report["errors"]), report


def test_validate_architecture_reads_the_adr_folder_from_layout() -> None:
    with project() as raw:
        root = Path(raw)
        (root / "docs" / "architecture" / "ADR" / "0001-postgres.md").rename(root / "0001-postgres.md")
        assert check(root)[0] == 1
        write(root, "decisions/0001-postgres.md", (root / "0001-postgres.md").read_text(encoding="utf-8"))
        write(root, ".agent-system/layout.json", json.dumps({"overrides": {"adr_dir": "decisions"}}))
        code, report, _ = check(root)
        assert code == 0, report


def test_validate_architecture_text_output_and_usage_errors() -> None:
    with project() as raw:
        root = Path(raw)
        done = run("validate_architecture.py", ["--root", str(root)])
        assert done.returncode == 0 and "ARCHITECTURE.md: valid" in done.stdout, done.stdout
        missing = run("validate_architecture.py", ["--root", str(root), "--file", "nope.md"])
        assert missing.returncode == 2 and "not found" in missing.stderr


def test_validate_architecture_accepts_every_case_study_contract() -> None:
    """The four case studies are valid contracts once cut out of their case file."""
    examples = SYSTEM.parent / "skills" / "architecture" / "references" / "examples"
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for path in sorted(examples.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            body = text.split("## Contrato", 1)[1].split("## O que este caso ensina", 1)[0]
            write(root, ARCH, body)
            code, report, _ = check(root)
            assert code == 0, (path.name, report)


def test_validate_architecture_refuses_order_and_duplicates() -> None:
    """AC-026 without the eval runner: section 9 before 8, and a repeated section."""
    with project() as raw:
        root = Path(raw)
        text = contract(root)
        s8, s9, s10 = (text.index(h) for h in ("## 8. Segurança", "## 9. Estágios", "## 10. Anti"))
        write(root, ARCH, text[:s8] + text[s9:s10] + text[s8:s9] + text[s10:])
        code, report, _ = check(root)
        assert code == 1
        assert any(error.startswith("section out of order: ## 9. Estágios de escala") for error in report["errors"]), report
        write(root, ARCH, text + "\n## 4. Cache\n\nDe novo.\n")
        code, report, _ = check(root)
        assert code == 1 and "duplicated section: ## 4. Cache" in report["errors"], report


def test_validate_architecture_ignores_fenced_examples() -> None:
    """FIND-024: a fenced sample heading or ADR id is not part of the contract."""
    sample = "\n```markdown\n## 9. Estágios de escala\n### Estágio 0: x (atual)\nVer ADR-0009.\n```\n"
    with project() as raw:
        root = Path(raw)
        text = contract(root)
        write(root, ARCH, text.replace("## 3. Dados", sample + "\n## 3. Dados", 1))
        code, report, _ = check(root)
        assert code == 0, report


def test_validate_architecture_eval_fixture_passes() -> None:
    """AC-026 through the eval runner, so TEST-008 covers it."""
    done = run("run_evals.py", ["architecture-contract"])
    assert done.returncode == 0 and "[PASS] architecture-contract" in done.stdout, done.stdout + done.stderr


def test_validate_architecture_reads_a_legacy_root_contract_with_a_warning() -> None:
    with project() as raw:
        root = Path(raw)
        (root / ARCH).replace(root / "ARCHITECTURE.md")
        code, report, done = check(root)
        assert code == 0 and report["file"] == "ARCHITECTURE.md", done.stdout
        assert "move it to docs/architecture/ARCHITECTURE.md" in done.stderr, done.stderr
        # Once moved, the folder copy wins and the warning goes away.
        write(root, ARCH, (root / "ARCHITECTURE.md").read_text(encoding="utf-8"))
        code, report, done = check(root)
        assert code == 0 and report["file"] == ARCH and "[WARN]" not in done.stderr, done.stderr
