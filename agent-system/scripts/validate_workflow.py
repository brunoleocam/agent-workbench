"""Validate the declared execution graph (workflow.json) and print it as Mermaid.

Exit codes: 0 valid, 1 structural error, 2 missing or invalid file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow  # noqa: E402


def state_keys() -> set[str] | None:
    """default_state() keys from init_project.py, which only exists in the plugin, not in a project copy."""
    if not (workflow.SCRIPTS_DIR / "init_project.py").is_file():
        return None
    import init_project  # noqa: PLC0415

    return set(init_project.default_state(Path(".")).keys())


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate workflow.json and optionally print it as a Mermaid flowchart.")
    parser.add_argument("--workflow", help="graph file (default: workflow.json next to scripts/)")
    parser.add_argument("--agents", help="agents registry (default: agents.json next to scripts/)")
    parser.add_argument("--json", action="store_true", help="structured output")
    parser.add_argument("--mermaid", action="store_true", help="print the graph as a Mermaid flowchart when it is valid")
    args = parser.parse_args()

    path = Path(args.workflow) if args.workflow else workflow.default_path()
    agents_path = Path(args.agents) if args.agents else workflow.SYSTEM_DIR / "agents.json"
    try:
        graph = workflow.load(path)
        registry = workflow.load(agents_path) if agents_path.is_file() else None
    except workflow.WorkflowError as exc:
        if args.json:
            print(json.dumps({"ok": False, "config_error": str(exc)}))
        else:
            print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    errors = workflow.validate(graph, registry, workflow.SCRIPTS_DIR, state_keys())
    if args.mermaid and not errors:
        print(workflow.mermaid(graph), end="")
        return 0
    if args.json:
        print(json.dumps({"ok": not errors, "nodes": len(graph.get("nodes") or []), "edges": len(graph.get("edges") or []), "errors": errors}, indent=2))
    else:
        for item in errors:
            print(f"[FAIL] {item['code']}: {item['message']}")
        if registry is None:
            print("[INFO] agents.json not found; agent coverage was not checked.")
        if errors:
            print(f"Workflow validation failed ({len(errors)} error(s)).")
        else:
            print(f"[PASS] {len(graph['nodes'])} nodes and {len(graph['edges'])} edges, every node reachable from '{graph['start']}'.")
            print("Workflow validation passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
