"""Pull request check: every M+ feature whose spec or tasks changed against the base must pass its gate.

A feature counts as changed when its spec or tasks changed, or when its tasks list a changed file in `Files`. Its
complexity is the larger of the base and the head, so a pull request cannot lower its own gate. For each such feature
it runs check_proofs.py (fresh proofs on this machine; proofs are never versioned), check_mutation.py when a minimum
mutation score is set, and then validate_verification.py. Exit codes: 0 all pass or no M+ feature changed, 1 a feature fails, 2 bad argument or git error.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import ConfigError, load_document, mutation_threshold, resolve_layout  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
LARGE = {"M", "L", "XL"}
ORDER = ("XS", "S", "M", "L", "XL")


def git(root: Path, args: list[str]) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None


def changed_paths(root: Path, base: str) -> list[str] | None:
    names = git(root, ["diff", "--name-only", "--no-renames", "-z", f"{base}...HEAD", "--", "."])
    if names is None:
        names = git(root, ["diff", "--name-only", "--no-renames", "-z", base, "--", "."])
    return None if names is None else [item for item in names.replace("\\", "/").split("\0") if item]


def task_files(root: Path, layout: dict, slug: str) -> set[str]:
    """Paths and folders named in the `Files` field of a feature's tasks."""
    path = root / layout.get("tasks_dir", "docs/tasks") / f"{slug}.md"
    try:
        tasks = load_document(path) if path.is_file() else None
    except (OSError, ValueError):
        return set()
    found = set()
    for block in tasks.of_kind("TASK") if tasks else []:
        for item in block.get("files").split(","):
            item = item.strip().strip("`").replace("\\", "/")
            if item:
                found.add(item)
    return found


def touches(paths: list[str], files: set[str]) -> bool:
    return any(path == item or (item.endswith("/") and path.startswith(item)) or path.startswith(item.rstrip("/") + "/") for path in paths for item in files)


def changed_features(root: Path, base: str, layout: dict) -> list[str] | None:
    """Features whose spec or tasks changed, plus features whose tasks list a changed file in `Files`."""
    paths = changed_paths(root, base)
    if paths is None:
        return None
    dirs = [layout[key].rstrip("/") + "/" for key in ("specs_dir", "tasks_dir") if layout.get(key)]
    slugs = set()
    for relative in paths:
        if relative.endswith(".md") and any(relative.startswith(prefix) and "/" not in relative[len(prefix):] for prefix in dirs):
            slugs.add(Path(relative).stem)
    for slug in all_features(root, layout):
        if slug not in slugs and touches(paths, task_files(root, layout, slug)):
            slugs.add(slug)
    return sorted(slugs)


def all_features(root: Path, layout: dict) -> list[str]:
    folder = root / layout.get("specs_dir", "docs/specs")
    return sorted(path.stem for path in folder.glob("*.md")) if folder.is_dir() else []


def frontmatter_of(text: str) -> dict:
    lines = text.splitlines()
    meta = {}
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, _, value = line.partition(":")
            meta[key.strip()] = value.split("#", 1)[0].strip()
    return meta


def complexity(root: Path, layout: dict, slug: str, base: str | None = None) -> str:
    """The spec's complexity; with a base, the larger of the base and the head, so a PR cannot lower its own gate."""
    relative = f"{layout.get('specs_dir', 'docs/specs')}/{slug}.md"
    path = root / relative
    if not path.is_file():
        return ""
    try:
        meta = load_document(path).frontmatter
    except (OSError, ValueError):
        return ""
    if str(meta.get("status", "")).lower() == "superseded":
        return ""
    value = str(meta.get("complexity", "")).upper()
    if base:
        before = str(frontmatter_of(git(root, ["show", f"{base}:{relative}"]) or "").get("complexity", "")).upper()
        if before in ORDER and (value not in ORDER or ORDER.index(before) > ORDER.index(value)):
            return before
    return value


def merge_base(root: Path, base: str) -> str:
    found = (git(root, ["merge-base", base, "HEAD"]) or "").strip()
    return found or base


def removed_large(root: Path, layout: dict, base: str, slugs: list[str]) -> list[str]:
    """Features that were M+ at the merge base and whose spec this pull request deleted, renamed, or superseded."""
    found = []
    for slug in slugs:
        relative = f"{layout.get('specs_dir', 'docs/specs')}/{slug}.md"
        before = frontmatter_of(git(root, ["show", f"{base}:{relative}"]) or "")
        if str(before.get("complexity", "")).upper() not in LARGE or str(before.get("status", "")).lower() == "superseded":
            continue
        path = root / relative
        try:
            status = str(load_document(path).frontmatter.get("status", "")).lower() if path.is_file() else "removed"
        except (OSError, ValueError):
            status = "removed"
        if status in {"removed", "superseded"}:
            found.append(f"{slug} ({status})")
    return found


def needs_mutation(root: Path, layout: dict, slug: str) -> bool:
    spec = root / layout.get("specs_dir", "docs/specs") / f"{slug}.md"
    try:
        meta = load_document(spec).frontmatter if spec.is_file() else {}
    except (OSError, ValueError):
        meta = {}
    threshold, _, problem = mutation_threshold(meta, layout)
    return threshold is not None and not problem


def run(script: str, root: Path, slug: str, extra: list[str]) -> int:
    done = subprocess.run([sys.executable, str(SCRIPTS / script), "--root", str(root), "--feature", slug, "--no-record", *extra], check=False)
    return done.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate every M+ feature changed in a pull request.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--base", help="base ref of the pull request (for example origin/main)")
    parser.add_argument("--all", action="store_true", help="check every M+ feature, not only the changed ones")
    parser.add_argument("--allow-downgrade", action="store_true", help="accept a spec whose complexity this pull request lowered below M")
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
    point = None if args.all else merge_base(root, args.base)
    large = [slug for slug in slugs if complexity(root, layout, slug, point) in LARGE]
    dropped = [] if args.all or args.allow_downgrade else removed_large(root, layout, point, slugs)
    if dropped:
        print(f"[FAIL] this pull request removes or supersedes the spec of M+ features: {', '.join(dropped)}. Pass --allow-downgrade if the repository owner agrees.")
        if not large:
            return 1
    if not large:
        print("[PASS] no M+ feature changed.")
        return 0
    failed = [item.split(" ", 1)[0] for item in dropped]
    if not args.all:
        for slug in large:
            head_value = complexity(root, layout, slug)
            if head_value not in LARGE and not args.allow_downgrade:
                print(f"[FAIL] {slug}: this pull request lowers its complexity to {head_value or 'none'}, which would skip the M+ gate. Pass --allow-downgrade if the repository owner agrees.")
                failed.append(slug)
    for slug in large:
        if slug in failed:
            continue
        print(f"== {slug}")
        shell = ["--allow-shell"] if args.allow_shell else []
        proofs = run("check_proofs.py", root, slug, shell)
        mutation = run("check_mutation.py", root, slug, shell) if needs_mutation(root, layout, slug) else 0
        gate = run("validate_verification.py", root, slug, [])
        if gate != 0 or proofs == 2 or mutation == 2:
            failed.append(slug)
    if failed:
        print(f"[FAIL] gate failed for: {', '.join(failed)}")
        return 1
    print(f"[PASS] gate passed for: {', '.join(large)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
