"""Print the timeline and optionally write a markdown view from JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--write-md", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    path = root / ".cursor" / "timeline" / "events.jsonl"
    if not path.exists():
        print("No timeline yet.")
        return 0
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = lines[-args.limit :]
    blocks = []
    for line in selected:
        event = json.loads(line)
        files = event.get("files") or []
        file_text = "\n".join(f"- {item}" for item in files)
        block = "\n".join(
            [
                str(event.get("local_time") or event.get("timestamp")),
                f"Agent: {event.get('agent')}",
                f"Task: {event.get('task') or '-'}",
                f"Event: {event.get('event')}",
                f"Summary: {event.get('summary')}",
                f"Files:\n{file_text}" if file_text else "Files: -",
                f"Result: {event.get('result')}",
            ]
        )
        blocks.append(block)
        print(block)
        print()
    if args.write_md:
        view = root / ".cursor" / "timeline" / "TIMELINE.md"
        view.parent.mkdir(parents=True, exist_ok=True)
        view.write_text("# Timeline\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
        print(f"Wrote {view}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
