"""Register a custom subagent without overwriting an existing definition."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import BUILTIN_AGENTS, BASE_DIR, read_json, utc_now, write_json  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def registry_path() -> Path:
    return BASE_DIR / "agent-system" / "agents.json"


def load_registry() -> dict:
    data = read_json(registry_path(), {"version": 1, "agents": []})
    data.setdefault("agents", [])
    return data


def existing_names() -> set[str]:
    names = set(BUILTIN_AGENTS)
    agents_dir = BASE_DIR / "agents"
    if agents_dir.is_dir():
        names.update(path.stem for path in agents_dir.glob("*.md"))
    for agent in load_registry().get("agents", []):
        if agent.get("name"):
            names.add(agent["name"])
    return names


def frontmatter_name(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    for line in text[3:end].splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "register"])
    parser.add_argument("--name", required=True)
    parser.add_argument("--purpose", default="")
    parser.add_argument("--recommended-for", default="")
    parser.add_argument("--root", default="")
    args = parser.parse_args()

    name = args.name.strip()
    if not NAME_RE.match(name):
        print("Name must be lowercase letters, numbers, and hyphens.")
        return 2
    if name in BUILTIN_AGENTS:
        print(f"{name} conflicts with a built-in Cursor agent.")
        return 2

    agent_file = BASE_DIR / "agents" / f"{name}.md"
    if args.action == "check":
        if name in existing_names() or agent_file.exists():
            print(f"Conflict: {name} already exists.")
            return 2
        print("ok")
        return 0

    if not agent_file.exists():
        print(f"Missing {agent_file}. Write the agent file before register.")
        return 2
    declared = frontmatter_name(agent_file)
    if declared != name:
        print(f"Frontmatter name is {declared!r}, expected {name!r}.")
        return 2

    registry = load_registry()
    if any(item.get("name") == name for item in registry["agents"]):
        print("Already registered. Agent file left unchanged.")
        return 0

    registry["agents"].append(
        {
            "name": name,
            "type": "custom",
            "purpose": args.purpose or name,
            "status": "active",
            "created_at": utc_now(),
            "scope": "user",
            "recommended_for": args.recommended_for or args.purpose or name,
            "dependencies": ["orchestrator"],
        }
    )
    write_json(registry_path(), registry)

    orchestrator = BASE_DIR / "agents" / "orchestrator.md"
    bullet = f"- `{name}`: {args.recommended_for or args.purpose or name}."
    if orchestrator.exists():
        text = orchestrator.read_text(encoding="utf-8")
        if bullet not in text:
            if "## Specialists" not in text:
                text += "\n## Specialists\n"
            text = text.rstrip() + "\n" + bullet + "\n"
            orchestrator.write_text(text, encoding="utf-8")

    if args.root:
        root = Path(args.root).resolve()
        project_registry = root / ".cursor" / "agent-system" / "agents.json"
        if project_registry.exists():
            local = read_json(project_registry, {"version": 1, "agents": []})
            if not any(item.get("name") == name for item in local.get("agents", [])):
                local.setdefault("agents", []).append(registry["agents"][-1])
                write_json(project_registry, local)
        project_agent = root / ".cursor" / "agents" / f"{name}.md"
        if (root / ".cursor" / "agent-system" / "state.json").exists() and not project_agent.exists():
            project_agent.parent.mkdir(parents=True, exist_ok=True)
            project_agent.write_text(agent_file.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Registered {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
