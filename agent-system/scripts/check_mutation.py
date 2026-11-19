"""Mutation proof: does a TEST fail when the code it covers is broken on purpose?

For the TESTs with a `Mutate` field (or whose task has one), this script makes one small change at a time to the
listed Python files (a flipped comparison, a swapped operator, a negated condition, a changed constant, `return None`),
runs the TEST command through the same policy as check_proofs.py, and counts the mutants the TEST kills (exit != 0).
The score is killed / mutants. Results go to .agent-system/proofs/<feature>.mutation.json with the workspace
fingerprint; validate_verification.py requires a minimum score when the spec or layout.json sets one.

Files are mutated in place and restored after each mutant. A backup lives in .agent-system/mutation/ until the run
ends; a later run restores it first if a run was killed. Standard library only; Python files only (other languages:
the project's own tool, such as Stryker or Infection, outside this gate). A mutant counts as killed when any TEST that
lists the file fails or times out, so the score belongs to the feature's tests together, not to one TEST.
Exit codes: 0 score at or above the minimum (or no minimum), 1 below it or a TEST failing unmutated, 2 configuration error.
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_proofs  # noqa: E402
from artifacts import (  # noqa: E402
    ConfigError,
    add_common_args,
    config_error,
    inside,
    load_bundle,
    record,
    system_dir,
    workspace_fingerprint,
)
from lib import redact, utc_now, write_json  # noqa: E402

DEFAULT_MAX_MUTANTS = 40
COMPARE_SWAP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
                ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot, ast.IsNot: ast.Is}
BINOP_SWAP = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult, ast.FloorDiv: ast.Mult, ast.Mod: ast.Mult}
BOOL_SWAP = {ast.And: ast.Or, ast.Or: ast.And}


def mutation_file(root: Path, slug: str) -> Path:
    return system_dir(root) / "proofs" / f"{slug}.mutation.json"


def backup_dir(root: Path) -> Path:
    return system_dir(root) / "mutation"


def sites(tree: ast.AST) -> list[tuple[int, str]]:
    """(node index in ast.walk order, description) of every mutation site, in a stable order."""
    found = []
    for index, node in enumerate(ast.walk(tree)):
        line = getattr(node, "lineno", 0)
        if isinstance(node, ast.Compare):
            for position, op in enumerate(node.ops):
                if type(op) in COMPARE_SWAP:
                    found.append((index, f"line {line}: {type(op).__name__} -> {COMPARE_SWAP[type(op)].__name__} (#{position})"))
        elif isinstance(node, ast.BinOp) and type(node.op) in BINOP_SWAP:
            found.append((index, f"line {line}: {type(node.op).__name__} -> {BINOP_SWAP[type(node.op)].__name__}"))
        elif isinstance(node, ast.BoolOp) and type(node.op) in BOOL_SWAP:
            found.append((index, f"line {line}: {type(node.op).__name__} -> {BOOL_SWAP[type(node.op)].__name__}"))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            found.append((index, f"line {line}: remove not"))
        elif isinstance(node, (ast.If, ast.While)):
            found.append((index, f"line {line}: negate {type(node).__name__.lower()} condition"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            found.append((index, f"line {line}: {node.value} -> {not node.value}"))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int):
            found.append((index, f"line {line}: {node.value} -> {node.value + 1}"))
        elif isinstance(node, ast.Return) and node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None):
            found.append((index, f"line {line}: return None"))
    return found


def mutate(source: str, target: int, description: str) -> str:
    tree = ast.parse(source)
    for index, node in enumerate(ast.walk(tree)):
        if index != target:
            continue
        if isinstance(node, ast.Compare):
            position = int(description.rsplit("#", 1)[1].rstrip(")"))
            node.ops[position] = COMPARE_SWAP[type(node.ops[position])]()
        elif isinstance(node, ast.BinOp):
            node.op = BINOP_SWAP[type(node.op)]()
        elif isinstance(node, ast.BoolOp):
            node.op = BOOL_SWAP[type(node.op)]()
        elif isinstance(node, ast.UnaryOp):
            return ast.unparse(_replace(tree, node, node.operand))
        elif isinstance(node, (ast.If, ast.While)):
            node.test = ast.UnaryOp(op=ast.Not(), operand=node.test)
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            node.value = not node.value
        elif isinstance(node, ast.Constant):
            node.value = node.value + 1
        elif isinstance(node, ast.Return):
            node.value = ast.Constant(value=None)
        break
    return ast.unparse(ast.fix_missing_locations(tree))


def _replace(tree: ast.AST, old: ast.AST, new: ast.AST) -> ast.AST:
    for parent in ast.walk(tree):
        for name, value in ast.iter_fields(parent):
            if value is old:
                setattr(parent, name, new)
                return ast.fix_missing_locations(tree)
            if isinstance(value, list):
                for position, item in enumerate(value):
                    if item is old:
                        value[position] = new
                        return ast.fix_missing_locations(tree)
    return tree


def restore_pending(root: Path) -> list[str]:
    """Put back files a killed run left mutated. Returns the restored paths."""
    folder = backup_dir(root)
    manifest = folder / "pending.json"
    if not manifest.is_file():
        return []
    restored = []
    try:
        pending = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pending = {}
    for relative, saved in (pending.items() if isinstance(pending, dict) else []):
        source = folder / saved
        if source.is_file():
            shutil.copyfile(source, root / relative)
            restored.append(relative)
    shutil.rmtree(folder, ignore_errors=True)
    return restored


def targets_of(test, tasks_by_id: dict) -> list[str]:
    raw = test.get("mutate")
    if not raw:
        for task_id in test.ids("task", "TASK"):
            task = tasks_by_id.get(task_id)
            if task and task.get("mutate"):
                raw = task.get("mutate")
                break
    return [item.strip().strip("`") for item in raw.split(",") if item.strip()] if raw else []


def min_score(bundle) -> float | None:
    value = (bundle.spec.frontmatter.get("mutation_min_score") if bundle.spec else None) or ""
    if not value:
        layout_value = (bundle.layout.get("mutation") or {}).get("min_score") if isinstance(bundle.layout.get("mutation"), dict) else None
        value = "" if layout_value is None else str(layout_value)
    try:
        score = float(value)
    except ValueError:
        return None
    return score if 0 < score <= 1 else None


def mutate_file(root: Path, relative: str, tests: list, bundle, options, allowed, limit: int) -> dict:
    """Mutants of one file; a mutant is killed when any TEST that covers the file fails or times out."""
    entry = {"mutants": 0, "killed": 0, "survived": [], "reason": ""}
    try:
        path = inside(root, root / relative)
    except ConfigError as exc:
        entry["reason"] = str(exc)
        return entry
    if path.suffix != ".py" or not path.is_file():
        entry["reason"] = "only existing .py files can be mutated"
        return entry
    raw = path.read_bytes()  # restored byte for byte, so the workspace fingerprint is unchanged
    original = raw.decode("utf-8", errors="replace")
    try:
        found = sites(ast.parse(original))
    except SyntaxError:
        entry["reason"] = "does not parse"
        return entry
    if not found:
        entry["reason"] = "no mutation site"
        return entry
    folder = backup_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, folder / "backup.py")
    (folder / "pending.json").write_text(json.dumps({relative: "backup.py"}), encoding="utf-8")
    try:
        for target, description in found[:limit]:
            path.write_text(mutate(original, target, description) + "\n", encoding="utf-8")
            entry["mutants"] += 1
            if any(check_proofs.execute(test, bundle, options, allowed)["status"] in {"FAIL", "TIMEOUT"} for test in tests):
                entry["killed"] += 1
            else:
                entry["survived"].append(description)
    finally:
        path.write_bytes(raw)
        shutil.rmtree(folder, ignore_errors=True)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Mutation score of a feature's TESTs over the Python files they declare in Mutate.")
    add_common_args(parser)
    parser.add_argument("--tasks", help="tasks path relative to the root (overrides --feature)")
    parser.add_argument("--spec", help="spec path, for mutation_min_score")
    parser.add_argument("--tests", help="extra file with TEST definitions")
    parser.add_argument("--max-mutants", type=int, default=DEFAULT_MAX_MUTANTS, help=f"per file (default {DEFAULT_MAX_MUTANTS})")
    parser.add_argument("--timeout", type=int, default=check_proofs.DEFAULT_TIMEOUT)
    parser.add_argument("--allow", action="append", default=[], metavar="EXE")
    parser.add_argument("--allow-shell", action="store_true")
    parser.add_argument("--allow-inline", action="store_true")
    args = parser.parse_args()
    try:
        bundle = load_bundle(args, need=("tasks",))
    except ConfigError as exc:
        return config_error(str(exc), args.json)
    restored = restore_pending(bundle.root)
    tasks_by_id = {task.id: task for task in bundle.task_blocks()}
    tests = [test for test in bundle.test_blocks() if targets_of(test, tasks_by_id)]
    if not tests:
        return config_error("No TEST declares Mutate (on the TEST or its task).", args.json)
    layout_allow = bundle.layout.get("proof_allow") if isinstance(bundle.layout.get("proof_allow"), list) else []
    allowed = check_proofs.ALLOWED_EXECUTABLES | {check_proofs.exe_name(item) for item in [*args.allow, *layout_allow] if isinstance(item, str)}
    options = SimpleNamespace(allow_shell=args.allow_shell, allow_inline=args.allow_inline, dry_run=False, timeout=args.timeout)
    threshold = min_score(bundle)
    before = workspace_fingerprint(bundle.root, bundle.layout)
    data = {"version": 2, "feature": bundle.slug, "updated_at": utc_now(), "fingerprint": before["digest"], "min_score": threshold,
            "tests": {test.id: redact(test.get("command"), 300) for test in tests}, "status": "ERROR", "reason": "",
            "mutants": 0, "killed": 0, "score": None, "files": {}}
    broken = [(test.id, proof) for test in tests for proof in [check_proofs.execute(test, bundle, options, allowed)] if proof["status"] != "PASS"]
    if broken:
        test_id, proof = broken[0]
        data["status"] = "FAIL" if proof["status"] == "FAIL" else "ERROR"
        data["reason"] = f"{test_id} does not pass unmutated ({proof['status']}: {proof.get('reason') or ''})"
    else:
        by_file: dict[str, list] = {}
        for test in tests:
            for relative in targets_of(test, tasks_by_id):
                by_file.setdefault(relative.replace("\\", "/"), []).append(test)
        for relative, covering in sorted(by_file.items()):
            entry = mutate_file(bundle.root, relative, covering, bundle, options, allowed, max(1, args.max_mutants))
            data["files"][relative] = entry
            data["mutants"] += entry["mutants"]
            data["killed"] += entry["killed"]
        problems = [f"{name}: {entry['reason']}" for name, entry in data["files"].items() if entry["reason"]]
        if problems:
            data["reason"] = "; ".join(problems)
        if data["mutants"]:
            data["score"] = round(data["killed"] / data["mutants"], 3)
            data["status"] = "MEASURED"
    target = mutation_file(bundle.root, bundle.slug)
    write_json(target, data)
    code = 0 if data["status"] == "MEASURED" and (threshold is None or data["score"] >= threshold) else 1
    if args.json:
        print(json.dumps({"ok": code == 0, "restored": restored, **data}, indent=2, ensure_ascii=False))
    else:
        if restored:
            print(f"[WARN] restored files left mutated by an interrupted run: {', '.join(restored)}")
        if data["status"] == "MEASURED":
            label = "FAIL" if code else "PASS"
            print(f"[{label}] {bundle.slug}: mutation score {data['score']} ({data['killed']}/{data['mutants']} killed), minimum {threshold if threshold is not None else 'not set'}")
            for name, entry in data["files"].items():
                print(f"  {name}: {entry['killed']}/{entry['mutants']} killed" + (f" ({entry['reason']})" if entry["reason"] else ""))
                for survivor in entry["survived"][:5]:
                    print(f"    survived: {survivor}")
        else:
            print(f"[{data['status']}] {bundle.slug}: {data['reason']}")
        print(f"Results in {target.relative_to(bundle.root).as_posix()}.")
    record(bundle.root, "MUTATION_COMPLETED", f"check_mutation {bundle.slug}", f"{'passed' if code == 0 else 'failed'} score={data['score']}", bundle.slug, "tester", not args.no_record)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
