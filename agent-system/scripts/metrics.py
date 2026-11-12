"""Per-node metrics from the timeline: runs, durations, response size, and tokens per agent; gates and revisions per feature.

Read only: it never writes state.json, the timeline, or any artifact. Malformed lines are skipped and counted.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import redact  # noqa: E402

PLUGIN_PREFIX = "agent-workbench:"
RESPONSE_CHARS = re.compile(r"\((\d+) chars\)")
TOKEN_FIELDS = ("input", "output", "cache_read", "cache_creation")


def parse_time(value) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def agent_of(event: dict) -> str:
    name = str(event.get("agent") or "unknown")
    return name[len(PLUGIN_PREFIX):] if name.startswith(PLUGIN_PREFIX) else name


def read_events(path: Path) -> tuple[list[dict], int]:
    events, skipped = [], 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if not isinstance(event, dict) or not event.get("event") or parse_time(event.get("timestamp")) is None:
            skipped += 1
            continue
        events.append(event)
    return events, skipped


def compute(events: list[dict], feature: str | None = None, since: datetime | None = None) -> dict:
    if since:
        events = [event for event in events if parse_time(event["timestamp"]) >= since]
    if feature:
        mine = [parse_time(event["timestamp"]) for event in events if event.get("feature") == feature]
        start, end = (min(mine), max(mine)) if mine else (None, None)
        events = [event for event in events if start and start <= parse_time(event["timestamp"]) <= end]

    agents: dict[str, dict] = {}
    open_runs: dict[tuple[str, str], list[datetime]] = {}

    def entry(name: str) -> dict:
        return agents.setdefault(name, {"runs": 0, "durations": [], "response_chars": 0, "tokens": dict.fromkeys(TOKEN_FIELDS, 0), "token_events": 0})

    any_tokens = False
    for event in events:
        kind = event["event"]
        name = agent_of(event)
        key = (str(event.get("session") or ""), name)
        when = parse_time(event["timestamp"])
        if kind == "SUBAGENT_STARTED":
            open_runs.setdefault(key, []).append(when)
        elif kind == "SUBAGENT_STOPPED":
            item = entry(name)
            item["runs"] += 1
            started = open_runs.get(key)
            if started:
                item["durations"].append(max(0.0, (when - started.pop(0)).total_seconds()))
        elif kind == "AGENT_RESPONSE":
            found = RESPONSE_CHARS.search(str(event.get("summary") or ""))
            if found:
                entry(name)["response_chars"] += int(found.group(1))
        tokens = event.get("tokens")
        if kind in {"SUBAGENT_STOPPED", "AGENT_RESPONSE"} and isinstance(tokens, dict):
            item = entry(name)
            counted = False
            for field in TOKEN_FIELDS:
                value = tokens.get(field)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    item["tokens"][field] += value
                    counted = True
            if counted:
                item["token_events"] += 1
                any_tokens = True

    report_agents = {}
    for name, item in sorted(agents.items()):
        durations = item["durations"]
        report_agents[name] = {
            "runs": item["runs"],
            "duration_s_total": round(sum(durations), 3),
            "duration_s_median": round(statistics.median(durations), 3) if durations else None,
            "response_chars": item["response_chars"],
            "tokens": {**item["tokens"], "total": sum(item["tokens"].values())} if item["token_events"] else "unavailable",
        }

    features: dict[str, dict] = {}
    for event in events:
        if event["event"] != "VERIFICATION_COMPLETED" or not event.get("feature"):
            continue
        slug = str(event["feature"])
        if feature and slug != feature:
            continue
        item = features.setdefault(slug, {"gates": 0, "gates_failed": 0, "revisions_to_pass": 0, "passed": False})
        item["gates"] += 1
        if str(event.get("result") or "").startswith("passed"):
            item["passed"] = True
        else:
            item["gates_failed"] += 1
            if not item["passed"]:
                item["revisions_to_pass"] += 1
    return {"agents": report_agents, "features": dict(sorted(features.items())), "tokens": "available" if any_tokens else "unavailable"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Per-agent and per-feature metrics from the timeline (read only).")
    parser.add_argument("--root", default=".")
    parser.add_argument("--feature", help="only this feature; agents are limited to the time span of its events")
    parser.add_argument("--since", help="ISO date or time; ignore older events")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    since = None
    if args.since:
        since = parse_time(args.since)
        if since is None:
            print(f"[ERROR] --since must be an ISO date or time, got {args.since!r}", file=sys.stderr)
            return 2
    path = Path(args.root).resolve() / ".cursor" / "timeline" / "events.jsonl"
    if not path.is_file():
        print(json.dumps({"agents": {}, "features": {}, "tokens": "unavailable", "skipped": 0}) if args.json else "No timeline yet.")
        return 0
    events, skipped = read_events(path)
    report = compute(events, args.feature, since)
    report["skipped"] = skipped
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print("Agents:")
    for name, item in report["agents"].items():
        tokens = item["tokens"]
        token_text = "unavailable" if tokens == "unavailable" else f"{tokens['total']} (in {tokens['input']}, out {tokens['output']}, cache read {tokens['cache_read']}, cache write {tokens['cache_creation']})"
        median = "-" if item["duration_s_median"] is None else f"{item['duration_s_median']}s"
        print(f"- {redact(name, 60)}: runs {item['runs']}, time {item['duration_s_total']}s (median {median}), response chars {item['response_chars']}, tokens: {token_text}")
    if not report["agents"]:
        print("- none")
    print("Features:")
    for slug, item in report["features"].items():
        state = "passed" if item["passed"] else "not passed yet"
        print(f"- {redact(slug, 80)}: gates {item['gates']}, failed {item['gates_failed']}, revisions to pass {item['revisions_to_pass']} ({state})")
    if not report["features"]:
        print("- none")
    if report["tokens"] == "unavailable":
        print("tokens: unavailable (the host sent no usage numbers; Cursor never does, Claude Code does for subagents)")
    if skipped:
        print(f"skipped: {skipped} malformed line(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
