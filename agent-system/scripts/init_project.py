"""Install the agent system into a project without clobbering existing config."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import MANAGED_MARK, BASE_DIR, read_json, utc_now, write_json  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_EVENTS = [
    "workspaceOpen",
    "sessionStart",
    "sessionEnd",
    "subagentStart",
    "subagentStop",
    "afterFileEdit",
    "postToolUseFailure",
    "afterShellExecution",
    "afterAgentResponse",
    "stop",
]
COPY_SCRIPTS = ["lib.py", "hook.py", "record_event.py", "timeline_view.py", "status_cmd.py"]
RULES = [
    "00-core-engineering.mdc",
    "01-request-classification.mdc",
    "02-spec-driven-development.mdc",
    "03-testing-and-evals.mdc",
    "04-change-management.mdc",
    "05-code-review.mdc",
    "06-checkpoint-and-progress.mdc",
    "07-documentation.mdc",
]
SKILLS = [
    "new-project",
    "feature",
    "feature-development",
    "bug-fix",
    "refactoring",
    "investigation",
    "change-request",
    "implementation",
    "code-review",
    "brainstorm",
    "implementation-plan",
    "tdd",
    "test-hygiene",
    "debug",
    "root-cause",
    "update-docs",
    "commit-push",
    "git-worktree",
    "ui-ux",
    "ui-ux-experiment",
    "init-agent-system",
    "create-agent",
    "agent-status",
    "timeline",
    "help",
    "create-skill",
]


def default_state(root: Path) -> dict:
    return {
        "version": 1,
        "project": str(root),
        "session_id": "",
        "active_task": None,
        "active_agent": "orchestrator",
        "phase": "idle",
        "completed_tasks": [],
        "blocked_tasks": [],
        "pending_tasks": [],
        "open_change_requests": [],
        "review_status": None,
        "last_checkpoint": None,
        "next_step": "Classify the next request before editing code.",
        "installed_at": utc_now(),
    }


def merge_hooks(path: Path, command: str) -> str:
    data = read_json(path, {"version": 1, "hooks": {}})
    if not isinstance(data, dict):
        return "skipped invalid hooks.json"
    data.setdefault("version", 1)
    hooks = data.setdefault("hooks", {})
    added = []
    for event in HOOK_EVENTS:
        entries = hooks.setdefault(event, [])
        if any(command in str(item.get("command", "")) for item in entries if isinstance(item, dict)):
            continue
        item = {"command": command, "timeout": 20}
        if event == "stop":
            item["loop_limit"] = 0
        entries.append(item)
        added.append(event)
    write_json(path, data)
    return "added " + ", ".join(added) if added else "hooks already present"


def copy_scripts(root: Path) -> None:
    dest = root / ".cursor" / "agent-system" / "scripts"
    dest.mkdir(parents=True, exist_ok=True)
    for name in COPY_SCRIPTS:
        target = dest / name
        source = SCRIPT_DIR / name
        header = source.read_text(encoding="utf-8").splitlines()[0] if source.exists() else ""
        if target.exists() and MANAGED_MARK not in target.read_text(encoding="utf-8") and MANAGED_MARK not in header:
            if target.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
                continue
        text = source.read_text(encoding="utf-8")
        if not text.startswith("#"):
            text = f"# {MANAGED_MARK}\n" + text
        elif MANAGED_MARK not in text.splitlines()[0]:
            text = f"# {MANAGED_MARK}\n" + text
        target.write_text(text, encoding="utf-8")


def skill_sources() -> list[Path]:
    found = [BASE_DIR / "skills"] if (BASE_DIR / "skills").is_dir() else []
    agents = Path.home() / ".agents" / "skills"
    if agents.is_dir():
        found.append(agents)
    store = Path.home() / "AppData" / "Local" / "Cursor" / "AgentStores" / "cursor_agent_stores"
    if store.is_dir():
        for child in store.iterdir():
            skills = child / "files" / "skills"
            if skills.is_dir():
                found.append(skills)
    return found


def copy_rules(root: Path) -> tuple[list[str], list[str]]:
    dest = root / ".cursor" / "rules"
    dest.mkdir(parents=True, exist_ok=True)
    created, preserved = [], []
    for name in RULES:
        target = dest / name
        source = BASE_DIR / "rules" / name
        if target.exists():
            preserved.append(name)
            continue
        if not source.exists():
            continue
        shutil.copyfile(source, target)
        created.append(name)
    return created, preserved


def copy_skills(root: Path) -> tuple[list[str], list[str], list[str]]:
    # Skills in a global source are already loaded in every project; a project copy only duplicates prompt tokens.
    dest = root / ".cursor" / "skills"
    created, preserved, global_skills = [], [], []
    sources = skill_sources()
    for name in SKILLS:
        target = dest / name
        if (target / "SKILL.md").exists():
            preserved.append(name)
            continue
        if any((path / name / "SKILL.md").exists() for path in sources):
            global_skills.append(name)
    return created, preserved, global_skills


SKIP_DIRS = {
    ".git",
    ".cursor",
    "node_modules",
    "dist",
    "build",
    "bin",
    "obj",
    "vendor",
    ".venv",
    "venv",
    "__pycache__",
    "coverage",
}
ADR_DIRS = {"adr", "adrs", "decisions", "decision-records"}
PRD_NAMES = {"prd.md", "pdr.md", "product-requirements.md"}
ARCH_NAMES = {"architecture.md", "arch.md"}


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def discover_layout(root: Path) -> dict:
    prd, architecture, specs, adr_dirs, adr_files = [], [], [], [], []
    tasks_dir = changes_dir = progress = None
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".")]
        current = Path(dirpath)
        folder = current.name.lower()
        if folder in ADR_DIRS:
            adr_dirs.append(rel(root, current))
        if folder in {"tasks"} and tasks_dir is None:
            tasks_dir = rel(root, current)
        if folder in {"changes", "change-requests"} and changes_dir is None:
            changes_dir = rel(root, current)
        if folder in {"specs", "spec"}:
            specs.append(rel(root, current))
        for filename in filenames:
            lowered = filename.lower()
            path = current / filename
            if lowered in PRD_NAMES:
                prd.append(rel(root, path))
            elif lowered in ARCH_NAMES:
                architecture.append(rel(root, path))
            elif lowered in {"current.md", "progress.md"} and progress is None:
                progress = rel(root, path)
            elif folder in ADR_DIRS and lowered.endswith(".md"):
                adr_files.append(rel(root, path))
            elif lowered.startswith("adr-") and lowered.endswith(".md"):
                adr_files.append(rel(root, path))
    stack = []
    markers = {
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "pom.xml": "java",
        "composer.json": "php",
    }
    for name, label in markers.items():
        if (root / name).exists() and label not in stack:
            stack.append(label)
    if list(root.glob("*.csproj")) or list(root.glob("*.sln")):
        stack.append("dotnet")
    signals = scan_signals(root)
    return {
        "version": 1,
        "adapted_at": utc_now(),
        "prd": prd[:50],
        "adr_dirs": adr_dirs[:50],
        "adr_files": adr_files[:200],
        "architecture": architecture[:50],
        "specs": specs[:50],
        "tasks_dir": tasks_dir,
        "changes_dir": changes_dir,
        "progress": progress,
        "stack": stack,
        "signals": signals,
    }


TEST_DIRS = {"test", "tests", "__tests__"}
TEST_SUFFIXES = (".test.ts", ".test.tsx", ".test.js", ".spec.ts", ".spec.tsx", "_test.py", "_test.go")
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".go", ".java", ".php", ".rs", ".vue", ".svelte"}


def scan_signals(root: Path) -> dict:
    tests, sources = [], []
    frontend, api, database, devops, auth = [], [], [], [], []
    package_text = ""
    package = root / "package.json"
    if package.exists() and package.stat().st_size < 500_000:
        package_text = package.read_text(encoding="utf-8", errors="ignore").lower()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS and not name.startswith(".")]
        current = Path(dirpath)
        folder = current.name.lower()
        for filename in filenames:
            lowered = filename.lower()
            path = current / filename
            relative = rel(root, path)
            if folder in TEST_DIRS or lowered.startswith("test_") or lowered.endswith(TEST_SUFFIXES):
                tests.append(relative)
            elif path.suffix.lower() in SOURCE_SUFFIXES:
                sources.append(relative)
            if path.suffix.lower() in {".tsx", ".vue", ".svelte"}:
                frontend.append(relative)
            if folder in {"api", "controllers", "routes"} or lowered in {"openapi.yaml", "openapi.yml", "swagger.yaml"}:
                api.append(relative)
            if folder in {"migrations", "prisma"} or lowered.endswith(".sql"):
                database.append(relative)
            if lowered in {"dockerfile", "docker-compose.yml"} or lowered.endswith(".tf") or ".github/workflows" in relative:
                devops.append(relative)
            if any(token in lowered for token in ("auth", "login", "jwt")):
                auth.append(relative)
    if any(token in package_text for token in ('"react"', '"vue"', '"next"', '"@angular/core"', '"svelte"')):
        frontend.append("package.json")
    return {
        "tests": tests[:20],
        "test_count": len(tests),
        "source_count": len(sources),
        "frontend": frontend[:5],
        "api": api[:5],
        "database": database[:5],
        "devops": devops[:5],
        "auth": auth[:5],
    }


def installed_agent_names(root: Path) -> set[str]:
    names = set()
    for folder in (root / ".cursor" / "agents", BASE_DIR / "agents"):
        if folder.is_dir():
            names.update(path.stem for path in folder.glob("*.md"))
    return names


def suggest(root: Path, layout: dict) -> list[dict]:
    signals = layout.get("signals") or {}
    installed = installed_agent_names(root)
    items = []
    if layout["prd"]:
        items.append({"kind": "prd", "status": "present", "evidence": layout["prd"][:3], "suggestion": "PRD ou PDR já existe. Não criar outro."})
    else:
        items.append({"kind": "prd", "status": "missing", "evidence": [], "suggestion": "Não há PRD nem PDR. Antes da próxima feature grande, escreva um PRD curto do produto atual. Não crie agora."})
    if layout["adr_files"] or layout["adr_dirs"]:
        items.append({"kind": "adr", "status": "present", "evidence": (layout["adr_dirs"] or layout["adr_files"])[:3], "suggestion": "ADR já existe. Decisão nova vira ADR novo nesse lugar. Não reescreva os aceitos."})
    else:
        items.append({"kind": "adr", "status": "missing", "evidence": [], "suggestion": "Não há ADR. Na próxima decisão de arquitetura, abra um ADR. Não invente decisões para o que já está em produção."})
    if signals.get("source_count", 0) == 0:
        items.append({"kind": "tests", "status": "not-applicable", "evidence": [], "suggestion": "Ainda não há código de produto. Testes entram com o primeiro comportamento."})
    elif signals.get("test_count", 0) == 0:
        items.append({"kind": "tests", "status": "missing", "evidence": [], "suggestion": "Há código e nenhum teste encontrado. Sugira uma suíte mínima para o comportamento que for mudar, não uma cobertura retroativa de tudo."})
    else:
        items.append({"kind": "tests", "status": "present", "evidence": signals["tests"][:3], "suggestion": "Testes encontrados. Novos comportamentos seguem TDD. Não reescreva a suíte existente."})
    catalog = [
        ("frontend-reviewer", signals.get("frontend"), "Há interface. Um agente de review de frontend ajuda nessa parte."),
        ("api-designer", signals.get("api"), "Há API ou contrato. Um agente de API ajuda em endpoint e contrato."),
        ("database-specialist", signals.get("database"), "Há banco ou migration. Um agente de banco ajuda em schema e consulta."),
        ("devops-engineer", signals.get("devops"), "Há deploy ou container. Um agente de devops ajuda nessa parte."),
        ("security-reviewer", signals.get("auth"), "Há autenticação. Um agente de segurança ajuda a revisar esse fluxo."),
    ]
    for name, evidence, reason in catalog:
        if not evidence or name in installed:
            continue
        items.append({"kind": "agent", "status": "missing", "name": name, "evidence": evidence[:3], "suggestion": f"{reason} Criar só se você pedir: /create-agent {name}."})
    return items


def write_suggestions(root: Path, items: list[dict]) -> None:
    lines = ["# Sugestões de adaptação", "", "O init não criou PRD, ADR, testes nem agentes. Isto é só recomendação.", ""]
    for item in items:
        title = item.get("name") or item["kind"]
        evidence = ", ".join(item.get("evidence") or []) or "nenhuma"
        lines.append(f"## {title}")
        lines.append(f"Estado: {item['status']}")
        lines.append(f"Evidência: {evidence}")
        lines.append(item["suggestion"])
        lines.append("")
    path = root / ".cursor" / "agent-system" / "SUGGESTIONS.md"
    path.write_text("\n".join(lines), encoding="utf-8")


def copy_agents(root: Path) -> list[str]:
    source = BASE_DIR / "agents"
    dest = root / ".cursor" / "agents"
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    if not source.is_dir():
        return copied
    for path in source.glob("*.md"):
        target = dest / path.name
        if target.exists():
            continue
        shutil.copyfile(path, target)
        copied.append(path.name)
    return copied


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--force-home", action="store_true")
    # Locally the plugin already loads rules and agents; project copies would load them twice.
    parser.add_argument("--for-cloud", action="store_true", help="copy rules and agents into the project for Cloud Agents")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root == Path.home().resolve() and not args.force_home:
        print("Refusing to initialize the user home directory. Pass a project root.")
        return 2

    cursor = root / ".cursor"
    cursor.mkdir(parents=True, exist_ok=True)
    system = cursor / "agent-system"
    system.mkdir(parents=True, exist_ok=True)

    report = {"root": str(root), "created": [], "preserved": [], "hooks": ""}
    rules = sorted(path.name for path in (cursor / "rules").glob("*.mdc")) if (cursor / "rules").is_dir() else []
    skills = sorted(path.parent.name for path in (cursor / "skills").glob("*/SKILL.md")) if (cursor / "skills").is_dir() else []
    agents = sorted(path.name for path in (cursor / "agents").glob("*.md")) if (cursor / "agents").is_dir() else []
    report["detected"] = {"rules": rules, "skills": skills, "agents": agents, "hooks": (cursor / "hooks.json").exists()}

    state_file = system / "state.json"
    state_existed = state_file.exists()

    registry_src = BASE_DIR / "agent-system" / "agents.json"
    registry_dest = system / "agents.json"
    if registry_dest.exists():
        report["preserved"].append("agents.json")
    elif registry_src.exists():
        shutil.copyfile(registry_src, registry_dest)
        report["created"].append("agents.json")

    copy_scripts(root)
    report["created"].append("scripts")
    created_rules, preserved_rules = copy_rules(root) if args.for_cloud else ([], [])
    created_skills, preserved_skills, global_skills = copy_skills(root)
    report["global_skills"] = global_skills
    report["created"].extend(created_rules)
    report["created"].extend(created_skills)
    report["preserved"].extend(preserved_rules)
    report["preserved"].extend(preserved_skills)
    copied_agents = copy_agents(root) if args.for_cloud else []
    report["created"].extend(copied_agents)
    if agents:
        report["preserved"].extend(agents)

    hooks_path = cursor / "hooks.json"
    if hooks_path.exists():
        backup = cursor / "hooks.json.bak-agent-system"
        if not backup.exists():
            shutil.copyfile(hooks_path, backup)
            report["preserved"].append("hooks.json.bak-agent-system")
    report["hooks"] = merge_hooks(hooks_path, "python .cursor/agent-system/scripts/hook.py")

    layout = discover_layout(root)
    write_json(system / "layout.json", layout)
    suggestions = suggest(root, layout)
    write_suggestions(root, suggestions)
    report["layout"] = {
        "prd": layout["prd"],
        "adr_dirs": layout["adr_dirs"],
        "adr_files": len(layout["adr_files"]),
        "architecture": layout["architecture"],
        "specs": layout["specs"],
        "stack": layout["stack"],
    }
    report["suggestions"] = suggestions
    if state_existed:
        report["preserved"].append("state.json")
    else:
        state = default_state(root)
        if layout["prd"] or layout["adr_files"] or layout["architecture"]:
            state["next_step"] = "Use the documents recorded in .cursor/agent-system/layout.json. Do not move them."
        write_json(state_file, state)
        report["created"].append("state.json")

    note = system / "INSTALLED.txt"
    if not note.exists():
        note.write_text(
            "Spec-driven agent system installed.\n"
            "Docs live in the agent-workbench plugin: agent-system/README.md\n"
            "Empty product docs were not created.\n",
            encoding="utf-8",
        )
        report["created"].append("INSTALLED.txt")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
