"""Structural contracts of the architecture skills (content an agent must find).

These tests prove that the skills, templates, and references contain the instructions and formats the spec
requires. They do not prove that an agent following them behaves as the acceptance criteria describe; that is
confirmed in the rehearsal after phase 3.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import SCRIPTS, SYSTEM  # noqa: E402

sys.path.insert(0, str(SCRIPTS))

# The stage and trigger rules live in validate_architecture.py; the tests use the same code.
from validate_architecture import (  # noqa: E402
    MEASURABLE,
    SECTIONS,
    STAGE_FIELDS,
    contract_headings,
    contract_section,
    stage_errors,
)

PLUGIN = SYSTEM.parent
SKILLS = PLUGIN / "skills"
REFS = SKILLS / "architecture" / "references"
REFERENCES = [
    "architecture-md-format.md", "scaling-stages.md", "data-stores.md", "caching.md", "messaging.md",
    "patterns.md", "deploy.md", "observability.md", "permissions.md",
]
PATTERNS = ["CQRS", "Event Sourcing", "Saga", "Circuit breaker", "Rate limiting", "Sharding", "Server-Sent Events"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


GOOD_STAGES = """## 9. Estágios de escala

### Estágio 0: monólito (atual)
- Mudança: desenho atual.

### Estágio 1: réplica
- Gatilho: p95 de leitura > 300 ms por 7 dias (fonte: APM)
- Mudança: réplica de leitura
- Custo: uma instância a mais
- Pré-requisito: leituras críticas no primário

### Estágio 2: fila
- Gatilho: CPU da app acima de 70% por 5 dias (fonte: métricas do servidor)
- Mudança: workers
- Custo: broker
- Pré-requisito: consumidores idempotentes

