"""Deterministic router: the next node(s) of workflow.json from a node, the request context, and a result.

It only recommends; the orchestrator runs the node. A human node returns status needs_decision with its question.
Exit codes: 0 next node or terminal node, 1 no edge holds, 2 bad argument or graph.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow  # noqa: E402
from lib import read_json  # noqa: E402


def revision_count(root: Path, feature: str) -> int:
    try:
        state = read_json(root / ".cursor" / "agent-system" / "state.json", {})
    except (OSError, json.JSONDecodeError):
        return 0
    revisions = state.get("revisions") if isinstance(state, dict) else None
    value = revisions.get(feature) if isinstance(revisions, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def fail(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"status": "error", "error": message}))
    else:
        print(f"[ERROR] {message}", file=sys.stderr)
    return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Next node of the execution graph (workflow.json).")
    parser.add_argument("--root", default=".", help="project root, for state.json revisions (default: current directory)")
    parser.add_argument("--workflow", help="graph file (default: workflow.json next to scripts/)")
    parser.add_argument("--from", dest="source", required=True, help="current node id")
    parser.add_argument("--result", default="pass", help="result of the current node: pass, fail, or escalate (default: pass)")
    parser.add_argument("--class", dest="klass", choices=workflow.CLASSES)
    parser.add_argument("--complexity", choices=workflow.COMPLEXITY)
    parser.add_argument("--security", choices=workflow.SECURITY)
    parser.add_argument("--interface", choices=workflow.INTERFACES, help="new, existing, or none; required where an edge depends on it")
    parser.add_argument("--design-approved", action="store_true", help="an approved DESIGN.md exists")
    parser.add_argument("--feature", help="feature slug; required after a failed gate to read its revision count")
    parser.add_argument("--text", action="store_true", help="one-line text output instead of JSON")
    args = parser.parse_args()

    as_json = not args.text
    try:
        graph = workflow.load(Path(args.workflow) if args.workflow else workflow.default_path())
    except workflow.WorkflowError as exc:
        return fail(str(exc), as_json)
    ctx = {
        "class": args.klass,
        "complexity": args.complexity,
        "security": args.security,
        "interface": args.interface,
        "design_approved": args.design_approved,
    }
    revisions = revision_count(Path(args.root).resolve(), args.feature) if args.feature else None
    try:
        answer = workflow.route(graph, args.source, ctx, args.result, revisions)
    except workflow.ArgumentError as exc:
        return fail(str(exc), as_json)
    if args.feature:
        answer["feature"] = args.feature
        answer["revisions"] = revisions
    if as_json:
        print(json.dumps(answer, indent=2, ensure_ascii=False))
    else:
        target = ", ".join(answer["next"]) or "-"
        mode = " (parallel, join " + str(answer["join"]) + ")" if answer["parallel"] else ""
        print(f"{answer['status']}: {args.source} -> {target}{mode}")
        if answer.get("question"):
            print(f"Ask the user: {answer['question']}")
        for reason in answer["reason"]:
            print(f"  {reason}")
    return 1 if answer["status"] == "no_match" else 0


if __name__ == "__main__":
    raise SystemExit(main())
