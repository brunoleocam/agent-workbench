"""Append one semantic timeline event and update workflow state."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

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
    args = parser.parse_args()

    if args.event not in SEMANTIC_EVENTS:
        print(f"Unknown event {args.event}", file=sys.stderr)
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
    append_event(root, event)
    save_state(root, apply_semantic_state(state, event))
    print(event["timestamp"], event["event"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
