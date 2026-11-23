#!/usr/bin/env python3
"""Arm-neutral mutation score of the tests an agent wrote (stdlib only).

Mutates the application files under app/ (never tests), one mutation at a time, and runs the
agent's own test suite. Deterministic sample (seeded). Prints JSON.
  python mutation.py --root <project> [--max 60] [--timeout 120] [--budget 1200]
"""
import argparse
import ast
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

SWAPS = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE,
         ast.LtE: ast.Gt, ast.Add: ast.Sub, ast.Sub: ast.Add, ast.And: ast.Or, ast.Or: ast.And,
         ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.In: ast.NotIn, ast.NotIn: ast.In}


def sites(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare):
            for i, op in enumerate(n.ops):
                if type(op) in SWAPS:
                    out.append(("cmp", n, i))
        elif isinstance(n, ast.BinOp) and type(n.op) in SWAPS:
            out.append(("bin", n, 0))
        elif isinstance(n, ast.BoolOp):
            out.append(("bool", n, 0))
        elif isinstance(n, ast.Constant) and isinstance(n.value, bool):
            out.append(("const", n, 0))
        elif isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool) and n.value not in (0,):
            out.append(("const", n, 0))
        elif isinstance(n, ast.Raise):
            out.append(("raise", n, 0))
    return out


def apply(kind, node, i):
    if kind == "cmp":
        old = node.ops[i]
        node.ops[i] = SWAPS[type(old)]()
        return lambda: node.ops.__setitem__(i, old)
    if kind == "bin":
        old = node.op
        node.op = SWAPS[type(old)]()
        return lambda: setattr(node, "op", old)
    if kind == "bool":
        old = node.op
        node.op = ast.Or() if isinstance(old, ast.And) else ast.And()
        return lambda: setattr(node, "op", old)
    if kind == "const":
        old = node.value
        node.value = (not old) if isinstance(old, bool) else old + 1
        return lambda: setattr(node, "value", old)
    if kind == "raise":
        # replace the raise by a no-op via swapping its exception for a harmless name
        old = node.exc
        node.exc = None
        node.cause = None
        return lambda: setattr(node, "exc", old)


def run_tests(root, timeout):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"],
                           cwd=root, env=env, capture_output=True, timeout=timeout)
        return r.returncode
    except subprocess.TimeoutExpired:
        return "timeout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--max", type=int, default=60)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--budget", type=int, default=1200)
    a = ap.parse_args()
    root = Path(a.root)
    files = sorted(p for p in (root / "app").rglob("*.py") if "test" not in p.name.lower())
    base = run_tests(root, a.timeout)
    if base != 0:
        print(json.dumps({"score": None, "reason": f"agent tests do not pass unmutated (exit {base})"}))
        return
    pool = []
    for f in files:
        src = f.read_text(encoding="utf-8")
        tree = ast.parse(src)
        for idx in range(len(sites(tree))):
            pool.append((f, idx))
    random.Random(7).shuffle(pool)
    chosen = pool[:a.max]
    killed = survived = timeouts = 0
    t0 = time.time()
    done = 0
    for f, idx in chosen:
        if time.time() - t0 > a.budget:
            break
        orig = f.read_text(encoding="utf-8")
        tree = ast.parse(orig)
        kind, node, i = sites(tree)[idx]
        apply(kind, node, i)
        try:
            mutated = ast.unparse(ast.fix_missing_locations(tree))
            compile(mutated, str(f), "exec")
        except Exception:
            continue
        f.write_text(mutated, encoding="utf-8")
        try:
            code = run_tests(root, a.timeout)
        finally:
            f.write_text(orig, encoding="utf-8")
        done += 1
        if code == 0:
            survived += 1
        elif code == "timeout":
            timeouts += 1
            killed += 1
        else:
            killed += 1
    total = killed + survived
    print(json.dumps({"score": (killed / total) if total else None, "mutants_run": done, "pool": len(pool),
                      "killed": killed, "survived": survived, "timeouts": timeouts,
                      "partial": done < min(len(pool), a.max)}))


if __name__ == "__main__":
    main()
