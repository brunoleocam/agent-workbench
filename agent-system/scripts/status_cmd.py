"""Show installed agents, workflow state, and nearby system files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import BASE_DIR, roadmap_summary  # noqa: E402


def list_md(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(path.stem for path in folder.glob("*.md"))


def list_skills(folder: Path) -> list[str]:
    if not folder.is_dir():
        return []
    return sorted(path.parent.name for path in folder.glob("*/SKILL.md"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    state_file = root / ".cursor" / "agent-system" / "state.json"
    registry_file = root / ".cursor" / "agent-system" / "agents.json"
    user_registry = BASE_DIR / "agent-system" / "agents.json"
    registry = {}
    if registry_file.exists():
        registry = json.loads(registry_file.read_text(encoding="utf-8"))
    elif user_registry.exists():
        registry = json.loads(user_registry.read_text(encoding="utf-8"))
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else None
    hooks = root / ".cursor" / "hooks.json"
    plugin_hooks = BASE_DIR / "hooks" / "hooks.json"
    print(f"Project: {root}")
    print(f"Initialized: {state_file.exists()}")
    print("Agents:")
    for agent in registry.get("agents", []):
        print(f"- {agent.get('name')}: {agent.get('purpose')}")
    print("Project agent files:", ", ".join(list_md(root / ".cursor" / "agents")) or "-")
    print("Plugin agent files:", ", ".join(list_md(BASE_DIR / "agents")) or "-")
    print("Project skills:", ", ".join(list_skills(root / ".cursor" / "skills")) or "-")
    print("Project rules:", ", ".join(sorted(path.name for path in (root / ".cursor" / "rules").glob("*.mdc"))) or "-")
    print(f"Project hooks: {hooks.exists()}")
    print(f"Plugin hooks: {plugin_hooks.exists()}")
    if state:
        print(f"Phase: {state.get('phase')}")
        print(f"Active task: {state.get('active_task')}")
        print(f"Active agent: {state.get('active_agent')}")
        print(f"Blocked: {', '.join(state.get('blocked_tasks') or []) or '-'}")
        print(f"Open CRs: {', '.join(state.get('open_change_requests') or []) or '-'}")
        print(f"Review: {state.get('review_status')}")
        print(f"Next: {state.get('next_step')}")
        print(f"Roadmap: {roadmap_summary(root) or '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
