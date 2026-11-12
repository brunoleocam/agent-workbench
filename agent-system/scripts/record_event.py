"""Append one semantic timeline event and update workflow state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import workflow  # noqa: E402
from artifacts import workspace_fingerprint  # noqa: E402
from lib import SEMANTIC_EVENTS, append_event, apply_semantic_state, load_state, local_stamp, opted_in, redact, safe_files, save_state, utc_now  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--event", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--agent", default="orchestrator")
    parser.add_argument("--task", default="")
    parser.add_argument("--files", default="")
    parser.add_argument("--result", default="completed")
    parser.add_argument("--session", default="")
    parser.add_argument("--feature", default="", help="feature slug, for validation and security events")
    parser.add_argument("--node", default="", help="workflow.json node id; makes the event a decision trace")
    parser.add_argument("--inputs", default="", help="comma-separated artifact paths the decision read (paths only)")
    args = parser.parse_args()

    if args.event not in SEMANTIC_EVENTS:
        print(f"Unknown event {args.event}", file=sys.stderr)
        return 2

    if args.inputs and not args.node:
        print("--inputs needs --node (the workflow node that made the decision)", file=sys.stderr)
        return 2
    if args.node:
        try:
            known = workflow.nodes_by_id(workflow.load(workflow.default_path()))
        except workflow.WorkflowError as exc:
            print(f"Cannot check --node: {exc}", file=sys.stderr)
            return 2
        if args.node not in known:
            print(f"Unknown workflow node {args.node!r}. Known: {', '.join(sorted(known))}", file=sys.stderr)
            return 2
        if known[args.node].get("kind") == "script":
            print(f"Node {args.node!r} is a script node; only {known[args.node].get('script')} records it.", file=sys.stderr)
            return 2

    root = Path(args.root).resolve()
    if not opted_in(root):
        print("Project is not initialized. Run /init-agent-system.", file=sys.stderr)
        return 2

    state = load_state(root)
    files = safe_files([part.strip() for part in args.files.split(",") if part.strip()])
    event = {
        "timestamp": utc_now(),
        "local_time": local_stamp(),
        "session": args.session or state.get("session_id") or "",
        "agent": args.agent,
        "event": args.event,
        "task": args.task or state.get("active_task"),
        "files": files,
        "summary": redact(args.summary, 240),
        "result": redact(args.result, 160),
    }
    if args.feature:
        event["feature"] = redact(args.feature, 80)
    if args.node:
        event["node"] = args.node
        event["inputs"] = safe_files(sorted({part.strip().replace("\\", "/") for part in args.inputs.split(",") if part.strip()}))
        try:
            event["fingerprint"] = workspace_fingerprint(root)["digest"]
        except (OSError, ValueError):
            event["fingerprint"] = None
    append_event(root, event)
    save_state(root, apply_semantic_state(state, event))
    print(event["timestamp"], event["event"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
