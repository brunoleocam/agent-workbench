"""Detect plan drift: files a pending task will touch that changed after the plan was written.

`--stamp` records a `- Baseline:` line (short content digests of the task's `Files:`) on tasks that are still
todo or blocked. The default run compares those digests with the working tree before an implementer starts.

A change is *expected* when another task of the same plan that is done or in progress lists the same file.
Any other change is unaccounted drift: the plan was written against different code. The implementer stops and
reports it instead of improvising. Digests ignore line-ending differences. Idea adapted from shadcn/improve
(MIT), which stamps a git commit into each plan; here the stamp is per file and survives a rebase or a squash.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import (  # noqa: E402
    Block,
    Bundle,
    ConfigError,
    Report,
    add_common_args,
    config_error,
    inside,
    load_bundle,
    task_status,
)

DIGEST_LEN = 10
PENDING = {"todo", "blocked"}
ACTIVE = {"done", "in_progress"}
BASELINE_LINE = re.compile(r"^(\s*[-*]\s+(?:\*\*)?)baseline(?:\*\*)?\s*:", re.IGNORECASE)
FILES_LINE = re.compile(r"^\s*[-*]\s+(?:\*\*)?(?:files|arquivos)(?:\*\*)?\s*:", re.IGNORECASE)
HEADING = re.compile(r"^#{1,6}\s+")


def split_paths(value: str) -> list[str]:
    paths = []
    for item in value.split(","):
        cleaned = item.strip().strip("`'\"").strip()
        if cleaned and cleaned.lower() not in {"none", "n/a", "-"}:
            paths.append(cleaned.replace("\\", "/"))
    return paths


def digest(root: Path, relative: str) -> str:
    """Short content digest, `absent` for a missing file, `dir` for a directory. CRLF and LF hash the same."""
    path = inside(root, root / relative)
    if path.is_dir():
        return "dir"
    if not path.is_file():
        return "absent"
    try:
        data = path.read_bytes().replace(b"\r\n", b"\n")
    except OSError:
        return "unreadable"
    return hashlib.sha256(data).hexdigest()[:DIGEST_LEN]


def parse_baseline(value: str) -> dict[str, str]:
    found = {}
    for item in value.split(","):
        if "=" in item:
            path, _, stamp = item.rpartition("=")
            found[path.strip().strip("`'\"").replace("\\", "/")] = stamp.strip()
    return found


def format_baseline(root: Path, paths: list[str]) -> str:
    return ", ".join(f"{path}={digest(root, path)}" for path in paths)


def stamp_file(bundle: Bundle, tasks: list[Block], refresh: bool) -> list[str]:
    """Insert or refresh `- Baseline:` after the `- Files:` line of each pending task. Returns the stamped task ids."""
    path = bundle.tasks.path
    raw = path.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in raw else "\n"
    trailing = raw.endswith(("\n", "\r\n"))
    lines = raw.splitlines()
    stamped = []
    for task in tasks:
        paths = split_paths(task.get("files"))
        if not paths or task_status(task.get("status")) not in PENDING:
            continue
        if task.get("baseline") and not refresh:
            continue
        start = next((i for i, line in enumerate(lines) if re.match(rf"^#{{2,6}}\s+(?:\[[ xX~!]\]\s+)?{re.escape(task.id)}\b", line)), None)
        if start is None:
            continue
        end = next((i for i in range(start + 1, len(lines)) if HEADING.match(lines[i])), len(lines))
        existing = next((i for i in range(start + 1, end) if BASELINE_LINE.match(lines[i])), None)
        files_at = next((i for i in range(start + 1, end) if FILES_LINE.match(lines[i])), None)
        if files_at is None:
            continue
        new_line = f"- Baseline: {format_baseline(bundle.root, paths)}"
        if existing is not None:
            lines[existing] = new_line
        else:
            lines.insert(files_at + 1, new_line)
        stamped.append(task.id)
    if stamped:
        path.write_bytes((eol.join(lines) + (eol if trailing else "")).encode("utf-8"))
    return stamped


def check(bundle: Bundle, report: Report, only: set[str]) -> None:
    tasks = bundle.task_blocks()
    touched: dict[str, list[str]] = {}
    for task in tasks:
        if task_status(task.get("status")) in ACTIVE:
            for item in split_paths(task.get("files")):
                touched.setdefault(item, []).append(task.id)
    checked = 0
    for task in tasks:
        if only and task.id not in only:
            continue
        if task_status(task.get("status")) not in PENDING:
            continue
        paths = split_paths(task.get("files"))
        if not paths:
            continue
        baseline = parse_baseline(task.get("baseline"))
        if not baseline:
            report.info("no-baseline", f"{task.id} has no Baseline; run check_drift.py --stamp before implementing.")
            continue
        checked += 1
        clean = True
        for item in paths:
            if item not in baseline:
                clean = False
                report.warn("unstamped-file", f"{task.id}: {item} was added to Files after the Baseline was stamped.", task.id)
                continue
            try:
                now = digest(bundle.root, item)
            except ConfigError as exc:
                clean = False
                report.fail("outside-root", f"{task.id}: {exc}", task.id)
                continue
            if now == baseline[item]:
                continue
            clean = False
            others = [other for other in touched.get(item, []) if other != task.id]
            if others:
                report.info("expected-drift", f"{task.id}: {item} changed ({baseline[item]} -> {now}), expected: {', '.join(others)} already works on it.")
            else:
                report.warn(
                    "drift",
                    f"{task.id}: {item} changed since the plan ({baseline[item]} -> {now}) and no task of this plan accounts for it. Stop and report to the orchestrator; re-plan or run --stamp --refresh once the change is understood.",
                    task.id,
                )
        if clean:
            report.ok("no-drift", f"{task.id}: {len(paths)} file(s) match the Baseline.")
    report.data["checked_tasks"] = checked


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or stamp the Baseline of pending tasks.")
    add_common_args(parser)
    parser.add_argument("--tasks", help="tasks path relative to the root (overrides --feature)")
    parser.add_argument("--task", action="append", default=[], metavar="TASK-NNN", help="only these tasks (repeatable)")
    parser.add_argument("--stamp", action="store_true", help="write Baseline lines for todo/blocked tasks that have none")
    parser.add_argument("--refresh", action="store_true", help="with --stamp, also rewrite existing Baseline lines (after an intentional re-plan)")
    args = parser.parse_args()
    try:
        bundle = load_bundle(args, need=("tasks",))
        only = set(args.task)
        if args.stamp:
            tasks = [task for task in bundle.task_blocks() if not only or task.id in only]
            stamped = stamp_file(bundle, tasks, args.refresh)
            print(f"Stamped {len(stamped)} task(s): {', '.join(stamped) if stamped else 'none'}.")
            return 0
        report = Report("Drift check", strict=args.strict)
        report.data["tasks"] = bundle.rel(bundle.tasks)
        check(bundle, report, only)
    except ConfigError as exc:
        return config_error(str(exc), args.json)
    return report.emit(args.json)


if __name__ == "__main__":
    raise SystemExit(main())