## 10. Anti-padrões
"""


def test_stage_check_accepts_a_complete_section() -> None:
    assert stage_errors(GOOD_STAGES) == []


def test_stage_check_refuses_vague_or_incomplete_stages() -> None:
    first = "p95 de leitura > 300 ms por 7 dias"
    broken = {
        "duration only": GOOD_STAGES.replace(first, "quando crescer por 7 dias"),
        "number without operator": GOOD_STAGES.replace(first, "revisar ADR-0004 h"),
        "duration as threshold": GOOD_STAGES.replace(first, "mais de 7 dias"),
        "no source": GOOD_STAGES.replace(" (fonte: APM)", ""),
        "missing field": GOOD_STAGES.replace("- Custo: broker\n", ""),
        "two current": GOOD_STAGES.replace("### Estágio 1: réplica", "### Estágio 1: réplica (atual)"),
        "current in body": GOOD_STAGES.replace("monólito (atual)", "monólito").replace(
            "- Mudança: desenho atual.", "- Mudança: desenho (atual)."
        ),
        "one later stage": GOOD_STAGES.split("### Estágio 2")[0] + "## 10. Anti-padrões\n",
        "title with dash": GOOD_STAGES.replace("### Estágio 0: monólito", "### Estágio 0 - monólito"),
        "title with word": GOOD_STAGES.replace("### Estágio 2: fila", "### Estágio dois: fila"),
    }
    for name, text in broken.items():
        assert stage_errors(text), name


def test_measurable_trigger_numbers_and_rates() -> None:
    for line in (
        "- Gatilho: usuários ativos > 1.000.000 usuários por 30 dias (fonte: analytics)",
        "- Gatilho: tentativas de reserva > 3.000 reservas/s num evento (fonte: métrica de negócio)",
        "- Gatilho: disponibilidade mensal < 99,5% (fonte: monitor externo)",
        "- Gatilho: pedidos acima de 1.200,5 pedidos/min no pico (fonte: APM)",
    ):
        assert MEASURABLE.search(line), line
    for line in ("- Gatilho: quando crescer por 7 dias", "- Gatilho: latência de 300 ms", "- Gatilho: rever ADR-0004 h"):
        assert not MEASURABLE.search(line), line


def test_architecture_references_and_credits() -> None:
    for name in REFERENCES:
        assert (REFS / name).is_file(), name
    format_ref = read(REFS / "architecture-md-format.md")
    assert contract_headings(format_ref) == SECTIONS
    assert "labels are literal" in format_ref
    accepted = next(line for line in format_ref.splitlines() if line.startswith("- Accepted:"))
    refused = next(line for line in format_ref.splitlines() if line.startswith("- Refused:"))
    assert MEASURABLE.search(accepted) and not MEASURABLE.search(refused)
    patterns = read(REFS / "patterns.md")
    for name in PATTERNS:
        assert name.lower() in patterns.lower(), name
    assert patterns.count("When to use") >= len(PATTERNS) and patterns.count("When not to use") >= len(PATTERNS)
    assert "outbox" in read(REFS / "messaging.md").lower()
    assert "08-security-engineering" in read(REFS / "permissions.md")
    credits = read(REFS / "CREDITS.md")
    assert "RenatoAugustoTech" in credits and "no content was transcribed" in credits.lower()


EXAMPLES = REFS / "examples"


def test_architecture_case_studies_follow_the_contract() -> None:
    cases = sorted(EXAMPLES.glob("*.md"))
    assert 3 <= len(cases) <= 4, cases
    for path in cases:
        text = read(path)
        for heading in ("## Brief", "## Opções", "## Contrato", "## O que este caso ensina"):
            assert heading in text, (path.name, heading)
        contract = text.split("## Contrato", 1)[1].split("## O que este caso ensina", 1)[0]
        assert contract_headings(contract) == SECTIONS, path.name
        assert stage_errors(contract) == [], (path.name, stage_errors(contract))
        assert "```mermaid" in contract_section(contract, 2), path.name
        assert "- Migrações:" in contract_section(contract, 3), path.name
        assert "- Garantia de entrega:" in contract_section(contract, 5), path.name
        deploy = contract_section(contract, 6)
        assert "- Ambientes:" in deploy and "- Caminho até produção:" in deploy, path.name
        assert "- Portas expostas:" in contract_section(contract, 8), path.name
        assert "recomendad" in text.split("## Opções", 1)[1].split("## Contrato", 1)[0].lower(), path.name


BRIEF_SECTIONS = [
    "## Propósito", "## Usuários e carga", "## Padrão de acesso", "## Consistência", "## Latência e disponibilidade",
    "## Dados sensíveis e obrigações legais", "## Equipe", "## Orçamento", "## Alvo de infraestrutura",
    "## Restrições", "## Arquitetura atual", "## Estimativa de capacidade",
]


def test_architecture_discovery_skill() -> None:
    skill = read(SKILLS / "architecture-discovery" / "SKILL.md")
    assert "name: architecture-discovery" in skill
    for needle in (
        "**at most 6 questions**",
        "**The infrastructure target. Always asked**",
        "ainda não sei",
        "fly.toml",
        "docker-compose",
        "Outbound bandwidth per month, always",
        "sets `status: draft` again",
    ):
        assert needle in skill, needle
    template = read(SKILLS / "architecture-discovery" / "references" / "brief-template.md")
    assert "status: draft" in template
    for heading in BRIEF_SECTIONS:
        assert heading in template, heading
    for mark in ("fornecido", "observado", "inferido"):
        assert mark in template, mark


def test_architecture_options_skill() -> None:
    skill = read(SKILLS / "architecture-options" / "SKILL.md")
    assert "name: architecture-options" in skill
    for needle in ("Mermaid", "Kubernetes", "**Stop and wait**", "Do not write `ARCHITECTURE.md`", "`status: approved`"):
        assert needle in skill, needle
    template = read(SKILLS / "architecture-options" / "references" / "options-template.md")
    assert "status: draft" in template and "choice:" in template
    for column in ("Custo mensal", "Complexidade operacional", "Pontos únicos de falha", "Se a carga dobrar", "Deixa de servir quando"):
        assert column in template, column
    assert "```mermaid" in template and "## Recomendação" in template


def test_architecture_system_skill() -> None:
    skill = read(SKILLS / "architecture-system" / "SKILL.md")
    assert "name: architecture-system" in skill
    for needle in (
        "`adr_dir`",
        "## Alternatives",
        "supersede",
        "(atual)",
        "is never recorded",
        "only after the user's explicit confirmation",
    ):
        assert needle in skill, needle
    move = skill.split("## 6. Moving to the next stage", 1)[1]
    assert "confirmation" in move, "a stage move needs the user's confirmation"
    template = read(SKILLS / "architecture-system" / "references" / "architecture-template.md")
    assert "status: draft" in template
    assert contract_headings(template) == SECTIONS
    for field in STAGE_FIELDS:
        assert field in template, field


def test_architecture_orchestration_and_review_skills() -> None:
    chain = read(SKILLS / "architecture" / "SKILL.md")
    assert "name: architecture" in chain
    order = [chain.index(name) for name in ("architecture-discovery", "architecture-options", "architecture-system", "architecture-review")]
    assert order == sorted(order), order
    assert "status: approved" in chain
    review = read(SKILLS / "architecture-review" / "SKILL.md")
    assert "name: architecture-review" in review and "<plugin>/agent-system/scripts/lint_infra.py" in review
    checklist = read(SKILLS / "architecture-review" / "references" / "review-checklist.md").lower()
    for needle in ("idempot", "correlation", "secret", "section 2", "p0-unpinned-image"):
        assert needle in checklist, needle
    assert "/architecture" in read(SKILLS / "help" / "SKILL.md")
