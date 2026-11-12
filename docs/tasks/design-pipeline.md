# Tasks: pipeline de design UI/UX

Spec: [design-pipeline](../specs/design-pipeline.md) (approved).

**Objetivo:** dar ao Workbench um pipeline de design (entrevista → 3 direções → DESIGN.md + tokens → revisão) com três agentes e um lint anti-slop determinístico que reprova os sinais clássicos de UI genérica.

**Abordagem:** primeiro o lint, porque ele é código testável e as skills e os agentes dependem dele (`design-review`, `frontend-implementer` e `design-reviewer` rodam o lint). Depois o hook. Em seguida as referências compartilhadas, as quatro skills, a orquestração, os agentes e, por fim, um ensaio real cujo resultado fica versionado como amostra e é verificado por teste.

**Stack do repo:** Python stdlib (3.10 a 3.13) em `agent-system/scripts/`; testes são funções `test_*` em `agent-system/tests/test_*.py`, coletadas por `agent-system/scripts/test_system.py`, que aceita filtros por substring de `módulo.função`; helpers em `agent-system/tests/support.py` (`run`, `write`, `opt_in`). Skills em `skills/<nome>/SKILL.md` com `references/`; agentes em `agents/<nome>.md` registrados em `agent-system/agents.json`. CI: `.github/workflows/ci.yml` roda `test_system.py` e `run_evals.py` em Ubuntu e Windows.

**Restrições copiadas da spec:**
- Só stdlib Python, compatível com 3.10 a 3.13, Windows e Linux.
- Skills no formato `skills/<nome>/SKILL.md` com `references/`, funcionando em Cursor e Claude Code. `test_skills_follow_the_agent_skills_specification` exige front matter só com campos conhecidos, `name` igual à pasta, descrição de até 1024 caracteres, menos de 500 linhas e links relativos que existam.
- Nenhum DESIGN.md de exemplo reproduz identidade de marca real.
- O hook nunca bloqueia nem altera arquivo.
- `ui-ux-experiment` e `apple-design` continuam válidas.

**Idioma:** o texto das skills e dos agentes fica em inglês, como o resto do harness, com gatilhos em português na `description`. Os valores que a spec fixa ficam literais: os títulos das 9 seções do DESIGN.md (REQ-011) e as marcas `fornecido | observado | inferido` (REQ-003).

**Invariantes que já existem e precisam continuar verdes:**
- `test_static` em `agent-system/scripts/test_system.py` compara a lista exata de agentes em `agents.json`.
- `test_registry_matches_agent_files` exige um `agents/<nome>.md` para cada entrada do registro, e vice-versa.
- `test_init_skill_list_matches_skills_folder` já lê a pasta `skills/`, então skill nova entra sozinha.
- `init_project.COPY_SCRIPTS` lista os scripts copiados para `.cursor/agent-system/scripts/` do projeto. O hook copiado importa o lint, então `lint_design.py` precisa entrar nessa lista.

**Limitação conhecida (REQ-032 no Cursor):** o `afterFileEdit` do Cursor não tem canal de retorno para o agente. No Cursor, o achado vai para a timeline (projetos com opt-in), e o `frontend-implementer` roda o lint por conta própria (REQ-024). Se isso não bastar para a REQ-032, abra um `change-request` antes da TASK-003.

---

### TASK-001: Lint — núcleo, regras P0, supressão e saída
- Requirements: REQ-027, REQ-028, REQ-030, REQ-031, REQ-034
- Acceptance: AC-023, AC-024, AC-026, AC-027, AC-030
- Files: agent-system/scripts/lint_design.py, agent-system/tests/test_design_lint.py
- Baseline: agent-system/scripts/lint_design.py=absent, agent-system/tests/test_design_lint.py=absent
- Out of scope: regras P1/P2 (TASK-002), hook (TASK-003)
- Stop if: `agent-system/scripts/lint_design.py` já existir
- Depends on: none
- Verification: TEST-001, TEST-002, TEST-003, TEST-004
- Done when: TEST-001 a TEST-004 passam e a suíte inteira continua verde
- Gate: check_proofs TEST-001 TEST-002 TEST-003 TEST-004
- Status: done

#### Passos

1. Crie `agent-system/tests/test_design_lint.py` com os testes abaixo.
2. Rode `python agent-system/scripts/test_system.py test_design_lint`. Esperado: `FAIL` em todos, porque o script não existe e `run` devolve exit 2 com `can't open file`.
3. Crie `agent-system/scripts/lint_design.py` com o código abaixo.
4. Rode de novo o mesmo comando. Esperado: `6 passed, 0 failed` e `ok`.
5. Regressão: `python agent-system/scripts/test_system.py`. Esperado: `ok`.

#### Teste (`agent-system/tests/test_design_lint.py`)

```python
"""Anti-AI-slop design lint: rules, exit codes, output, suppression, brand allowlist, and the hook."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import run, write  # noqa: E402

P0_CASES = {
    "P0-INDIGO": ("src/Button.tsx", 'export const B = () => <button style={{ background: "#6366f1" }}>Salvar</button>;\n'),
    "P0-GRADIENT": ("src/hero.css", ".hero {\n  background: linear-gradient(135deg, #8b5cf6, #3b82f6);\n}\n"),
    "P0-EMOJI-ICON": ("src/Features.tsx", "export const F = () => <h3>\U0001F680 Deploy rápido</h3>;\n"),
    "P0-SIDE-STRIPE": ("src/card.css", ".card {\n  border-left: 4px solid #0f766e;\n  border-radius: 12px;\n}\n"),
    "P0-FILLER": ("index.html", "<p>Lorem ipsum dolor sit amet</p>\n"),
    "P0-METRIC": ("index.html", "<p>Deploys 10x faster than before</p>\n"),
    "P0-PLACEHOLDER-CDN": ("index.html", '<img src="https://images.unsplash.com/photo-1" alt="">\n'),
}


def lint(root: Path, *args: str):
    done = run("lint_design.py", [*args, "--format", "json"], cwd=root)
    return done.returncode, (json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}), done


def rules(report: dict) -> set[str]:
    return {item["rule"] for item in report.get("findings", [])}


def test_design_lint_flags_each_p0() -> None:
    for rule, (relative, text) in P0_CASES.items():
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            code, report, done = lint(root, relative)
            assert code == 1, (rule, code, done.stdout, done.stderr)
            assert rule in rules(report), (rule, report)


def test_design_lint_finding_shape_and_json() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "index.html", "<ul>\n  <li>✨ Rápido</li>\n</ul>\n")
        code, report, _ = lint(root, "index.html")
        assert code == 1
        finding = report["findings"][0]
        assert set(finding) == {"file", "line", "rule", "severity", "message", "suggestion"}
        assert finding["file"] == "index.html" and finding["line"] == 2 and finding["severity"] == "P0"
        assert finding["message"] and finding["suggestion"]
        assert report["summary"]["P0"] == 1
        text = run("lint_design.py", ["index.html"], cwd=root)
        assert "index.html:2: P0 P0-EMOJI-ICON" in text.stdout, text.stdout


def test_design_lint_skips_vendor_and_build_folders() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "src/App.tsx", 'const c = "#6366f1";\n')
        for folder in ("node_modules/x", "dist", "build", ".next", ".git"):
            write(root, f"{folder}/index.html", '<div style="color:#6366f1"></div>\n')
        code, report, _ = lint(root, ".")
        assert code == 1
        assert {item["file"] for item in report["findings"]} == {"src/App.tsx"}, report


def test_design_lint_allows_declared_brand_color() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "design/tokens.css", ":root {\n  --color-accent: #7c3aed;\n}\n")
        write(root, "src/Badge.tsx", 'export const Badge = () => <span className="bg-violet-600">Novo</span>;\n')
        code, report, _ = lint(root, "src", "--tokens", "design/tokens.css")
        assert "P0-INDIGO" not in rules(report), report
        assert code == 0
        # Without the token file the same class is the default AI accent.
        (root / "design" / "tokens.css").unlink()
        code, report, _ = lint(root, "src")
        assert code == 1 and "P0-INDIGO" in rules(report)


def test_design_lint_suppression_needs_a_reason() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(
            root,
            "index.html",
            "<!-- design-lint-disable P0-METRIC -- SLA contratual -->\n"
            "<p>99.9% uptime</p>\n"
            "<!-- design-lint-disable P0-METRIC -->\n"
            "<p>99.9% uptime</p>\n",
        )
        code, report, _ = lint(root, "index.html")
        lines = {(item["rule"], item["line"]) for item in report["findings"]}
        assert ("P0-METRIC", 2) not in lines, lines
        assert ("P0-METRIC", 4) in lines and ("P1-SUPPRESSION-NO-REASON", 3) in lines, lines
        assert code == 1


def test_design_lint_usage_errors_exit_2() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        assert run("lint_design.py", ["missing"], cwd=root).returncode == 2
        write(root, "a.css", "a { color: red; }\n")
        assert run("lint_design.py", ["a.css", "--tokens", "nope.css"], cwd=root).returncode == 2
```

#### Código (`agent-system/scripts/lint_design.py`)

