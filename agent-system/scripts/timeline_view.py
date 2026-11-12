"""Print the timeline and optionally write a markdown view from JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lib import redact, safe_files


def feature_trace(lines: list[str], feature: str, as_json: bool) -> int:
    """Every event of one feature in order; a verdict whose fingerprint differs from the previous verdict is marked."""
    items = []
    last_fingerprint = None
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("feature") != feature:
            continue
        fingerprint = event.get("fingerprint") if isinstance(event.get("fingerprint"), str) else None
        changed = bool(fingerprint and last_fingerprint and fingerprint != last_fingerprint)
        if fingerprint:
            last_fingerprint = fingerprint
        inputs = event.get("inputs") if isinstance(event.get("inputs"), list) else []
        items.append({
            "time": str(event.get("local_time") or event.get("timestamp") or ""),
            "event": str(event.get("event") or ""),
            "node": event.get("node"),
            "agent": event.get("agent"),
            "result": redact(str(event.get("result") or ""), 160),
            "inputs": safe_files([str(item) for item in inputs]),
            "fingerprint": fingerprint[:12] if fingerprint else None,
            "code_changed": changed,
        })
    if as_json:
        print(json.dumps({"feature": feature, "events": items}, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print(f"No events for feature {feature}.")
        return 0
    for item in items:
        mark = "  [code changed since the previous verdict]" if item["code_changed"] else ""
        print(f"{item['time']}  {item['event']}  node={item['node'] or '-'}  agent={item['agent']}  result={item['result'] or '-'}  fp={item['fingerprint'] or '-'}{mark}")
        if item["inputs"]:
            print(f"    inputs: {', '.join(item['inputs'])}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--write-md", action="store_true")
    parser.add_argument("--feature", help="decision trace of one feature: every event of that slug, oldest first")
    parser.add_argument("--json", action="store_true", help="with --feature, structured output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    path = root / ".cursor" / "timeline" / "events.jsonl"
    if not path.exists():
        print("No timeline yet.")
        return 0
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.feature:
        return feature_trace(lines, args.feature, args.json)
    selected = lines[-args.limit :]
    blocks = []
    for line in selected:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        files = event.get("files") if isinstance(event.get("files"), list) else []
        file_text = "\n".join(f"- {item}" for item in safe_files([str(item) for item in files]))
        block = "\n".join(
            [
                str(event.get("local_time") or event.get("timestamp")),
                f"Agent: {event.get('agent')}",
                f"Task: {event.get('task') or '-'}",
                f"Event: {event.get('event')}",
                f"Summary: {redact(str(event.get('summary') or ''), 240)}",
                f"Files:\n{file_text}" if file_text else "Files: -",
                f"Result: {redact(str(event.get('result') or ''), 160)}",
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
