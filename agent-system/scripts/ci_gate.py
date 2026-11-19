"""Pull request check: every M+ feature whose spec or tasks changed against the base must pass its gate.

For each such feature it runs check_proofs.py (fresh proofs on this machine; proofs are never versioned) and then
validate_verification.py. Exit codes: 0 all pass or no M+ feature changed, 1 a feature fails, 2 bad argument or git error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import ConfigError, load_document, resolve_layout  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
LARGE = {"M", "L", "XL"}


def git(root: Path, args: list[str]) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None


def changed_features(root: Path, base: str, layout: dict) -> list[str] | None:
    names = git(root, ["diff", "--name-only", "-z", f"{base}...HEAD", "--", "."])
    if names is None:
        names = git(root, ["diff", "--name-only", "-z", base, "--", "."])
    if names is None:
        return None
    dirs = [layout[key].rstrip("/") + "/" for key in ("specs_dir", "tasks_dir") if layout.get(key)]
    slugs = set()
    for relative in filter(None, names.replace("\\", "/").split("\0")):
        if relative.endswith(".md") and any(relative.startswith(prefix) and "/" not in relative[len(prefix):] for prefix in dirs):
            slugs.add(Path(relative).stem)
    return sorted(slugs)


def all_features(root: Path, layout: dict) -> list[str]:
    folder = root / layout.get("specs_dir", "docs/specs")
    return sorted(path.stem for path in folder.glob("*.md")) if folder.is_dir() else []


def complexity(root: Path, layout: dict, slug: str) -> str:
    path = root / layout.get("specs_dir", "docs/specs") / f"{slug}.md"
    if not path.is_file():
        return ""
    try:
        meta = load_document(path).frontmatter
    except (OSError, ValueError):
        return ""
    if str(meta.get("status", "")).lower() == "superseded":
        return ""
    return str(meta.get("complexity", "")).upper()


def run(script: str, root: Path, slug: str, extra: list[str]) -> int:
    done = subprocess.run([sys.executable, str(SCRIPTS / script), "--root", str(root), "--feature", slug, "--no-record", *extra], check=False)
    return done.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate every M+ feature changed in a pull request.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--base", help="base ref of the pull request (for example origin/main)")
    parser.add_argument("--all", action="store_true", help="check every M+ feature, not only the changed ones")
    parser.add_argument("--allow-shell", action="store_true", help="passed to check_proofs.py; only when the repository owner allows it")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not args.base and not args.all:
        print("[ERROR] pass --base <ref> or --all", file=sys.stderr)
        return 2
    try:
        layout = resolve_layout(root)
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    slugs = all_features(root, layout) if args.all else changed_features(root, args.base, layout)
    if slugs is None:
        print(f"[ERROR] cannot diff against {args.base}; fetch the base with enough history (fetch-depth: 0)", file=sys.stderr)
        return 2
    large = [slug for slug in slugs if complexity(root, layout, slug) in LARGE]
    if not large:
        print("[PASS] no M+ feature changed.")
        return 0
    failed = []
    for slug in large:
        print(f"== {slug}")
        proofs = run("check_proofs.py", root, slug, ["--allow-shell"] if args.allow_shell else [])
        gate = run("validate_verification.py", root, slug, [])
        if gate != 0 or proofs == 2:
            failed.append(slug)
    if failed:
        print(f"[FAIL] gate failed for: {', '.join(failed)}")
        return 1
    print(f"[PASS] gate passed for: {', '.join(large)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
