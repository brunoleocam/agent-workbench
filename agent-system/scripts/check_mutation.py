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
import math
import os
import shutil
import sys
import time
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
    mutation_threshold,
    record,
    system_dir,
    truthy,
    workspace_fingerprint,
)
from lib import redact, utc_now, write_json  # noqa: E402

DEFAULT_BUDGET_S = 1800
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
    """Put back files a killed run left mutated. Returns the restored paths; refuses paths outside the root."""
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
        mtime_ns = saved.get("mtime_ns") if isinstance(saved, dict) else None
        saved = saved.get("backup") if isinstance(saved, dict) else saved
        source = folder / str(saved)
        try:
            target = inside(root, root / str(relative))
        except ConfigError:
            continue
        if source.is_file() and source.parent == folder:
            shutil.copyfile(source, target)
            if isinstance(mtime_ns, int):
                os.utime(target, ns=(mtime_ns, mtime_ns))
            restored.append(str(relative))
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
    return sorted({item.strip().strip("`").replace("\\", "/") for item in raw.split(",") if item.strip()}) if raw else []


def mutate_file(root: Path, relative: str, tests: list, bundle, options, allowed, limit: int, deadline: float) -> dict:
    """Mutants of one file; a mutant is killed when any TEST that covers the file fails or times out."""
    entry = {"mutants": 0, "killed": 0, "timeouts": 0, "survived": [], "reason": "", "error": False, "truncated": False}
    try:
        path = inside(root, root / relative)
    except ConfigError as exc:
        entry["reason"], entry["error"] = str(exc), True
        return entry
    if path.suffix != ".py" or not path.is_file():
        entry["reason"], entry["error"] = "only existing .py files can be mutated", True
        return entry
    raw = path.read_bytes()  # restored byte for byte, so the workspace fingerprint is unchanged
    try:
        original = raw.decode("utf-8")
    except UnicodeDecodeError:
        entry["reason"], entry["error"] = "not UTF-8; cannot mutate it safely", True
        return entry
    try:
        found = sites(ast.parse(original))
    except SyntaxError:
        entry["reason"], entry["error"] = "does not parse", True
        return entry
    if not found:
        entry["reason"] = "no mutation site"
        return entry
    stat = path.stat()
    folder = backup_dir(root)
    shutil.copyfile(path, folder / "backup.py")
    (folder / "pending.json").write_text(json.dumps({relative: {"backup": "backup.py", "mtime_ns": stat.st_mtime_ns}}), encoding="utf-8")
    try:
        if limit and len(found) > limit:
            entry["truncated"] = True
            entry["reason"] = f"capped at {limit} of {len(found)} mutants"
        for number, (target, description) in enumerate(found[:limit] if limit else found, start=1):
            if time.monotonic() > deadline:
                entry["truncated"] = True
                break
            path.write_text(mutate(original, target, description) + "\n", encoding="utf-8")
            # A distinct mtime per mutant: Python validates cached bytecode by source size and whole-second mtime, and a
            # mutant of the same size written within the same second would otherwise import the stale .pyc.
            os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + (number + 1) * 2_000_000_000))
            entry["mutants"] += 1
            outcomes = [check_proofs.execute(test, bundle, options, allowed)["status"] for test in tests]
            if any(status in {"FAIL", "TIMEOUT"} for status in outcomes):
                entry["killed"] += 1
                if "FAIL" not in outcomes:
                    entry["timeouts"] += 1
            else:
                entry["survived"].append(description)
    finally:
        path.write_bytes(raw)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        (folder / "pending.json").unlink(missing_ok=True)
        (folder / "backup.py").unlink(missing_ok=True)
    return entry


def lock_file(root: Path) -> Path:
    return system_dir(root) / "mutation.lock"


def process_alive(pid: int) -> bool:
    """Whether a process with this id is running. Unknown is treated as alive, so a live run is never disturbed."""
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return ctypes.GetLastError() == 5  # access denied: it exists
            try:
                code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return True
                return code.value == 259  # STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        except (AttributeError, OSError):
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def acquire(root: Path) -> list[str]:
    """Take the run lock atomically, then restore what a dead run left behind. Raises ConfigError if a live run holds it.

    The lock comes first: a backup belongs to whoever holds the lock, so a second run never mistakes a live run's
    mutant for an interrupted one.
    """
    lock = lock_file(root)
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            handle = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                holder = int(lock.read_text(encoding="utf-8").strip() or "0")
            except (OSError, ValueError):
                holder = 0
            if holder and process_alive(holder):
                raise ConfigError(f"another check_mutation.py run (process {holder}) holds {lock.relative_to(root).as_posix()}; wait for it to finish, "
                                  "or delete the lock if no check_mutation.py is running (its process id was reused)")
            try:
                # Rename, not delete: of two runs taking over the same dead lock, only one rename succeeds, and the
                # other cannot remove the lock the winner creates next.
                os.replace(lock, lock.with_name(f"{lock.name}.stale-{os.getpid()}"))
                lock.with_name(f"{lock.name}.stale-{os.getpid()}").unlink(missing_ok=True)
            except FileNotFoundError:
                pass
            continue
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(str(os.getpid()))
        break
    else:
        raise ConfigError(f"could not take {lock.relative_to(root).as_posix()}")
    restored = restore_pending(root)  # only a dead run's backup can be here now
    backup_dir(root).mkdir(parents=True, exist_ok=True)
    return restored