```python
"""Anti-AI-slop design lint for UI source files.

Reports P0 (blocking), P1, and P2 findings with file, line, rule, severity, message, and suggestion.
Heuristic: regular expressions over text, no CSS or JSX parser. Standard library only.

Exit codes: 0 without P0 findings, 1 with at least one P0, 2 on a usage error.
Suppress one rule on a line, or on the line after the comment:
    design-lint-disable P0-METRIC -- <reason>
A suppression without a reason is ignored and reported as P1-SUPPRESSION-NO-REASON.
"""

from __future__ import annotations

import argparse
import bisect
import colorsys
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

EXTENSIONS = {".html", ".htm", ".css", ".scss", ".jsx", ".tsx", ".vue", ".svelte"}
MARKUP = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", "dist", "build", ".next", ".git"}
MAX_BYTES = 512 * 1024

AI_INDIGO = {"#6366f1", "#4f46e5", "#4338ca", "#3730a3", "#8b5cf6", "#7c3aed", "#a855f7"}
TAILWIND = {
    "indigo-400": "#818cf8", "indigo-500": "#6366f1", "indigo-600": "#4f46e5", "indigo-700": "#4338ca",
    "violet-400": "#a78bfa", "violet-500": "#8b5cf6", "violet-600": "#7c3aed", "violet-700": "#6d28d9",
    "purple-400": "#c084fc", "purple-500": "#a855f7", "purple-600": "#9333ea", "purple-700": "#7e22ce",
}
TW_FAMILY = {"blue": "blue", "sky": "blue", "cyan": "blue", "indigo": "blue", "violet": "purple", "purple": "purple", "fuchsia": "pink", "pink": "pink"}

ANY_HEX = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_-])")
INDIGO_CLASS = re.compile(r"\b(?:bg|text|border|from|via|to|ring|fill|stroke|outline|shadow)-((?:indigo|violet|purple)-[4-7]00)\b")
GRADIENT = re.compile(r"(?:linear|radial|conic)-gradient\(([^;{}]*)\)", re.I)
TW_GRADIENT = re.compile(r"\bfrom-([a-z]+)-\d{2,3}\b[^\"'`\n]*?\bto-([a-z]+)-\d{2,3}\b")
CLIP_TEXT = re.compile(r"background-clip\s*:\s*text|backgroundClip\s*:\s*[\"']text|\bbg-clip-text\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐⭕]")
ICON_TEXT = re.compile(
    r"<(h[1-6]|button|li)\b[^>]*>([^<]*)|<(\w+)[^>]*\bclass(?:Name)?=[\"'][^\"']*icon[^\"']*[\"'][^>]*>([^<]*)",
    re.I,
)
CSS_BLOCK = re.compile(r"\{([^{}]*)\}")
SIDE_BORDER = re.compile(
    r"(?:border-(?:left|right|inline-start|inline-end)|border(?:Left|Right|InlineStart|InlineEnd))"
    r"\s*:\s*[\"'`]?(\d+)px\s+solid\s+(?!transparent)",
)
RADIUS = re.compile(r"border-radius|borderRadius")
CLASS_ATTR = re.compile(r"\bclass(?:Name)?\s*=\s*[\"'`{]([^\"'`}]*)")
TW_SIDE = re.compile(r"\bborder-[lrse]-(?:[2-8]|\[\d+px\])(?![\w-])")
TW_ROUNDED = re.compile(r"\brounded(?:-[\w\[\]]+)?(?![\w-])")
FILLER = re.compile(r"lorem ipsum|\bfeature (?:one|two|three)\b|placeholder text|sample content|\bjohn doe\b|\bjane doe\b|\bacme\b", re.I)
METRIC = re.compile(
    r"\b\d+(?:[.,]\d+)?\s?[x×]\s+(?:faster|more|better|cheaper|mais)\b"
    r"|\b9\d(?:[.,]\d+)?\s?%\s+(?:uptime|availability|disponibilidade)\b"
    r"|\b(?:trusted by|used by|loved by|usado por|confiado por|mais de|over)\s+\d[\d.,]*\s?[kKmM]?\+?\s+"
    r"(?:teams|companies|users|developers|customers|empresas|usu[aá]rios|times|clientes|desenvolvedores)\b",
    re.I,
)
CDN = re.compile(r"(?:images\.)?unsplash\.com|placehold\.co|placekitten\.com|picsum\.photos|via\.placeholder\.com", re.I)
# The reason needs a space after "--", so the "-->" that closes an HTML comment is never read as a reason.
SUPPRESS = re.compile(r"design-lint-disable\s+([A-Z0-9,\s-]+?)(?:\s+--\s+(\S.*?))?\s*(?:\*/|-->|\}|$)")
COMMENT_END = re.compile(r"\s*(?:\*/|-->|\})+\s*$")
RULE_ID = re.compile(r"P[012]-[A-Z-]+")


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    severity: str
    message: str
    suggestion: str


class Source:
    """One file's text with offset-to-line lookup."""

    def __init__(self, display: str, suffix: str, text: str, is_tokens: bool = False) -> None:
        self.display = display
        self.suffix = suffix
        self.text = text
        self.is_tokens = is_tokens
        self.starts = [0] + [index + 1 for index, char in enumerate(text) if char == "\n"]
        self.findings: list[Finding] = []

    def line(self, offset: int) -> int:
        return bisect.bisect_right(self.starts, offset)

    def add(self, offset: int, rule: str, message: str, suggestion: str) -> None:
        self.findings.append(Finding(self.display, self.line(offset), rule, rule[:2], message, suggestion))


def norm_hex(value: str) -> str:
    value = value.lower()
    if len(value) == 4:
        value = "#" + "".join(char * 2 for char in value[1:])
    return value


def hue(value: str) -> float | None:
    """Hue in degrees for a saturated, mid-lightness color; None for neutrals."""
    value = norm_hex(value)
    red, green, blue = (int(value[index:index + 2], 16) / 255 for index in (1, 3, 5))
    shade, light, saturation = colorsys.rgb_to_hls(red, green, blue)
    if saturation < 0.3 or light < 0.15 or light > 0.92:
        return None
    return shade * 360


def declared_colors(*paths: Path | None) -> set[str]:
    found: set[str] = set()
    for path in paths:
        if path and path.is_file():
            found |= {norm_hex(item) for item in ANY_HEX.findall(path.read_text(encoding="utf-8", errors="replace"))}
    return found


def check_p0(src: Source, allowed: set[str]) -> None:
    text = src.text
    for match in ANY_HEX.finditer(text):
        value = norm_hex(match.group())
        if value in AI_INDIGO and value not in allowed:
            src.add(match.start(), "P0-INDIGO", f"Default Tailwind indigo/violet {value} used as a color.", "Use the accent token from DESIGN.md, for example var(--color-accent).")
    for match in INDIGO_CLASS.finditer(text):
        if TAILWIND[match.group(1)] not in allowed:
            src.add(match.start(), "P0-INDIGO", f"Default Tailwind class {match.group()} used as a color.", "Use the accent token from DESIGN.md instead of the framework default.")
    for match in GRADIENT.finditer(text):
        stops = [norm_hex(item) for item in ANY_HEX.findall(match.group(1))]
        hues = [value for value in (hue(item) for item in stops) if value is not None and 180 <= value < 345]
        if len(hues) >= 2 and max(hues) - min(hues) >= 20 and not set(stops) <= allowed:
            src.add(match.start(), "P0-GRADIENT", "Purple, blue, cyan, or pink two-stop gradient.", "Use a flat surface from the tokens and let type carry the section.")
    for match in TW_GRADIENT.finditer(text):
        first, last = TW_FAMILY.get(match.group(1)), TW_FAMILY.get(match.group(2))
        if first and last and match.group(1) != match.group(2):
            src.add(match.start(), "P0-GRADIENT", f"Framework gradient {match.group(1)} to {match.group(2)}.", "Use a flat surface from the tokens and let type carry the section.")
    for match in CLIP_TEXT.finditer(text):
        src.add(match.start(), "P0-GRADIENT", "Gradient text (background-clip: text).", "Use a solid token color for text.")
    for match in CSS_BLOCK.finditer(text):
        body = match.group(1)
        side = SIDE_BORDER.search(body)
        if side and int(side.group(1)) >= 2 and RADIUS.search(body):
            src.add(match.start(1) + side.start(), "P0-SIDE-STRIPE", "Rounded card with a colored side border.", "Drop either the side border or the radius.")
    if src.suffix in MARKUP:
        for match in CLASS_ATTR.finditer(text):
            if TW_SIDE.search(match.group(1)) and TW_ROUNDED.search(match.group(1)):
                src.add(match.start(), "P0-SIDE-STRIPE", "Rounded card with a colored side border.", "Drop either the side border or the radius.")
        for match in ICON_TEXT.finditer(text):
            tag = match.group(1) or match.group(3)
            content = match.group(2) if match.group(1) else match.group(4)
            emoji = EMOJI.search(content or "")
            if emoji:
                start = match.start(2) if match.group(1) else match.start(4)
                src.add(start + emoji.start(), "P0-EMOJI-ICON", f"Emoji used as an icon inside <{tag}>.", "Use a monoline SVG icon with currentColor, or remove it.")
        for match in FILLER.finditer(text):
            src.add(match.start(), "P0-FILLER", f"Filler text '{match.group()}'.", "Write real content from design/brief.md, or design a labelled empty state.")
        for match in METRIC.finditer(text):
            src.add(match.start(), "P0-METRIC", f"Unsourced marketing metric '{match.group()}'.", "Use a real, sourced number, or suppress with design-lint-disable P0-METRIC -- <source>.")
    for match in CDN.finditer(text):
        src.add(match.start(), "P0-PLACEHOLDER-CDN", f"Placeholder image CDN '{match.group()}'.", "Use a local asset or a labelled placeholder block.")


