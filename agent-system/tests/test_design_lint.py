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



def test_design_lint_counts_fonts_per_direction() -> None:
    """Each preview in design/directions/ is an alternative, not part of one product."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        pairs = {"a": ("Baloo 2", "Nunito Sans"), "b": ("Fraunces", "Source Sans 3"), "c": ("Barlow Condensed", "Barlow")}
        for name, (display, body) in pairs.items():
            write(root, f"design/directions/{name}.html", f"<style>:root {{ --font-display: '{display}', serif; --font-body: '{body}', sans-serif; }}</style>\n")
        code, report, _ = lint(root, "design/directions")
        assert "P1-FONT-COUNT" not in rules(report) and code == 0, report
        # One direction with four families is still flagged.
        write(root, "design/directions/d.html", "<style>:root { --font-a: 'A1', serif; --font-b: 'B1', serif; --font-c: 'C1', serif; --font-d: 'D1', serif; }</style>\n")
        code, report, _ = lint(root, "design/directions")
        assert {item["file"] for item in report["findings"] if item["rule"] == "P1-FONT-COUNT"} == {"design/directions/d.html"}, report


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


# --- Review findings (docs/reviews/design-pipeline.md) ---------------------------------------

sys.path.insert(0, str(SCRIPTS))
import lint_design  # noqa: E402

P0_VARIANTS = [
    ("P0-INDIGO", "src/a.css", ".a { color: #4f46e5; }\n"),
    ("P0-INDIGO", "src/A.tsx", 'export const A = () => <p className="text-indigo-500">Oi</p>;\n'),
    ("P0-INDIGO", "src/B.tsx", 'const s = { color: "#a855f7" };\n'),
    ("P0-GRADIENT", "src/C.tsx", 'export const C = () => <div className="bg-gradient-to-r from-violet-600 to-blue-500">Oi</div>;\n'),
    ("P0-GRADIENT", "src/d.css", "h1 { background-clip: text; }\n"),
    ("P0-GRADIENT", "src/e.css", ".e { background: linear-gradient(135deg, rgb(139, 92, 246), rgb(59, 130, 246)); }\n"),
    ("P0-GRADIENT", "src/f.css", ".f { background: linear-gradient(to right, purple, blue); }\n"),
    ("P0-GRADIENT", "src/g.css", ".g { background: linear-gradient(90deg, hsl(260 80% 60%), hsl(200 80% 55%)); }\n"),
    ("P0-EMOJI-ICON", "src/H.tsx", "export const H = () => <button><span>\U0001F680</span> Enviar</button>;\n"),
    ("P0-EMOJI-ICON", "src/I.tsx", "export const I = () => <h2>Título <em>novo</em> \U0001F389</h2>;\n"),
    ("P0-EMOJI-ICON", "src/J.tsx", "export const J = () => <span className={styles.icon}>⚡</span>;\n"),
    ("P0-EMOJI-ICON", "index.html", "<ul><li>✅ Pronto</li></ul>\n"),
    ("P0-SIDE-STRIPE", "src/K.tsx", 'export const K = () => <div className="border-l-4 border-teal-600 rounded-lg">Oi</div>;\n'),
    ("P0-SIDE-STRIPE", "src/L.tsx", 'export const L = () => <div className={cn("border-l-4 border-teal-600", "rounded-lg")}>Oi</div>;\n'),
    ("P0-SIDE-STRIPE", "src/M.tsx", 'const s = { borderLeft: "4px solid teal", borderRadius: 8 };\n'),
    ("P0-METRIC", "index.html", "<p>99,9% de disponibilidade garantida</p>\n"),
    ("P0-METRIC", "index.html", "<p>Usado por mais de 10 mil empresas</p>\n"),
    ("P0-METRIC", "index.html", "<p>100% uptime</p>\n"),
    ("P0-METRIC", "index.html", "<p>Join 10,000+ developers</p>\n"),
    ("P0-METRIC", "index.html", "<p>Ship 3x faster</p>\n"),
] + [("P0-PLACEHOLDER-CDN", "index.html", f'<img src="https://{host}/x" alt="">\n') for host in ("images.unsplash.com", "placehold.co", "placekitten.com", "picsum.photos", "via.placeholder.com")]

CLEAN_VARIANTS = [
    ("src/Close.tsx", 'export const C = () => <button aria-label="Fechar">✕</button>;\n'),
    ("index.html", "<ul><li>✓ Sem cartão</li></ul>\n"),
    ("index.html", "<p>Over 3 users can edit this document.</p>\n"),
    ("index.html", "<p>Plano 2x mais barato que o anual.</p>\n"),
    ("src/N.tsx", 'export const N = () => <div className="border-l-4 rounded-none">Oi</div>;\n'),
    ("index.html", '<a href="/.well-known/acme-challenge/x">Validar domínio</a>\n'),
]


def test_design_lint_flags_p0_variants() -> None:
    for rule, relative, text in P0_VARIANTS:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            code, report, done = lint(root, relative)
            assert rule in rules(report) and code == 1, (rule, text, report, done.stderr)


def test_design_lint_keeps_legitimate_ui_clean_of_p0() -> None:
    for relative, text in CLEAN_VARIANTS:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            code, report, _ = lint(root, relative)
            assert not [item for item in report["findings"] if item["severity"] == "P0"] and code == 0, (text, report)


def test_design_lint_section_nine_does_not_allowlist_forbidden_colors() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "DESIGN.md", "---\nstatus: approved\n---\n## 2. Cor\n| `--color-accent` | `#0f766e` |\n## 9. Anti-padrões\n- Nunca use #6366f1 nem #7c3aed.\n")
        write(root, "src/B.tsx", 'export const B = () => <p style={{ color: "#6366f1" }} className="bg-indigo-500">Oi</p>;\n')
        code, report, _ = lint(root, "src")
        assert [item["rule"] for item in report["findings"] if item["severity"] == "P0"].count("P0-INDIGO") == 2 and code == 1, report


def test_design_lint_allows_declared_brand_hex_and_gradient() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "design/tokens.css", ":root {\n  --color-accent: #7c3aed;\n  --color-accent-2: #ec4899;\n}\n")
        write(root, "src/Badge.tsx", 'const s = { color: "#7c3aed" };\nexport const B = () => <div className="bg-gradient-to-r from-violet-600 to-pink-500">Novo</div>;\n')
        write(root, "src/hero.css", ".h { background: linear-gradient(90deg, #7c3aed, #ec4899); }\n")
        code, report, _ = lint(root, "src", "--tokens", "design/tokens.css")
        assert not {"P0-INDIGO", "P0-GRADIENT"} & rules(report) and code == 0, report


def test_design_lint_p1_variants_in_css_in_js_and_prose() -> None:
    flagged = [
        ("P1-TRANSITION-ALL", "src/A.tsx", 'const s = { transition: "all 0.2s" };\n@media (prefers-reduced-motion: reduce) {}\n'),
        ("P1-OUTLINE-NONE", "src/B.tsx", 'const s = { outline: "none" };\n'),
    ]
    for rule, relative, text in flagged:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            _, report, _ = lint(root, relative)
            assert rule in rules(report), (rule, report)
    clean = [
        ("index.html", "<p>A smooth transition between your old tool and ours.</p>\n"),
        ("src/C.tsx", 'export const C = () => <a href={"#add"}>Adicionar</a>;\n'),
        ("index.html", '<svg><path fill="url(#bad)"/></svg>\n'),
        ("index.html", "<p>Veja a issue #123 no repositório.</p>\n"),
    ]
    for relative, text in clean:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            _, report, _ = lint(root, relative)
            assert not {"P1-NO-REDUCED-MOTION", "P1-RAW-COLOR"} & rules(report), (text, report)


def test_design_lint_p2_thresholds_at_the_boundary() -> None:
    for count, expected in ((6, False), (7, True)):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, "a.css", "".join(f".a{n} {{ color: var(--color-accent); }}\n" for n in range(count)))
            _, report, _ = lint(root, "a.css")
            assert ("P2-ACCENT-OVERUSE" in rules(report)) is expected, (count, report)
    for count, expected in ((3, False), (4, True)):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, "G.tsx", "".join(f'<div className="hover:scale-105">{n}</div>\n' for n in range(count)))
            _, report, _ = lint(root, "G.tsx")
            assert ("P2-UNIFORM-HOVER-SCALE" in rules(report)) is expected, (count, report)


def test_design_lint_suppression_in_block_and_jsx_comments() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "a.css", "/* design-lint-disable P0-INDIGO -- logo do parceiro */\n.logo { color: #6366f1; }\n")
        write(root, "B.tsx", "{/* design-lint-disable P0-METRIC -- SLA do contrato */}\n<p>99.9% uptime</p>\n")
        code, report, _ = lint(root, ".")
        assert report["findings"] == [] and code == 0, report


def test_design_lint_is_fast_on_large_minified_files() -> None:
    import time

    samples = {
        "min.css": "".join(f".from-blue-{n % 9 + 1}00{{--tw-gradient-from:#3b82f6;--tw-gradient-stops:var(--tw-gradient-from)}}" for n in range(3000)),
        "classes.html": "from-blue-500 " * 8000,
        "tags.html": "<h1 " * 8000,
    }
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        for name, text in samples.items():
            path = write(root, name, text)
            start = time.perf_counter()
            lint_design.lint_paths([path])
            elapsed = time.perf_counter() - start
            assert elapsed < 3, (name, len(text), round(elapsed, 2))


def test_design_lint_reports_skipped_and_unreadable_files() -> None:
    from unittest import mock

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "big.css", "a { color: var(--c); }\n" * 30000)
        done = run("lint_design.py", ["big.css"], cwd=root)
        assert done.returncode == 0 and "skipped" in done.stderr and "big.css" in done.stderr, (done.stdout, done.stderr)
        target = write(root, "x.css", "a { color: var(--c); }\n")
        real = lint_design.read_source

        def broken(path: Path) -> str:
            if path.name == "x.css":
                raise PermissionError("denied")
            return real(path)

        with mock.patch.object(lint_design, "read_source", broken):
            notes: list[str] = []
            lint_design.lint_paths([target], notes=notes)
        assert notes and "x.css" in notes[0] and "unreadable" in notes[0], notes


def test_design_lint_hook_skips_files_outside_the_workspace() -> None:
    with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as other:
        root = Path(raw)
        outside = write(Path(other), "Hero.tsx", "export const Hero = () => <h1>\U0001F680 Agenda</h1>;\n")
        script = write(root, "tool.py", "print('\U0001F680')\n")
        common = {"session_id": "s", "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_response": {"success": True}}
        assert hook({**common, "tool_input": {"file_path": str(outside)}}, root) == {}
        assert hook({**common, "tool_input": {"file_path": str(script)}}, root) == {}
