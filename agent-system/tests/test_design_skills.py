"""Structural contracts of the design skills and agents (content an agent must find)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import SCRIPTS, SYSTEM  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
import lint_design  # noqa: E402

PLUGIN = SYSTEM.parent
REFS = PLUGIN / "skills" / "design" / "references"
SECTIONS = [
    "## 1. Tema visual e atmosfera",
    "## 2. Cor",
    "## 3. Tipografia",
    "## 4. Espaçamento e grid",
    "## 5. Layout e composição",
    "## 6. Componentes",
    "## 7. Movimento e interação",
    "## 8. Voz e microcopy",
    "## 9. Anti-padrões",
]
P0_RULES = ["P0-INDIGO", "P0-GRADIENT", "P0-EMOJI-ICON", "P0-SIDE-STRIPE", "P0-FILLER", "P0-METRIC", "P0-PLACEHOLDER-CDN"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def headings_in_order(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if re.match(r"## \d\. ", line)]


def test_design_references_and_credits() -> None:
    anti = read(REFS / "anti-slop.md")
    for rule in P0_RULES:
        assert rule in anti, rule
    assert "design-lint-disable" in anti and "80/20" in anti
    assert headings_in_order(read(REFS / "design-md-format.md")) == SECTIONS
    assert "apple-design" in read(REFS / "design-md-format.md")
    assert read(REFS / "microcopy.md").strip()
    examples = sorted((REFS / "examples").glob("*.md"))
    assert 3 <= len(examples) <= 4, examples
    for path in examples:
        text = read(path)
        assert headings_in_order(text) == SECTIONS, path.name
        hexes = {lint_design.norm_hex(item) for item in lint_design.ANY_HEX.findall(text)}
        assert not hexes & lint_design.AI_INDIGO, (path.name, hexes & lint_design.AI_INDIGO)
    credits = read(REFS / "CREDITS.md")
    for source, license_name in (
        ("VoltAgent/awesome-design-md", "MIT"),
        ("nexu-io/open-design", "Apache-2.0"),
        ("Nutlope/hallmark", "MIT"),
        ("nextlevelbuilder/ui-ux-pro-max-skill", "MIT"),
        ("petergyang/no-ai-slop", "MIT"),
    ):
        line = next((item for item in credits.splitlines() if source in item), "")
        assert line and license_name in line, source


def skill(name: str) -> str:
    return read(PLUGIN / "skills" / name / "SKILL.md")


def test_design_discovery_contract() -> None:
    text = skill("design-discovery")
    for needle in ("at most 5 questions", "recommended answer", "at most 7 options", "2 to 3 references", "design/brief.md", "status: approved", "inferido"):
        assert needle in text, needle
    template = read(PLUGIN / "skills" / "design-discovery" / "references" / "brief-template.md")
    for needle in ("status: draft", "## Público", "## Tarefa principal", "## Tom de voz", "## Densidade", "## Idioma", "## Restrições", "## Referências", "Keep", "Change", "Do not copy", "fornecido", "observado", "inferido"):
        assert needle in template, needle


def test_design_directions_contract() -> None:
    text = skill("design-directions")
    for needle in ("design/directions/a.html", "b.html", "c.html", "index.html", "at least two", "layout", "display", "palette", "density", "Stop and wait", "DESIGN.md", "lint_design.py", "variety", "motion"):
        assert needle in text, needle
    reference = read(PLUGIN / "skills" / "design-directions" / "references" / "directions.md")
    assert "24" in reference and "96" in reference and "8" in reference and "32" in reference


def test_design_system_contract() -> None:
    text = skill("design-system")
    for needle in ("DESIGN.md", "design/tokens.css", "design/pages/", "4.5:1", "multiples of 4px", "at most 3", "confirmation", "status: approved", "design-md-format.md"):
        assert needle in text, needle
    template = read(PLUGIN / "skills" / "design-system" / "references" / "tokens-template.css")
    assert ":root" in template and "--color-accent-ink" in template and "--space-1: 4px" in template
    hexes = {lint_design.norm_hex(item) for item in lint_design.ANY_HEX.findall(template)}
    assert not hexes & lint_design.AI_INDIGO


def test_design_review_contract() -> None:
    text = skill("design-review")
    for axis in ("stance", "hierarchy", "execution", "specificity", "restraint", "variety"):
        assert axis in text.lower(), axis
    for needle in ("below 3", "3 passes", "in prose", "lint_design.py", "microcopy.md"):
        assert needle in text, needle
    checklist = read(PLUGIN / "skills" / "design-review" / "references" / "review-checklist.md")
    for needle in ("4.5:1", "3:1", "44px", "320", "1920", "45", "75"):
        assert needle in checklist, needle


def test_design_orchestration_and_ui_ux() -> None:
    text = skill("design")
    order = [text.index(name) for name in ("design-discovery", "design-directions", "design-system", "design-review")]
    assert order == sorted(order), order
    assert "status: approved" in text
    ui = skill("ui-ux")
    for needle in ("DESIGN.md", "design/tokens.css", "design/pages/", "/design", "lint_design.py"):
        assert needle in ui, needle
    for relative in ("skills/help/SKILL.md", "README.md", "README.pt-BR.md"):
        doc = read(PLUGIN / relative)
        for command in ("/design", "/design-discovery", "/design-directions", "/design-system", "/design-review"):
            assert command in doc, (relative, command)


def frontmatter(path: Path) -> dict:
    fields = {}
    for line in read(path).split("---")[1].splitlines():
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def test_design_agents_contract() -> None:
    import json

    registry = [item["name"] for item in json.loads(read(SYSTEM / "agents.json"))["agents"]]
    assert registry[-3:] == ["designer", "frontend-implementer", "design-reviewer"], registry
    tools = {item.strip() for item in frontmatter(PLUGIN / "agents" / "design-reviewer.md")["tools"].split(",")}
    assert not tools & {"Edit", "MultiEdit", "NotebookEdit"}, tools
    assert "Does not write production code" in read(PLUGIN / "agents" / "designer.md")
    implementer = read(PLUGIN / "agents" / "frontend-implementer.md")
    for needle in ("DESIGN.md", "lint_design.py", "empty", "loading", "error", "success"):
        assert needle in implementer, needle
    reviewer = read(PLUGIN / "agents" / "design-reviewer.md")
    assert "Does not fix" in reviewer and "P0" in reviewer
    orchestrator = read(PLUGIN / "agents" / "orchestrator.md")
    contracts = read(SYSTEM / "docs" / "contracts.md")
    for name in ("designer", "frontend-implementer", "design-reviewer"):
        assert name in orchestrator and f"### {name}" in contracts, name


SAMPLE = SYSTEM / "tests" / "samples" / "design-sample"
TOKEN = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")


def luminance(value: str) -> float:
    value = lint_design.norm_hex(value)
    channels = []
    for index in (1, 3, 5):
        channel = int(value[index:index + 2], 16) / 255
        channels.append(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(first: str, second: str) -> float:
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_design_sample_artifacts() -> None:
    design = read(SAMPLE / "DESIGN.md")
    assert "status: approved" in design
    assert headings_in_order(design) == SECTIONS
    # The first :root block holds the values; a later @media block only overrides them (reduced motion).
    tokens = dict(TOKEN.findall(read(SAMPLE / "design" / "tokens.css").split("@media", 1)[0]))
    values = {value.strip().lower() for value in tokens.values()}
    for item in lint_design.ANY_HEX.findall(design):
        assert lint_design.norm_hex(item) in {lint_design.norm_hex(v) for v in values if v.startswith("#")}, item
    for name, value in tokens.items():
        if name.startswith("--space-"):
            assert value.strip().endswith("px") and int(value.strip()[:-2]) % 4 == 0, (name, value)
        if name.endswith("-ink"):
            base = tokens.get(name[: -len("-ink")])
            if base and base.strip().startswith("#") and value.strip().startswith("#"):
                assert contrast(base.strip(), value.strip()) >= 4.5, (name, base, value)
    families = {value.split(",")[0].strip().strip("'\"").lower() for name, value in tokens.items() if name.startswith("--font-")}
    assert len(families) <= 3, families
    brief = read(SAMPLE / "design" / "brief.md")
    assert "status: approved" in brief and "Do not copy" in brief
    directions = sorted((SAMPLE / "design" / "directions").glob("*.html"))
    assert [path.name for path in directions] == ["a.html", "b.html", "c.html", "index.html"], directions
    for path in directions:
        html = read(path)
        assert not re.search(r"<script[^>]+src=[\"']https?:", html) and not re.search(r"<img[^>]+src=[\"']https?:", html), path.name
        if path.name != "index.html":
            assert html.lstrip().startswith("<!-- direction:"), path.name
    findings = lint_design.lint_paths([SAMPLE], SAMPLE / "DESIGN.md", SAMPLE / "design" / "tokens.css")
    assert not [item for item in findings if item.severity == "P0"], findings
    # AC-016: the screen built from the contract uses only tokens.
    screen = lint_design.lint_paths([SAMPLE / "src"], SAMPLE / "DESIGN.md", SAMPLE / "design" / "tokens.css")
    assert not [item for item in screen if item.rule in {"P1-RAW-COLOR", "P1-FONT-LITERAL"}], screen
    # AC-011: every token value DESIGN.md cites (`--name: value`) matches the tokens file.
    for name, value in re.findall(r"`(--[\w-]+): ([^`]+)`", design):
        assert tokens.get(name, "").strip() == value.strip(), (name, value, tokens.get(name))
    for name, value, *_ in re.findall(r"\| `(--(?:color|font|text|space|radius)[\w-]*)` \| `?([^|`]+?)`? \|", design):
        if name.startswith("--color-"):
            assert tokens.get(name, "").strip().lower() == value.strip().lower(), (name, value, tokens.get(name))
    # AC-010: section 9 names the lint's P0 rules.
    nine = design.split("## 9.", 1)[1]
    assert "P0" in nine and "índigo" in nine and "emoji" in nine, nine[:200]
    # AC-005: every pair of directions differs on at least two of the four axes.
    axes = {}
    for path in directions:
        if path.name == "index.html":
            continue
        field = re.search(r"axes: ([^>]+?) -->", read(path)).group(1)
        axes[path.stem] = dict(item.strip().split("=", 1) for item in field.split(","))
    names = sorted(axes)
    for index, first in enumerate(names):
        for second in names[index + 1:]:
            differing = [key for key in ("layout", "display", "palette", "density") if axes[first][key] != axes[second][key]]
            assert len(differing) >= 2, (first, second, differing)


ACCEPTANCE_ACS = ("AC-001", "AC-002", "AC-004", "AC-007", "AC-008", "AC-009", "AC-013", "AC-014", "AC-020", "AC-021")


def test_design_acceptance_report_records_each_ac() -> None:
    report = read(PLUGIN / "docs" / "reviews" / "design-pipeline-acceptance.md")
    missing = [item for item in ACCEPTANCE_ACS if item not in report]
    assert not missing, missing