def check_p1_p2(src: Source) -> None:
    """P1 and P2 rules (TASK-002)."""


def apply_suppressions(src: Source) -> None:
    allowed: dict[int, set[str]] = {}
    for number, line in enumerate(src.text.splitlines(), start=1):
        match = SUPPRESS.search(line)
        if not match:
            continue
        ids = set(RULE_ID.findall(match.group(1)))
        if not COMMENT_END.sub("", match.group(2) or "").strip():
            src.findings.append(Finding(src.display, number, "P1-SUPPRESSION-NO-REASON", "P1", "design-lint-disable without a reason is ignored.", "Add the reason after --, for example: design-lint-disable P0-METRIC -- SLA in the contract."))
            continue
        allowed.setdefault(number, set()).update(ids)
        allowed.setdefault(number + 1, set()).update(ids)
    src.findings = [item for item in src.findings if item.rule not in allowed.get(item.line, set())]


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            if path.suffix.lower() in EXTENSIONS:
                yield path
            continue
        for folder, dirs, files in os.walk(path):
            dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
            for name in sorted(files):
                if Path(name).suffix.lower() in EXTENSIONS:
                    yield Path(folder) / name


def lint_paths(paths: list[Path], design: Path | None = None, tokens: Path | None = None) -> list[Finding]:
    allowed = declared_colors(design, tokens)
    token_file = tokens.resolve() if tokens and tokens.is_file() else None
    sources: list[Source] = []
    for path in iter_files(paths):
        if path.stat().st_size > MAX_BYTES:
            continue
        src = Source(display(path), path.suffix.lower(), path.read_text(encoding="utf-8", errors="replace"), path.resolve() == token_file)
        check_p0(src, allowed)
        check_p1_p2(src)
        apply_suppressions(src)
        sources.append(src)
    check_across_files(sources)
    findings = [item for src in sources for item in src.findings]
    return sorted(findings, key=lambda item: (item.file, item.line, item.rule))


def check_across_files(sources: list[Source]) -> None:
    """Rules that need every scanned file (TASK-002)."""


def summary(findings: list[Finding]) -> dict[str, int]:
    return {level: sum(1 for item in findings if item.severity == level) for level in ("P0", "P1", "P2")}