def release(root: Path) -> None:
    shutil.rmtree(backup_dir(root), ignore_errors=True)
    try:
        if lock_file(root).read_text(encoding="utf-8").strip() == str(os.getpid()):
            lock_file(root).unlink()
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Mutation score of a feature's TESTs over the Python files they declare in Mutate.")
    add_common_args(parser)
    parser.add_argument("--tasks", help="tasks path relative to the root (overrides --feature)")
    parser.add_argument("--spec", help="spec path, for mutation_min_score")
    parser.add_argument("--tests", help="extra file with TEST definitions")
    parser.add_argument("--max-mutants", type=int, default=0, help="per file, for a quick look (default 0: all); a capped run is partial and does not pass the gate")
    parser.add_argument("--timeout", type=int, default=check_proofs.DEFAULT_TIMEOUT, help="seconds per TEST run; each mutant gets at most 5x the unmutated run, minimum 10 s")
    parser.add_argument("--budget-seconds", type=int, default=DEFAULT_BUDGET_S, help=f"wall-clock limit for the whole run (default {DEFAULT_BUDGET_S}); the score is marked truncated")
    parser.add_argument("--allow", action="append", default=[], metavar="EXE")
    parser.add_argument("--allow-shell", action="store_true")
    parser.add_argument("--allow-inline", action="store_true")
    args = parser.parse_args()
    try:
        bundle = load_bundle(args, need=("tasks",))
        threshold, source, problem = mutation_threshold(bundle.spec.frontmatter if bundle.spec else {}, bundle.layout)
        if problem:
            raise ConfigError(problem)
        tasks_by_id = {task.id: task for task in bundle.task_blocks()}
        tests = [test for test in bundle.test_blocks() if truthy(test.get("required"), True) and targets_of(test, tasks_by_id)]
        if not tests:
            raise ConfigError("No required TEST declares Mutate (on the TEST or its task).")
        restored = acquire(bundle.root)
    except ConfigError as exc:
        return config_error(str(exc), args.json)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # the TESTs this process starts never cache a mutant's bytecode
    layout_allow = bundle.layout.get("proof_allow") if isinstance(bundle.layout.get("proof_allow"), list) else []
    allowed = check_proofs.ALLOWED_EXECUTABLES | {check_proofs.exe_name(item) for item in [*args.allow, *layout_allow] if isinstance(item, str)}
    options = SimpleNamespace(allow_shell=args.allow_shell, allow_inline=args.allow_inline, dry_run=False, timeout=args.timeout)
    before = workspace_fingerprint(bundle.root, bundle.layout)
    data = {"version": 3, "feature": bundle.slug, "updated_at": utc_now(), "fingerprint": before["digest"], "min_score": threshold,
            "tests": {test.id: redact(test.get("command"), 300) for test in tests},
            "targets": {test.id: targets_of(test, tasks_by_id) for test in tests},
            "status": "ERROR", "reason": "", "mutants": 0, "killed": 0, "score": None, "truncated": False, "files": {}}
    deadline = time.monotonic() + max(1, args.budget_seconds)
    try:
        baseline = [(test, check_proofs.execute(test, bundle, options, allowed)) for test in tests]
        broken = [(test.id, proof) for test, proof in baseline if proof["status"] != "PASS"]
        if broken:
            test_id, proof = broken[0]
            data["status"] = "FAIL" if proof["status"] == "FAIL" else "ERROR"
            data["reason"] = f"{test_id} does not pass unmutated ({proof['status']}: {proof.get('reason') or ''})"
        else:
            slowest = max(float(proof.get("duration_s") or 0) for _, proof in baseline)
            options.timeout = max(1, min(args.timeout, max(10, math.ceil(5 * slowest))))
            by_file: dict[str, list] = {}
            for test in tests:
                for relative in targets_of(test, tasks_by_id):
                    by_file.setdefault(relative, []).append(test)
            for relative, covering in sorted(by_file.items()):
                entry = mutate_file(bundle.root, relative, covering, bundle, options, allowed, max(0, args.max_mutants), deadline)
                data["files"][relative] = entry
                data["mutants"] += entry["mutants"]
                data["killed"] += entry["killed"]
                data["truncated"] = data["truncated"] or entry["truncated"]
            errors = [f"{name}: {entry['reason']}" for name, entry in data["files"].items() if entry["error"]]
            if errors:
                data["reason"] = "; ".join(errors)
            elif not data["mutants"]:
                data["reason"] = "no mutation site in the listed files"
            else:
                data["score"] = round(data["killed"] / data["mutants"], 3)
                data["status"] = "MEASURED"
                if data["truncated"]:
                    data["reason"] = "partial run (time budget or --max-mutants); the gate needs a complete run"
    finally:
        release(bundle.root)
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
            print(f"[{label}] {bundle.slug}: mutation score {data['score']} ({data['killed']}/{data['mutants']} killed), minimum {threshold if threshold is not None else 'not set'}"
                  + (" (truncated by the time budget)" if data["truncated"] else ""))
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
