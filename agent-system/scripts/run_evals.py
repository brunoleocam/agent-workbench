"""Deterministic evals: run each fixture in a temporary copy and compare exit codes and output with expect.json.

Only script behavior is checked. Agent (model) behavior is not evaluated here.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
FIXTURES = SCRIPTS.parent / "evals" / "fixtures"
PYTHON_TOKEN = "__PYTHON__"
SCRIPTS_ALLOWED = {"validate_spec.py", "validate_tasks.py", "check_proofs.py", "validate_verification.py", "lessons.py", "init_project.py"}


class FixtureError(Exception):
    pass


def prepare(source: Path, target: Path, base: str | None) -> None:
    if base:
        base_dir = FIXTURES / base / "project"
        if not base_dir.is_dir() or base_dir.resolve().parent.parent != FIXTURES.resolve():
            raise FixtureError(f"{source.name}: unknown base fixture {base!r}")
        shutil.copytree(base_dir, target, dirs_exist_ok=True)
    if (source / "project").is_dir():
        shutil.copytree(source / "project", target, dirs_exist_ok=True)
    escaped = json.dumps(sys.executable)[1:-1]
    for path in target.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if PYTHON_TOKEN in text:
            path.write_text(text.replace(PYTHON_TOKEN, escaped), encoding="utf-8")


def run_step(step: dict, root: Path) -> list[str]:
    if "write" in step:
        target = (root / step["write"]).resolve()
        if root.resolve() not in target.parents:
            raise FixtureError(f"write outside fixture: {step['write']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(step.get("content", ""), encoding="utf-8")
        return []
    script = step.get("script")
    if script not in SCRIPTS_ALLOWED:
        raise FixtureError(f"unknown script {script!r}")
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / script), "--root", str(root), *step.get("args", [])],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300, check=False,
    )
    output = done.stdout + done.stderr
    problems = []
    if "exit_code" in step and done.returncode != step["exit_code"]:
        problems.append(f"{script}: exit {done.returncode}, expected {step['exit_code']}")
    for needle in step.get("contains", []):
        if needle not in output:
            problems.append(f"{script}: missing {needle!r}")
    for needle in step.get("not_contains", []):
        if needle in output:
            problems.append(f"{script}: unexpected {needle!r}")
    return problems


def run_fixture(folder: Path) -> dict:
    expect_file = folder / "expect.json"
    try:
        expect = json.loads(expect_file.read_text(encoding="utf-8"))
        steps = expect["steps"]
        if not isinstance(steps, list) or not ((folder / "project").is_dir() or expect.get("base")):
            raise KeyError("steps")
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise FixtureError(f"{folder.name}: invalid expect.json or missing project/ ({exc.__class__.__name__})") from exc
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        prepare(folder, root, expect.get("base"))
        problems = []
        for step in steps:
            problems += run_step(step, root)
    return {"fixture": folder.name, "description": expect.get("description", ""), "ok": not problems, "problems": problems}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic eval fixtures.")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("names", nargs="*", help="fixture folder names (default: all)")
    args = parser.parse_args()
    folders = sorted(path for path in FIXTURES.iterdir() if path.is_dir()) if FIXTURES.is_dir() else []
    if args.names:
        folders = [path for path in folders if path.name in set(args.names)]
    if not folders:
        print("No fixture found.", file=sys.stderr)
        return 2
    try:
        results = [run_fixture(folder) for folder in folders]
    except FixtureError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for item in results:
            print(f"[{'PASS' if item['ok'] else 'FAIL'}] {item['fixture']}: {item['description']}")
            for problem in item["problems"]:
                print(f"    {problem}")
        print(f"{sum(item['ok'] for item in results)}/{len(results)} deterministic evals passed.")
    return 0 if all(item["ok"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