def render_text(findings: list[Finding]) -> str:
    lines = [f"{item.file}:{item.line}: {item.severity} {item.rule} {item.message} Fix: {item.suggestion}" for item in findings]
    counts = summary(findings)
    lines.append(f"design lint: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Anti-AI-slop design lint for UI source files.")
    parser.add_argument("paths", nargs="*", default=["."], help="files or folders (default: current folder)")
    parser.add_argument("--design", help="DESIGN.md whose colors are allowed (default: ./DESIGN.md when present)")
    parser.add_argument("--tokens", help="token stylesheet whose colors are allowed (default: ./design/tokens.css when present)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    paths = [Path(item) for item in args.paths]
    for given, default in ((args.design, "DESIGN.md"), (args.tokens, "design/tokens.css")):
        if given and not Path(given).is_file():
            print(f"error: {given} not found", file=sys.stderr)
            return 2
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(f"error: not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    design = Path(args.design) if args.design else Path("DESIGN.md")
    tokens = Path(args.tokens) if args.tokens else Path("design/tokens.css")
    findings = lint_paths(paths, design if design.is_file() else None, tokens if tokens.is_file() else None)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if args.format == "json":
        print(json.dumps({"findings": [asdict(item) for item in findings], "summary": summary(findings)}, ensure_ascii=True))
    else:
        print(render_text(findings))
    return 1 if summary(findings)["P0"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Notas para quem implementa:
- `run` de `support.py` roda o script com `cwd=root`, então `display()` gera caminhos relativos como `src/App.tsx`.
- `P0-EMOJI-ICON` em `<li>✨` cai na linha 2 do teste de formato porque `start(2)` aponta para o texto do `<li>`.
- Em `test_design_lint_allows_declared_brand_color`, o padrão `design/tokens.css` é lido mesmo sem `--tokens`. Por isso o teste apaga o arquivo antes da segunda rodada.

### TEST-001: cada P0 reprova
- Acceptance: AC-024
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_lint_flags_each_p0", "test_design_lint_usage_errors_exit_2", "test_design_lint_flags_p0_variants", "test_design_lint_keeps_legitimate_ui_clean_of_p0", "test_design_lint_section_nine_does_not_allowlist_forbidden_colors"]
- Expected: exit 0; cada uma das 7 regras P0 sai com 1 e é reportada; caminho e arquivo de tokens inexistentes saem com 2

### TEST-002: formato do achado e JSON
- Acceptance: AC-024, AC-027
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_lint_finding_shape_and_json"]
- Expected: exit 0; JSON com as seis chaves, linha correta e resumo; texto `index.html:2: P0 P0-EMOJI-ICON`

### TEST-003: exclusões e cor de marca
- Acceptance: AC-023, AC-026
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_lint_skips_vendor_and_build_folders", "test_design_lint_allows_declared_brand_color", "test_design_lint_allows_declared_brand_hex_and_gradient", "test_design_lint_reports_skipped_and_unreadable_files"]
- Expected: exit 0; só `src/App.tsx` reportado; `bg-violet-600` passa com tokens que declaram `#7c3aed` e reprova sem eles

### TEST-004: supressão com e sem motivo
- Acceptance: AC-030
- Task: TASK-001
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_lint_suppression_needs_a_reason", "test_design_lint_suppression_in_block_and_jsx_comments"]
- Expected: exit 0; linha 2 suprimida; linha 4 com `P0-METRIC`; linha 3 com `P1-SUPPRESSION-NO-REASON`

---

### TASK-002: Lint — regras P1, P2 e fixtures limpas
- Requirements: REQ-029, REQ-033
- Acceptance: AC-025, AC-029
- Files: agent-system/scripts/lint_design.py, agent-system/tests/test_design_lint.py
- Baseline: agent-system/scripts/lint_design.py=absent, agent-system/tests/test_design_lint.py=absent
- Depends on: TASK-001
- Verification: TEST-005, TEST-006
- Done when: TEST-005 e TEST-006 passam, e a suíte inteira passa em Windows e Linux no CI
- Gate: check_proofs TEST-005 TEST-006
- Status: done

#### Passos

1. Acrescente os testes abaixo em `agent-system/tests/test_design_lint.py`.
2. Rode `python agent-system/scripts/test_system.py test_design_lint_p1 test_design_lint_clean`. Esperado: `FAIL` em `test_design_lint_p1_p2_rules_only_warn`, porque `check_p1_p2` está vazio. O teste limpo deve passar já nesta etapa.
3. Implemente `check_p1_p2` e `check_across_files` com o código abaixo.
4. Rode de novo. Esperado: `3 passed, 0 failed`.
5. Regressão: `python agent-system/scripts/test_system.py`. Esperado: `ok`.

#### Teste (acrescentar)

```python
P1_P2_CASES = {
    "P1-RAW-COLOR": ("src/a.css", ".a {\n  color: #1f2937;\n}\n"),
    "P1-FONT-LITERAL": ("src/b.css", ".b {\n  font-family: Inter, sans-serif;\n}\n"),
    "P1-TRANSITION-ALL": ("src/c.css", ".c {\n  transition: all 200ms;\n}\n@media (prefers-reduced-motion: reduce) { .c { transition: none; } }\n"),
    "P1-OUTLINE-NONE": ("src/d.css", ".d:focus {\n  outline: none;\n}\n"),
    "P1-NO-REDUCED-MOTION": ("src/e.css", "@keyframes pop { from { opacity: 0; } to { opacity: 1; } }\n"),
    "P2-ACCENT-OVERUSE": ("src/f.css", "".join(f".f{n} {{ color: var(--color-accent); }}\n" for n in range(7))),
    "P2-UNIFORM-HOVER-SCALE": ("src/G.tsx", "".join(f'<div className="hover:scale-105">{n}</div>\n' for n in range(4))),
}


def test_design_lint_p1_p2_rules_only_warn() -> None:
    for rule, (relative, text) in P1_P2_CASES.items():
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            code, report, done = lint(root, relative)
            assert rule in rules(report), (rule, report)
            assert code == 0, (rule, done.stdout)
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "src/x.css", ".x {\n  color: #1f2937;\n  transition: all 1s;\n}\n@media (prefers-reduced-motion: reduce) { .x { transition: none; } }\n")
        code, report, _ = lint(root, "src")
        assert {"P1-RAW-COLOR", "P1-TRANSITION-ALL"} <= rules(report) and code == 0, report


def test_design_lint_font_count_across_files() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "design/tokens.css", ":root {\n  --font-display: 'Fraunces', serif;\n  --font-body: 'Source Sans 3', sans-serif;\n  --font-mono: 'IBM Plex Mono', monospace;\n}\n")
        write(root, "src/a.css", ".a { font-family: 'Comic Neue', cursive; }\n")
        code, report, _ = lint(root, ".", "--tokens", "design/tokens.css")
        assert "P1-FONT-COUNT" in rules(report) and code == 0, report


CLEAN_TOKENS = """:root {
  --color-surface: #f7f4ee;
  --color-ink: #1d1b18;
  --color-accent: #b4532a;
  --color-accent-ink: #ffffff;
  --font-display: 'Fraunces', Georgia, serif;
  --font-body: 'Source Sans 3', system-ui, sans-serif;
  --space-4: 16px;
  --radius-2: 6px;
  --duration-1: 120ms;
}
"""

CLEAN_PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<link rel="stylesheet" href="design/tokens.css">
<style>
  body { background: var(--color-surface); color: var(--color-ink); font-family: var(--font-body); }
  h1 { font-family: var(--font-display); }
  .cta { background: var(--color-accent); color: var(--color-accent-ink); border-radius: var(--radius-2);
         transition: background-color var(--duration-1) ease-out; }
  .cta:focus-visible { outline: 2px solid var(--color-ink); outline-offset: 2px; }
  @media (prefers-reduced-motion: reduce) { .cta { transition: none; } }
</style>
</head>
<body>
  <h1>Agenda da clínica em uma tela</h1>
  <p>Veja os horários de amanhã e confirme por WhatsApp.</p>
  <a class="cta" href="#agenda">Abrir a agenda de amanhã</a>
</body>
</html>
"""


def test_design_lint_clean_fixture_has_no_findings() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "design/tokens.css", CLEAN_TOKENS)
        write(root, "index.html", CLEAN_PAGE)
        code, report, _ = lint(root, ".")
        assert code == 0 and report["findings"] == [], report
```

#### Código (substitui os dois stubs)

```python
COLOR_FN = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|lch|lab)\(", re.I)
CSS_HEX = re.compile(r"(?<=[\s:(,\[\"'])#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_-])")
TOKEN_SCOPE = re.compile(r"(?::root|@theme)[^{]*\{[^{}]*\}")
FONT_FAMILY = re.compile(r"font-family\s*:\s*([^;}\n]+)|fontFamily\s*:\s*[\"'`]([^\"'`]+)", re.I)
TRANSITION_ALL = re.compile(r"transition\s*:\s*all\b|\btransition-all\b", re.I)
OUTLINE_NONE = re.compile(r"outline\s*:\s*(?:none|0)\b|\boutline-none\b", re.I)
FOCUS_VISIBLE = re.compile(r":focus-visible|focus-visible:")
MOTION = re.compile(r"@keyframes|\banimation\s*:|\btransition\s*:|\banimate-[a-z]|\btransition(?:-[a-z]+)?(?=[\s\"'])")
REDUCED = re.compile(r"prefers-reduced-motion|motion-reduce:|motion-safe:")
ACCENT = re.compile(r"var\(--(?:color-)?accent\)|\b(?:bg|text|border)-accent\b")
HOVER_SCALE = re.compile(r"\bhover:scale-\d+\b|:hover\s*\{[^}]*transform\s*:\s*scale\(")
KEYWORD_VALUES = ("var(", "inherit", "initial", "unset")
# Family tokens such as --font-display; size, weight, and spacing tokens share the prefix and are skipped.
FONT_TOKEN = re.compile(r"--font-(?![\w-]*(?:size|weight|leading|tracking|line|scale|step))[\w-]+\s*:\s*([^;}\n]+)", re.I)


def token_spans(text: str) -> list[tuple[int, int]]:
    return [match.span() for match in TOKEN_SCOPE.finditer(text)]


def in_spans(offset: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= offset < end for start, end in spans)


def check_p1_p2(src: Source) -> None:
    text = src.text
    spans = token_spans(text)
    p0_lines = {item.line for item in src.findings if item.rule == "P0-INDIGO"}
    if not src.is_tokens:
        for regex in (CSS_HEX, COLOR_FN):
            for match in regex.finditer(text):
                if in_spans(match.start(), spans) or src.line(match.start()) in p0_lines:
                    continue
                if text[max(0, match.start() - 6):match.start()].lower().endswith(("href=\"", "href='")):
                    continue
                src.add(match.start(), "P1-RAW-COLOR", f"Literal color {match.group().rstrip('(')} outside the tokens.", "Reference a color token, for example var(--color-ink).")
        for match in FONT_FAMILY.finditer(text):
            value = (match.group(1) or match.group(2) or "").strip()
            if in_spans(match.start(), spans) or value.startswith(("var(", "inherit", "initial", "unset")):
                continue
            src.add(match.start(), "P1-FONT-LITERAL", f"Literal font-family {value[:40]}.", "Use var(--font-display) or var(--font-body).")
    for match in TRANSITION_ALL.finditer(text):
        src.add(match.start(), "P1-TRANSITION-ALL", "transition: all animates every property.", "List the properties, for example transition: background-color 120ms ease-out.")
    if not FOCUS_VISIBLE.search(text):
        for match in OUTLINE_NONE.finditer(text):
            src.add(match.start(), "P1-OUTLINE-NONE", "Focus outline removed with no :focus-visible style in this file.", "Add a :focus-visible outline of at least 2px.")
    motion = MOTION.search(text)
    if motion and not REDUCED.search(text):
        src.add(motion.start(), "P1-NO-REDUCED-MOTION", "Motion without a prefers-reduced-motion fallback in this file.", "Add @media (prefers-reduced-motion: reduce) that removes or shortens the motion.")
    accents = list(ACCENT.finditer(text))
    if len(accents) > 6:
        src.add(accents[6].start(), "P2-ACCENT-OVERUSE", f"Accent used {len(accents)} times in one file.", "Keep the accent for the one or two things that must stand out.")
    scales = list(HOVER_SCALE.finditer(text))
    if len(scales) > 3:
        src.add(scales[3].start(), "P2-UNIFORM-HOVER-SCALE", f"The same hover scale on {len(scales)} elements.", "Give hover feedback that fits each element; reserve scale for one.")


def first_family(value: str) -> str:
    return value.split(",")[0].strip().strip("\"'`").lower()


def check_across_files(sources: list[Source]) -> None:
    seen: list[str] = []
    for src in sources:
        declared = [(match.start(), match.group(1)) for match in FONT_TOKEN.finditer(src.text)]
        literal = [(match.start(), match.group(1) or match.group(2)) for match in FONT_FAMILY.finditer(src.text)]
        for offset, raw in sorted(declared + literal):
            value = (raw or "").strip()
            if value.startswith(KEYWORD_VALUES):
                continue
            family = first_family(value)
            if family and family not in seen:
                seen.append(family)
                if len(seen) == 4:
                    src.add(offset, "P1-FONT-COUNT", f"Fourth font family '{family}' ({', '.join(seen)}).", "Keep at most three families: display, body, and one outlier.")
```

Notas:
- `apply_suppressions` roda depois de `check_across_files` (já feito na TASK-001), então a supressão vale também para `P1-FONT-COUNT`.
- Os tokens declaram fontes como custom properties (`--font-display: 'Fraunces'`), não como `font-family:`; por isso a contagem também lê `FONT_TOKEN`.
- Correção depois do ensaio (FIND-001 de `docs/reviews/design-pipeline-acceptance.md`): cada arquivo em `design/directions/` é um escopo próprio na contagem (`font_scope`), porque as prévias são alternativas, não partes de um produto. Teste: `test_design_lint_counts_fonts_per_direction`.
- O arquivo de tokens só entra na contagem de fontes quando está dentro dos caminhos varridos. No teste ele está, porque a varredura é sobre `.`.

### TEST-005: P1 e P2 só avisam
- Acceptance: AC-025
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_lint_p1_p2_rules_only_warn", "test_design_lint_font_count_across_files", "test_design_lint_counts_fonts_per_direction", "test_design_lint_p1_variants_in_css_in_js_and_prose", "test_design_lint_p2_thresholds_at_the_boundary"]
- Expected: exit 0; cada regra P1/P2 é reportada e o lint sai 0

### TEST-006: fixture limpa e suíte completa
- Acceptance: AC-029
- Task: TASK-002
- Command: ["python", "agent-system/scripts/test_system.py"]
- Expected: exit 0 e `ok`; a fixture limpa não tem achados e a fixture de marca roxa (TEST-003) passa

---

### TASK-003: Hook informativo do lint
- Requirements: REQ-032
- Acceptance: AC-028
- Files: agent-system/scripts/hook.py, agent-system/scripts/init_project.py, agent-system/tests/test_design_lint.py
- Baseline: agent-system/scripts/hook.py=e0209d582f, agent-system/scripts/init_project.py=acfcf62aeb, agent-system/tests/test_design_lint.py=absent
- Out of scope: alterar `hooks/hooks.json` ou `hooks/claude-hooks.json`; os dois já chamam `hook.py` no `afterFileEdit` e no `PostToolUse` de Edit/Write/MultiEdit
- Stop if: o `change-request` da limitação do Cursor (ver cabeçalho) ainda estiver aberto
- Depends on: TASK-002
- Verification: TEST-007
- Done when: TEST-007 passa e `test_claude_hook_adapter` continua verde
- Gate: check_proofs TEST-007
- Status: done

#### Passos

1. Acrescente o teste abaixo.
2. Rode `python agent-system/scripts/test_system.py test_design_lint_hook`. Esperado: FAIL, porque a saída do PostToolUse é `{}`.
3. Aplique as mudanças em `hook.py` e `init_project.py`.
4. Rode de novo. Esperado: `1 passed`.
5. Regressão: `python agent-system/scripts/test_system.py test_claude test_audit`. Esperado: `ok`.

#### Teste (acrescentar)

```python
import os  # noqa: E402
import subprocess  # noqa: E402

from support import PYTHON, SCRIPTS, opt_in  # noqa: E402


def hook(payload: dict, project_dir: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in {"CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"}}
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps(payload), text=True, capture_output=True, check=False, env=env, timeout=20)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def test_design_lint_hook_reports_without_blocking() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        hero = write(root, "src/Hero.tsx", "export const Hero = () => <h1>\U0001F680 Agenda</h1>;\n")
        notes = write(root, "notes.md", "\U0001F680 lorem ipsum\n")
        common = {"session_id": "s", "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_response": {"success": True}}
        reply = hook({**common, "tool_input": {"file_path": str(hero)}}, root)
        context = reply["hookSpecificOutput"]
        assert context["hookEventName"] == "PostToolUse"
        assert "P0-EMOJI-ICON" in context["additionalContext"] and "Hero.tsx" in context["additionalContext"]
        assert hook({**common, "tool_input": {"file_path": str(notes)}}, root) == {}
        # Cursor: no channel back to the agent; the summary goes to the timeline of an opted-in project.
        opt_in(root)
        cursor = {"hook_event_name": "afterFileEdit", "workspace_roots": [str(root)], "file_path": str(hero)}
        done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps(cursor), text=True, capture_output=True, check=False, timeout=20)
        assert done.returncode == 0 and json.loads(done.stdout) == {}, done.stdout
        timeline = (root / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        assert '"DESIGN_LINT"' in timeline and "Agenda" not in timeline
```

#### Código

Em `agent-system/scripts/hook.py`, logo após `def is_claude`:

```python
LINT_SHOWN = 8  # findings passed to the agent; the rest is a count


def design_lint(path: str, roots: list[Path]) -> str:
    """Informational lint summary for one edited UI file. Empty when clean, not a UI file, or on any error."""
    try:
        import lint_design

        file = Path(path)
        if file.suffix.lower() not in lint_design.EXTENSIONS or not file.is_file():
            return ""
        resolved = file.resolve()
        root = next((item for item in roots if item.resolve() in resolved.parents), file.parent)
        design, tokens = root / "DESIGN.md", root / "design" / "tokens.css"
        findings = lint_design.lint_paths([file], design if design.is_file() else None, tokens if tokens.is_file() else None)
    except Exception:
        return ""
    if not findings:
        return ""
    counts = lint_design.summary(findings)
    lines = [f"Design lint (informational) for {file.name}: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2. P0 blocks review."]
    lines += [f"line {item.line}: {item.rule} {item.message} Fix: {item.suggestion}" for item in findings[:LINT_SHOWN]]
    if len(findings) > LINT_SHOWN:
        lines.append(f"{len(findings) - LINT_SHOWN} more; run lint_design.py {file.name} for the full list.")
    return "\n".join(lines)
```

Em `to_claude`, antes do `return {}`:

```python
    lint = reply.get("design_lint")
    if event == "PostToolUse" and lint:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": redact(lint, 1500)}}
```

No ramo `afterFileEdit` de `handle`, troque o `return {}` final por:

```python
        report = design_lint(path, workspace_roots(payload)) if path else ""
        if report:
            for root in roots:
                log(root, payload, "DESIGN_LINT", report.splitlines()[0], result="warning", files=[path])
            return {"design_lint": report}
        return {}
```

Em `main`, no ramo do Cursor, troque `emit(handle(payload))` por:

```python
            reply = handle(payload)
            reply.pop("design_lint", None)  # Cursor's afterFileEdit has no channel back to the agent
            emit(reply)
```

Em `agent-system/scripts/init_project.py`, acrescente `"lint_design.py",` em `COPY_SCRIPTS`, logo após `"check_drift.py",`.

Notas:
- O resumo gravado na timeline é só a primeira linha (nome do arquivo e contagens). Ele não contém trecho do arquivo, como já exige a docstring do hook.
- O lint roda mesmo sem opt-in, porque é informativo e barato. A timeline só é gravada com opt-in, como os outros eventos.
- `redact` já existe em `lib`. Ele limita o tamanho e remove padrões de segredo.

### TEST-007: hook mostra achados e não bloqueia
- Acceptance: AC-028
- Task: TASK-003
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_lint_hook_reports_without_blocking", "test_claude_hook_adapter", "test_design_lint_hook_skips_files_outside_the_workspace", "test_design_lint_is_fast_on_large_minified_files"]
- Expected: exit 0; o Claude recebe `additionalContext` com `P0-EMOJI-ICON`; `.md` não dispara o lint; o Cursor recebe `{}` e a timeline ganha `DESIGN_LINT` sem trecho do arquivo

---

### TASK-004: Referências compartilhadas e créditos
- Requirements: REQ-021, REQ-022
- Acceptance: AC-018
- Files: skills/design/references/anti-slop.md, skills/design/references/design-md-format.md, skills/design/references/microcopy.md, skills/design/references/CREDITS.md, skills/design/references/examples/editorial-calm.md, skills/design/references/examples/technical-dense.md, skills/design/references/examples/warm-tactile.md, skills/design/references/examples/bold-graphic.md, agent-system/tests/test_design_skills.py
- Baseline: skills/design/references/anti-slop.md=absent, skills/design/references/design-md-format.md=absent, skills/design/references/microcopy.md=absent, skills/design/references/CREDITS.md=absent, skills/design/references/examples/editorial-calm.md=absent, skills/design/references/examples/technical-dense.md=absent, skills/design/references/examples/warm-tactile.md=absent, skills/design/references/examples/bold-graphic.md=absent, agent-system/tests/test_design_skills.py=absent
- Out of scope: `skills/design/SKILL.md` (TASK-009). Como a pasta `skills/design/` só passa a ter `SKILL.md` na TASK-009, esta tarefa cria só `references/`; os testes de skills ignoram pastas sem `SKILL.md`.
- Stop if: algum exemplo precisar citar nome, logo ou paleta proprietária de uma marca real
- Depends on: TASK-002
- Verification: TEST-008
- Done when: TEST-008 passa
- Gate: check_proofs TEST-008
- Status: done

#### Conteúdo exigido

`anti-slop.md`:
- Os 7 P0 com o ID exato do lint (`P0-INDIGO` … `P0-PLACEHOLDER-CDN`), o porquê de cada um e a correção.
- Os P1 e P2 do lint com seus IDs.
- Os sinais estruturais que o lint não vê: sequência Hero → Features → Pricing → FAQ → CTA sem variação; grade de 3 cards iguais com ícone em cima; hero com tudo centralizado; nav e rodapé padrão; cromo de navegador ou celular redesenhado; layout simétrico sem tensão.
- A regra 80/20 e o teste do print ("alguém de fora reconhece o produto?").
- A sintaxe `design-lint-disable <REGRA> -- motivo`.
- O comando do lint: `python <plugin>/agent-system/scripts/lint_design.py <caminho>`, ou `.cursor/agent-system/scripts/lint_design.py` no projeto com init.

`design-md-format.md`:
- Os 9 títulos exatamente assim: `## 1. Tema visual e atmosfera`, `## 2. Cor`, `## 3. Tipografia`, `## 4. Espaçamento e grid`, `## 5. Layout e composição`, `## 6. Componentes`, `## 7. Movimento e interação`, `## 8. Voz e microcopy`, `## 9. Anti-padrões`.
- O que cada seção deve conter: papel semântico de cada cor e par `-ink`; escala tipográfica em tabela; escala de espaço em múltiplos de 4px; estados de componente (default, hover, focus-visible, active, disabled, loading, erro); a escolha distintiva na seção 1; na seção 7, citação de `apple-design` quando houver gesto ou mola; na seção 9, os P0 mais os anti-padrões do projeto.
- O front matter `status: draft | approved`.

`microcopy.md` (adaptado de no-ai-slop):
- Verbo específico no botão, sem "Get started" ou "Saiba mais" soltos.
- Palavras proibidas em UI (leverage, seamless, robust, empower, unlock, revolutionize, e equivalentes em português).
- O teste de portabilidade aplicado a títulos.
- Mensagens de erro com causa e próximo passo.
- Estado vazio com uma ação.
- Nada de métrica ou depoimento inventado.

`examples/*.md`: quatro DESIGN.md completos no formato de 9 seções, para produtos fictícios com estéticas diferentes (editorial calmo, técnico denso, quente e tátil, gráfico ousado). Cada um usa escala de espaço em múltiplos de 4px e no máximo 3 famílias de fonte, e nenhum usa os hex de `AI_INDIGO`.

`CREDITS.md`: uma linha por fonte com nome, link, licença e o que foi adaptado. As fontes são VoltAgent/awesome-design-md (MIT, formato), nexu-io/open-design (Apache-2.0: `craft/anti-ai-slop.md`, `discovery-question-form`, `reference-design-contract`, `critique-theater`), Nutlope/hallmark (MIT: autocrítica de 6 eixos e slop-test), nextlevelbuilder/ui-ux-pro-max-skill (prioridades, dials e master + override; adaptado como ideia, sem copiar dados) e petergyang/no-ai-slop (MIT: microcopy e formato de eval). Para Apache-2.0, registre que houve modificação, como a licença exige.

#### Teste (`agent-system/tests/test_design_skills.py`)

```python
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
        ("nextlevelbuilder/ui-ux-pro-max-skill", ""),
        ("petergyang/no-ai-slop", "MIT"),
    ):
        line = next((item for item in credits.splitlines() if source in item), "")
        assert line and license_name in line, source
```

### TEST-008: referências e créditos
- Acceptance: AC-018
- Task: TASK-004
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_references_and_credits"]
- Expected: exit 0; 7 P0 citados; 9 seções na ordem em `design-md-format.md` e em cada exemplo; nenhum exemplo com índigo padrão; 5 fontes creditadas com licença

---

### TASK-005: Skill design-discovery
- Requirements: REQ-001, REQ-002, REQ-003, REQ-004
- Acceptance: AC-001, AC-002, AC-003, AC-004
- Files: skills/design-discovery/SKILL.md, skills/design-discovery/references/brief-template.md, agent-system/tests/test_design_skills.py
- Baseline: skills/design-discovery/SKILL.md=absent, skills/design-discovery/references/brief-template.md=absent, agent-system/tests/test_design_skills.py=absent
- Depends on: TASK-004
- Verification: TEST-009
- Done when: TEST-009 passa; o comportamento é confirmado no ensaio da TASK-011
- Gate: check_proofs TEST-009
- Status: done

#### Conteúdo exigido em `SKILL.md`

- Front matter com `name: design-discovery` e uma `description` com gatilhos em inglês e português (entrevista de design, brief, referências, "quero um visual", começar o design).
- Quando usar: projeto ou tela nova sem `design/brief.md` aprovado. Quando não usar: brief aprovado (vá para `design-directions`).
- Fluxo:
  1. Ler o pedido, README, código e brief anterior. Toda resposta que já der para obter vira `inferido` e não vira pergunta.
  2. Perguntar em uma mensagem só, com **at most 5 questions**, cada uma com uma **recommended answer** já preenchida e **at most 7 options**, rotuladas em palavras leigas. Inclua uma tabela de tradução jargão → palavra comum, por exemplo "editorial" → "parece revista".
  3. Pedir **2 to 3 references** (URL ou imagem). Se não houver nenhuma, registrar no brief que a direção parte só do brief e seguir.
  4. Para cada referência, preencher Keep / Change / Do not copy. Não copiar logo, texto, preço nem tela proprietária.
  5. Gravar `design/brief.md` a partir de `references/brief-template.md`, com `status: draft`. Mostrar o brief e mudar para `status: approved` só depois do ok do usuário.
- Usar no Claude Code a ferramenta de pergunta de escolha fechada quando ela existir; senão, uma lista numerada com a recomendação marcada.
- Link para `../design/references/microcopy.md` (tom de voz) e para `../design-directions/SKILL.md` como próximo passo.

`references/brief-template.md`: front matter `status: draft`; seções `## Público`, `## Tarefa principal`, `## Tom de voz`, `## Densidade`, `## Idioma`, `## Restrições` e `## Referências` (com a tabela `| Referência | Keep | Change | Do not copy |`); e a legenda de origem `fornecido | observado | inferido`.

#### Teste (acrescentar em `test_design_skills.py`)

```python
def skill(name: str) -> str:
    return read(PLUGIN / "skills" / name / "SKILL.md")


def test_design_discovery_contract() -> None:
    text = skill("design-discovery")
    for needle in ("at most 5 questions", "recommended answer", "at most 7 options", "2 to 3 references", "design/brief.md", "status: approved", "inferido"):
        assert needle in text, needle
    template = read(PLUGIN / "skills" / "design-discovery" / "references" / "brief-template.md")
    for needle in ("status: draft", "## Público", "## Tarefa principal", "## Tom de voz", "## Densidade", "## Idioma", "## Restrições", "## Referências", "Keep", "Change", "Do not copy", "fornecido", "observado", "inferido"):
        assert needle in template, needle
```

### TEST-009: contrato da design-discovery
- Acceptance: AC-001, AC-003
- Task: TASK-005
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_discovery_contract", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0

---

### TASK-006: Skill design-directions
- Requirements: REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010
- Acceptance: AC-005, AC-006, AC-007, AC-008, AC-009
- Files: skills/design-directions/SKILL.md, skills/design-directions/references/directions.md, agent-system/tests/test_design_skills.py
- Baseline: skills/design-directions/SKILL.md=absent, skills/design-directions/references/directions.md=absent, agent-system/tests/test_design_skills.py=absent
- Depends on: TASK-005
- Verification: TEST-010
- Done when: TEST-010 passa
- Gate: check_proofs TEST-010
- Status: done

#### Conteúdo exigido

`SKILL.md`:
- Entrada: `design/brief.md` com `status: approved`. Sem isso, mandar para `design-discovery`.
- Gerar 3 direções. Cada par difere em pelo menos dois dos quatro eixos (macroestrutura de layout, família tipográfica de display, temperatura da paleta, densidade). Uma diferença só de cor não conta. Antes de gravar, preencher uma matriz direção × eixo e conferir.
- Arquivos `design/directions/a.html`, `b.html`, `c.html` e `index.html`, que mostra as três lado a lado em `<iframe>` relativos.
- HTML autocontido: CSS inline, sem `<script src>` nem `<img src>` externos. Fontes externas só com fallback local. Conteúdo real do brief.
- Comentário no topo de cada arquivo, no formato `<!-- direction: <nome> | stance: <uma frase> | distinctive: <o 20%> | variety: N | motion: N | density: N | axes: layout=..., display=..., palette=..., density=... -->`.
- Rodar o lint em `design/directions/`. Nenhum P0 pode ficar aberto.
- **Stop and wait** pela escolha. Não criar `DESIGN.md`.
- Ajuste: regenerar só o arquivo escolhido e atualizar o comentário. Pedido de mistura: explicar o risco e entregar uma única versão coerente.
- Próximo passo: `../design-system/SKILL.md`.

`references/directions.md`: tabela dos dials (variedade, movimento, densidade, de 1 a 10) com o efeito de baixo, médio e alto. Na densidade, a escala de espaço: baixo 24–96px, médio 16–64px, alto 8–32px. Catálogo curto de macroestruturas para variar (coluna editorial, split assimétrico, índice ou tabela, canvas ou mapa, feed denso, narrativa em capítulos). Esqueleto mínimo de `index.html`.

#### Teste (acrescentar)

```python
def test_design_directions_contract() -> None:
    text = skill("design-directions")
    for needle in ("design/directions/a.html", "b.html", "c.html", "index.html", "at least two", "layout", "display", "palette", "density", "Stop and wait", "DESIGN.md", "lint_design.py", "variety", "motion"):
        assert needle in text, needle
    reference = read(PLUGIN / "skills" / "design-directions" / "references" / "directions.md")
    assert "24" in reference and "96" in reference and "8" in reference and "32" in reference
```

### TEST-010: contrato da design-directions
- Acceptance: AC-005, AC-007
- Task: TASK-006
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_directions_contract", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0

---

### TASK-007: Skill design-system
- Requirements: REQ-011, REQ-012, REQ-013, REQ-014, REQ-015
- Acceptance: AC-010, AC-011, AC-012, AC-013
- Files: skills/design-system/SKILL.md, skills/design-system/references/tokens-template.css, agent-system/tests/test_design_skills.py
- Baseline: skills/design-system/SKILL.md=absent, skills/design-system/references/tokens-template.css=absent, agent-system/tests/test_design_skills.py=absent
- Depends on: TASK-006
- Verification: TEST-011
- Done when: TEST-011 passa
- Gate: check_proofs TEST-011
- Status: done

#### Conteúdo exigido

`SKILL.md`:
- Entrada: a direção escolhida em `design/directions/`.
- Se `DESIGN.md` já existir: ler, mostrar a diferença por seção e sobrescrever só com confirmação explícita.
- Gravar `DESIGN.md` na raiz, seguindo `../design/references/design-md-format.md`. A seção 1 traz a escolha distintiva em uma frase concreta; a seção 9 traz os P0 do lint mais os anti-padrões do projeto.
- Gravar `design/tokens.css` a partir de `references/tokens-template.css`. Todo valor citado em `DESIGN.md` existe nos tokens com o mesmo valor. Espaço em múltiplos de 4px. No máximo 3 famílias de fonte. Cada cor de fundo de texto tem par `-ink` com contraste de pelo menos 4.5:1; incluir a fórmula de luminância relativa da WCAG para conferir à mão.
- Exceções em `design/pages/<pagina>.md`, citando a regra substituída e o motivo.
- `status: approved` no DESIGN.md só depois do ok do usuário.
- Próximo passo: `../design-review/SKILL.md` sobre a direção, depois `ui-ux` para as telas.

`references/tokens-template.css`: `:root` com grupos comentados — cor (`--color-surface`, `--color-ink`, `--color-muted`, `--color-accent`, `--color-accent-ink`, `--color-danger`, `--color-danger-ink`, `--color-focus`), fonte (`--font-display`, `--font-body`, `--font-mono`), escala de texto, espaço (`--space-1: 4px` … `--space-12: 96px`), raio, sombra e duração. Os valores são placeholders neutros válidos, sem índigo.

#### Teste (acrescentar)

```python
def test_design_system_contract() -> None:
    text = skill("design-system")
    for needle in ("DESIGN.md", "design/tokens.css", "design/pages/", "4.5:1", "multiples of 4px", "at most 3", "confirmation", "status: approved", "design-md-format.md"):
        assert needle in text, needle
    template = read(PLUGIN / "skills" / "design-system" / "references" / "tokens-template.css")
    assert ":root" in template and "--color-accent-ink" in template and "--space-1: 4px" in template
    hexes = {lint_design.norm_hex(item) for item in lint_design.ANY_HEX.findall(template)}
    assert not hexes & lint_design.AI_INDIGO
```

### TEST-011: contrato da design-system
- Acceptance: AC-010, AC-012
- Task: TASK-007
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_system_contract", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0

---

### TASK-008: Skill design-review
- Requirements: REQ-016, REQ-017
- Acceptance: AC-014
- Files: skills/design-review/SKILL.md, skills/design-review/references/review-checklist.md, agent-system/tests/test_design_skills.py
- Baseline: skills/design-review/SKILL.md=absent, skills/design-review/references/review-checklist.md=absent, agent-system/tests/test_design_skills.py=absent
- Depends on: TASK-004
- Verification: TEST-012
- Done when: TEST-012 passa
- Gate: check_proofs TEST-012
- Status: done

#### Conteúdo exigido

`SKILL.md`:
- Os seis eixos com nota de 1 a 5 (postura, hierarquia, execução, especificidade, contenção, variedade) e a pergunta de cada um. Nota **below 3** em qualquer eixo obriga a revisar e reavaliar, com no máximo **3 passes**.
- Depois, a checklist de `references/review-checklist.md`, as regras de `../design/references/microcopy.md` e o lint (`lint_design.py`). P0 aberto impede a entrega.
- Relato **in prose**, no idioma do usuário: o que verificou, o que corrigiu, as notas finais e o que ficou aberto com o motivo. Não gravar arquivo de pontuação nem inventar painel de revisores.

`references/review-checklist.md`: P0, P1 e P2 em forma de pergunta sim/não (todas devem dar "não"). Inclui as checagens que o lint não faz: hierarquia em 2 segundos, contraste de corpo 4.5:1 e de texto grande e foco 3:1, alvo de toque de 44px, rótulo de botão sem quebrar linha de 320 a 1920px, nenhum scroll horizontal, os quatro estados de cada componente e texto entre 45 e 75 caracteres por linha.

#### Teste (acrescentar)

```python
def test_design_review_contract() -> None:
    text = skill("design-review")
    for axis in ("hierarchy", "execution", "specificity", "restraint", "variety"):
        assert axis in text.lower(), axis
    for needle in ("below 3", "3 passes", "in prose", "lint_design.py", "microcopy.md"):
        assert needle in text, needle
    checklist = read(PLUGIN / "skills" / "design-review" / "references" / "review-checklist.md")
    for needle in ("4.5:1", "3:1", "44px", "320", "1920", "45", "75"):
        assert needle in checklist, needle
```

### TEST-012: contrato da design-review
- Acceptance: AC-014
- Task: TASK-008
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_review_contract", "test_skills_follow_the_agent_skills_specification"]
- Expected: exit 0

---

### TASK-009: Orquestração /design, ui-ux e documentação
- Requirements: REQ-018, REQ-019, REQ-020
- Acceptance: AC-013, AC-015, AC-016, AC-017
- Files: skills/design/SKILL.md, skills/ui-ux/SKILL.md, skills/help/SKILL.md, README.md, README.pt-BR.md, rules/01-request-classification.mdc, agent-system/tests/test_design_skills.py
- Baseline: skills/design/SKILL.md=absent, skills/ui-ux/SKILL.md=9a200b4b16, skills/help/SKILL.md=a25c0fa653, README.md=971f059d12, README.pt-BR.md=634788d921, rules/01-request-classification.mdc=d7e545cf23, agent-system/tests/test_design_skills.py=absent
- Depends on: TASK-005, TASK-006, TASK-007, TASK-008
- Verification: TEST-013
- Done when: TEST-013 passa
- Gate: check_proofs TEST-013
- Status: done

#### Conteúdo exigido

`skills/design/SKILL.md`:
- Encadeia `design-discovery` → `design-directions` → `design-system` → `design-review`, nessa ordem e com links relativos.
- Pula a etapa cujo artefato já tem `status: approved` (`design/brief.md`, `DESIGN.md`). As direções contam como concluídas quando `design/directions/` existe e o usuário já escolheu.
- Para nas perguntas da entrevista, na escolha de direção e na aprovação do DESIGN.md.
- Lista as referências compartilhadas (`references/anti-slop.md`, `design-md-format.md`, `microcopy.md`, `examples/`, `CREDITS.md`).
- Diz o que vem depois: `ui-ux` tela por tela, ou o agente `frontend-implementer`.

`skills/ui-ux/SKILL.md`, novos passos no início:
- Se existir `DESIGN.md`: ler `DESIGN.md`, `design/tokens.css` e `design/pages/<pagina>.md` quando houver (a exceção vence). Usar só os tokens para cor, fonte, espaço, raio, sombra e duração.
- Se não existir `DESIGN.md` e a tarefa cria interface visual nova: recomendar `/design` antes. Mudança pequena em interface que já tem sistema visual próprio segue sem essa recomendação.
- Antes de encerrar: rodar `lint_design.py` nos arquivos alterados. Nenhum P0 pode ficar aberto.
- Manter os passos atuais: estados, acessibilidade, verificação no navegador.

`skills/help/SKILL.md`, `README.md`, `README.pt-BR.md`: acrescentar `/design`, `/design-discovery`, `/design-directions`, `/design-system` e `/design-review`. Trocar o fluxo de interface para `/design` → você escolhe a direção → `/ui-ux` (com `/ui-ux-experiment` mantido para comparar variantes de uma tela). Acrescentar uma linha sobre `lint_design.py`.

`rules/01-request-classification.mdc`: na linha "Mid-cycle", acrescentar `design` antes de `ui-ux` para interface visual nova sem `DESIGN.md`.

#### Teste (acrescentar)

```python
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
```

### TEST-013: orquestração e ui-ux
- Acceptance: AC-015, AC-017
- Task: TASK-009
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_orchestration_and_ui_ux", "test_skills_follow_the_agent_skills_specification", "test_init_skill_list_matches_skills_folder"]
- Expected: exit 0

---

### TASK-010: Agentes designer, frontend-implementer e design-reviewer
- Requirements: REQ-023, REQ-024, REQ-025, REQ-026
- Acceptance: AC-019, AC-020, AC-021, AC-022
- Files: agents/designer.md, agents/frontend-implementer.md, agents/design-reviewer.md, agent-system/agents.json, agents/orchestrator.md, agent-system/docs/contracts.md, agent-system/scripts/test_system.py, agent-system/tests/test_design_skills.py
- Baseline: agents/designer.md=absent, agents/frontend-implementer.md=absent, agents/design-reviewer.md=absent, agent-system/agents.json=134bf46d98, agents/orchestrator.md=fadc62216b, agent-system/docs/contracts.md=8d76dfa450, agent-system/scripts/test_system.py=4d93dd9434, agent-system/tests/test_design_skills.py=absent
- Depends on: TASK-009
- Verification: TEST-014
- Done when: TEST-014 passa e a suíte inteira continua verde
- Gate: check_proofs TEST-014
- Status: done

#### Conteúdo exigido

`agents/designer.md`:
- Front matter `name: designer`, `description` com "Use proactively for a new visual interface without an approved DESIGN.md", e `tools: Read, Grep, Glob, Write, Edit, Bash`.
- Corpo: roda `design-discovery`, `design-directions` e `design-system`. Só escreve em `design/` e `DESIGN.md`. **Does not write production code.** Para na escolha de direção e devolve `status: needs_decision`.

`agents/frontend-implementer.md`:
- Front matter `name: frontend-implementer`, sem restrição de tools (como `implementer`).
- Corpo: uma tela ou tarefa por vez. Lê `DESIGN.md`, `design/tokens.css` e a exceção da página. Só tokens. Cobre os estados empty, loading, error e success. Roda `lint_design.py` nos arquivos alterados e inclui a saída no handoff. Com P0 aberto, devolve `status: blocked`. Segue `ui-ux` e `tdd` como o `implementer`.

`agents/design-reviewer.md`:
- Front matter `name: design-reviewer` e `tools: Read, Grep, Glob, Bash, Write` (sem Edit, MultiEdit e NotebookEdit; Write só para o relatório de revisão, como o `reviewer`).
- Corpo: independente. Compara a tela com `DESIGN.md` e `design/brief.md` e roda `design-review` e o lint. Achados `FIND-NNN` com Severity e Location (arquivo:linha). **Does not fix.** P0 do lint aberto = `status: FAIL`.

`agent-system/agents.json`: três entradas no formato das existentes (`type: custom`, `status: active`, `scope: user`, `purpose`, `recommended_for`, `dependencies`), na ordem `designer`, `frontend-implementer`, `design-reviewer`, depois de `security-reviewer`. `created_at` com a data da implementação.

`agent-system/scripts/test_system.py`, `test_static`: estender a lista esperada para `[..., "security-reviewer", "designer", "frontend-implementer", "design-reviewer"]`.

`agents/orchestrator.md`: na lista de delegação e em "Specialists", acrescentar os três com a regra de roteamento da REQ-026 (interface visual nova sem `DESIGN.md` aprovado → `designer`; implementação de tela → `frontend-implementer`; revisão de design → `design-reviewer`, além do `reviewer` de sempre).

`agent-system/docs/contracts.md`: uma seção `### <nome>` para cada agente novo, no formato das existentes, com entrada e saída.

#### Teste (acrescentar)

```python
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
```

### TEST-014: agentes registrados, restritos e roteados
- Acceptance: AC-019, AC-021, AC-022
- Task: TASK-010
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_agents_contract", "test_static", "test_registry_matches_agent_files"]
- Expected: exit 0

---

### TASK-011: Ensaio de aceitação com amostra versionada
- Requirements: REQ-001, REQ-005, REQ-006, REQ-008, REQ-011, REQ-012, REQ-016, REQ-019, REQ-024, REQ-025
- Acceptance: AC-001, AC-002, AC-004, AC-005, AC-006, AC-007, AC-008, AC-009, AC-010, AC-011, AC-013, AC-014, AC-016, AC-020, AC-021
- Files: agent-system/tests/samples/design-sample/, agent-system/tests/test_design_skills.py, docs/reviews/design-pipeline-acceptance.md
- Baseline: agent-system/tests/samples/design-sample/=absent, agent-system/tests/test_design_skills.py=absent, docs/reviews/design-pipeline-acceptance.md=absent
- Out of scope: corrigir as skills dentro desta tarefa. Defeito encontrado vira `FIND-NNN` no relatório e volta para a tarefa da skill.
- Stop if: TASK-001 a TASK-010 não estiverem `done`
- Depends on: TASK-010
- Verification: TEST-015, TEST-016
- Done when: TEST-015 passa sobre a amostra e o relatório registra cada AC do ensaio como observado ou falho
- Gate: check_proofs TEST-015
- Status: done

#### Passos

1. Num diretório temporário fora do repo, crie um projeto com `README.md` que diga "app de agendamento para clínicas veterinárias pequenas". Rode `/design` com o plugin do branch.
2. Registre em `docs/reviews/design-pipeline-acceptance.md`, para cada AC listado, o que aconteceu: número de perguntas e se cada uma tinha recomendação; se a pergunta sobre o público foi pulada (AC-002); a resposta "não tenho referências" (AC-004); a matriz de eixos das 3 direções (AC-005); a abertura dos HTML sem rede (AC-006); a parada antes do DESIGN.md (AC-007); o ajuste "densidade 8" só na direção escolhida (AC-008); o pedido "tipografia da A com cores da C" (AC-009); uma página com exceção compacta (AC-013); uma revisão com nota abaixo de 3 (AC-014); uma tela feita pelo `frontend-implementer` (AC-016, AC-020); e um `<h3>` com emoji revisado pelo `design-reviewer` (AC-021).
3. Copie para `agent-system/tests/samples/design-sample/` só `DESIGN.md`, `design/brief.md`, `design/tokens.css`, `design/directions/*.html` e a tela gerada (`src/` ou `index.html`).
4. Acrescente o teste abaixo e rode.

#### Teste (acrescentar)

```python
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
    tokens = dict(TOKEN.findall(read(SAMPLE / "design" / "tokens.css")))
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
```

Nota: `lint_paths` usa `display()` relativo ao `cwd`, então o caminho fica absoluto quando o teste roda da raiz do repo. Isso não afeta a asserção.

### TEST-015: amostra do ensaio cumpre o contrato
- Acceptance: AC-005, AC-006, AC-010, AC-011, AC-016
- Task: TASK-011
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_sample_artifacts"]
- Expected: exit 0; 9 seções; valores do DESIGN.md presentes nos tokens; espaço múltiplo de 4; pares `-ink` com 4.5:1 ou mais; no máximo 3 fontes; 4 HTML sem recurso externo; nenhum P0

### TEST-016: relatório do ensaio de aceitação
- Acceptance: AC-001, AC-002, AC-004, AC-007, AC-008, AC-009, AC-013, AC-014, AC-020, AC-021
- Task: TASK-011
- Command: ["python", "agent-system/scripts/test_system.py", "test_design_acceptance_report_records_each_ac"]
- Required: no
- Expected: exit 0. É informativo: o julgamento de cada AC comportamental está no relatório, não no script.

Teste (acrescentar em `test_design_skills.py` na TASK-011):

```python
ACCEPTANCE_ACS = ("AC-001", "AC-002", "AC-004", "AC-007", "AC-008", "AC-009", "AC-013", "AC-014", "AC-020", "AC-021")


def test_design_acceptance_report_records_each_ac() -> None:
    report = read(PLUGIN / "docs" / "reviews" / "design-pipeline-acceptance.md")
    missing = [item for item in ACCEPTANCE_ACS if item not in report]
    assert not missing, missing
```

## Correções da revisão independente

Revisão: [docs/reviews/design-pipeline.md](../reviews/design-pipeline.md) (FAIL em 2026-11-12). Corrigido depois dela, com teste que falhava antes:

- FIND-001 (blocker): `declared_colors` lê só custom properties dos tokens e a seção `## 2.` do DESIGN.md; a seção 9 não libera mais cores. Teste: `test_design_lint_section_nine_does_not_allowlist_forbidden_colors` (TEST-001).
- FIND-002: `TW_GRADIENT`, `TAG_INNER` e `ICON_ELEMENT` com janelas limitadas; 324 KB de CSS minificado cai de cerca de 31 s para menos de 3 s. Teste: `test_design_lint_is_fast_on_large_minified_files` (TEST-007).
- FIND-004 e FIND-005: gradientes com `rgb()`, `hsl()` e nomes de cor; emoji em elemento filho e em `className={...}`; classes dentro de `cn()`/`clsx`; métricas em português; allowlist também no gradiente do Tailwind; sem P0 para `✓`, `✕`, "Over 3 users", "2x mais barato", `rounded-none` e `acme-challenge`. Testes: `test_design_lint_flags_p0_variants`, `test_design_lint_keeps_legitimate_ui_clean_of_p0`, `test_design_lint_allows_declared_brand_hex_and_gradient`.
- FIND-006: hex só em contexto de cor (não em `href`, `url(#...)` nem prosa); "transition" solto só conta dentro de classe; `transition: "all"` e `outline: "none"` de CSS-in-JS. Teste: `test_design_lint_p1_variants_in_css_in_js_and_prose` (TEST-005).
- FIND-007 e FIND-009: variantes por regra, limites do P2, supressão em `/* */` e `{/* */}`, e na amostra: P1 de cor e fonte em `src/` (AC-016), valores citados no DESIGN.md contra os tokens (AC-011), seção 9 com os P0 (AC-010), eixos das direções par a par (AC-005), licença MIT do ui-ux-pro-max e o eixo "stance".
- FIND-010: o hook só analisa arquivos dentro da raiz do projeto; a CLI avisa no stderr quando pula um arquivo grande e sai com 2 quando um arquivo não pode ser lido. Testes: `test_design_lint_hook_skips_files_outside_the_workspace`, `test_design_lint_reports_skipped_and_unreadable_files`.
- FIND-011: parágrafo do lint movido para depois da lista de comandos nos READMEs; relatório do `design-reviewer` com `fingerprint` e dito como artefato separado do gate; item 27 da checklist virou pergunta de sim ou não.

- FIND-003: o usuário escolheu corrigir o spec. REQ-032 e AC-028 agora dizem o que cada host faz, com o change request registrado em Decisions do spec.
- FIND-008: o usuário escolheu um segundo ensaio com o plugin desta branch carregado. O roteiro está em `docs/reviews/design-pipeline-acceptance.md`, seção "Ensaio 2".
