"""Validate the structure of an ARCHITECTURE.md contract.

Checks the ten fixed section headings in order, the scaling stages of section 9 (one stage marked (atual)
in its title, at least two later stages, each with the four fields and a measurable trigger with a source),
and that every cited ADR-NNNN exists in the project's ADR folders (layout.json, default docs/architecture/ADR).
Standard library only. The stage labels are literal in every project, whatever the contract's language.

Exit codes: 0 valid, 1 structural problems, 2 usage error (missing file, bad layout.json).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import ConfigError, project_root, resolve_layout  # noqa: E402

SECTIONS = [
    "## 1. Contexto e atributos de qualidade",
    "## 2. Componentes e fronteiras",
    "## 3. Dados",
    "## 4. Cache",
    "## 5. Comunicação",
    "## 6. Deploy e infraestrutura",
    "## 7. Observabilidade",
    "## 8. Segurança e permissões",
    "## 9. Estágios de escala",
    "## 10. Anti-padrões",
]
# A measurable trigger compares a metric with a threshold: an operator, a number (thousands separators and
# decimals allowed), and a unit or a business rate ("reservas/s"). A duration alone ("por 7 dias") is not one.
MEASURABLE = re.compile(
    r"(?:[<>]=?|≥|≤|acima de|abaixo de|mais de|menos de)\s*"
    r"(?:\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*"
    r"(?:%|ms|s|min|minutos|h|horas|rps|GB|TB|MB|usuários|conexões|\w+/(?:s|min|h))(?![\w/])",
    re.IGNORECASE,
)
STAGE_FIELDS = ("- Gatilho:", "- Mudança:", "- Custo:", "- Pré-requisito:")
STAGE_TITLE = re.compile(r"^### Estágio (\d+): ")
ADR_CITE = re.compile(r"\bADR-(\d{3,4})\b")
ADR_STEM = re.compile(r"^(?:adr[-_ ]?)?0*(\d+)(?:\b|[-_])", re.IGNORECASE)
FENCE = re.compile(r"(?ms)^```.*?^```")


def contract_headings(text: str) -> list[str]:
    return [line.strip() for line in FENCE.sub("", text).splitlines() if re.match(r"## \d{1,2}\. ", line)]


def contract_section(text: str, number: int) -> str:
    heading = next(h for h in SECTIONS if h.startswith(f"## {number}. "))
    if heading not in text:
        return ""
    body = text.split(heading, 1)[1]
    return re.split(r"(?m)^## ", body, maxsplit=1)[0]


def section_errors(text: str) -> list[str]:
    found = contract_headings(text)
    if found == SECTIONS:
        return []
    errors = [f"missing section: {heading}" for heading in SECTIONS if heading not in found]
    errors += [f"unknown or renamed section: {heading}" for heading in found if heading not in SECTIONS]
    known = [heading for heading in found if heading in SECTIONS]
    expected = [heading for heading in SECTIONS if heading in known]
    for position, (got, want) in enumerate(zip(known, expected)):
        if got != want:
            errors.append(f"section out of order: {got} (position {position + 1}, expected {want})")
            break
    if len(found) != len(set(found)):
        errors += [f"duplicated section: {heading}" for heading in SECTIONS if found.count(heading) > 1]
    return errors


def stage_errors(contract: str) -> list[str]:
    """Problems in section 9: one stage marked (atual) in its title, and every later stage complete and measurable."""
    section = contract_section(contract, 9)
    if not section:
        return ["section 9 not found"]
    blocks = [b for b in re.split(r"(?m)^(?=### Estágio )", section) if b.startswith("### Estágio ")]
    malformed = [b.splitlines()[0] for b in blocks if not STAGE_TITLE.match(b)]
    if malformed:
        return [f"stage title must be '### Estágio <number>: <name>': {title}" for title in malformed]
    errors: list[str] = []
    if section.count("(atual)") != 1:
        errors.append("(atual) must appear exactly once in section 9")
    current = [b for b in blocks if "(atual)" in b.splitlines()[0]]
    if len(current) != 1:
        errors.append("exactly one stage title must carry (atual)")
        return errors
    current_number = int(STAGE_TITLE.match(current[0]).group(1))
    later = [b for b in blocks if int(STAGE_TITLE.match(b).group(1)) > current_number]
    if len(later) < 2:
        errors.append("at least two stages after the current one")
    for block in later:
        title = block.splitlines()[0]
        for field in STAGE_FIELDS:
            if field not in block:
                errors.append(f"{title}: missing {field}")
        trigger = next((line for line in block.splitlines() if line.startswith("- Gatilho:")), "")
        if trigger and not MEASURABLE.search(trigger):
            errors.append(f"{title}: trigger without operator, number, and unit")
        if trigger and "(fonte:" not in trigger:
            errors.append(f"{title}: trigger without (fonte: ...)")
    return errors


def adr_numbers(root: Path, layout: dict) -> set[int]:
    found = set()
    for folder in layout["adr_dirs"]:
        path = root / folder
        if path.is_dir():
            for item in path.glob("*.md"):
                match = ADR_STEM.match(item.stem)
                if match:
                    found.add(int(match.group(1)))
    return found


def adr_errors(text: str, root: Path, layout: dict) -> list[str]:
    existing = adr_numbers(root, layout)
    cited = sorted({int(number) for number in ADR_CITE.findall(text)})
    folders = ", ".join(layout["adr_dirs"])
    return [f"ADR-{number:04d} is cited but not found in {folders}" for number in cited if number not in existing]


def validate(text: str, root: Path, layout: dict) -> list[str]:
    # Fenced blocks are examples (Mermaid, sample headings, sample ADR ids): none of the checks reads them.
    text = FENCE.sub("", text)
    return section_errors(text) + stage_errors(text) + adr_errors(text, root, layout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the structure of ARCHITECTURE.md.")
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--file", default="ARCHITECTURE.md", help="contract path relative to the root")
    parser.add_argument("--json", action="store_true", help="structured output")
    args = parser.parse_args(argv)
    try:
        root = project_root(args.root)
        layout = resolve_layout(root)
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    path = (root / args.file).resolve()
    if not path.is_file():
        print(f"[ERROR] {args.file} not found", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8", errors="replace")
    errors = validate(text, root, layout)
    # The section names are Portuguese literals; print them as UTF-8 so they survive a cp1252 console or pipe.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if args.json:
        print(json.dumps({"file": args.file, "ok": not errors, "errors": errors}, ensure_ascii=False))
    else:
        for error in errors:
            print(f"[FAIL] {error}")
        print(f"{args.file}: {'valid' if not errors else f'{len(errors)} problem(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
