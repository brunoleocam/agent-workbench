"""Re-entry of a closed feature: code that changed after the feature's gate passed while its spec did not.

When the Stop gate passes a feature it records a snapshot of the working tree (a git tree object written through a
temporary index, so untracked files count and nothing in the user's index or history changes) and a digest of the
feature's spec. A later session that changes the code above the S floor without touching that spec has moved the
behaviour away from the documents: the spec, tasks and proofs describe an older version. Benchmark long task: the
Workbench's spec still described version 1 after three sessions in 6 of 6 plugin runs.

Used by stop_gate.py (asks once per workspace state on Stop) and by hook.py (one line in the SessionStart context).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import classify_floor  # noqa: E402
from artifacts import harness_doc_dirs, resolve_layout  # noqa: E402

GIT_TIMEOUT = 8


def snapshot_tree(root: Path) -> str | None:
    """Tree id of the working tree as `git add -A` would stage it, written through a temporary index."""
    handle, index = tempfile.mkstemp(prefix="aw-index-")
    os.close(handle)
    os.unlink(index)  # git creates it; an empty file is not a valid index
    env = dict(os.environ, GIT_INDEX_FILE=index)
    try:
        add = subprocess.run(["git", "-C", str(root), "add", "-A", "--", "."], env=env, capture_output=True, text=True, timeout=GIT_TIMEOUT)
        if add.returncode != 0:
            return None
        tree = subprocess.run(["git", "-C", str(root), "write-tree"], env=env, capture_output=True, text=True, timeout=GIT_TIMEOUT)
        return tree.stdout.strip() or None if tree.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None
    finally:
        try:
            os.unlink(index)
        except OSError:
            pass


def spec_digest(root: Path, feature: str) -> str:
    try:
        path = root / resolve_layout(root)["specs_dir"] / f"{feature}.md"
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else ""
    except Exception:
        return ""


def delta(root: Path, old_tree: str, new_tree: str) -> dict:
    """Files and lines changed between two trees, harness documents and .agent-system excluded."""
    done = subprocess.run(["git", "-C", str(root), "diff-tree", "-r", "--numstat", "--no-renames", "-z", old_tree, new_tree],
                          capture_output=True, text=True, timeout=GIT_TIMEOUT)
    if done.returncode != 0:
        return {"floor": None, "files": [], "lines": 0}
    doc_dirs = harness_doc_dirs(resolve_layout(root))
    counted: dict[str, int] = {}
    for record in done.stdout.split("\0"):
        fields = record.split("\t")
        if len(fields) == 3 and fields[2] and not classify_floor.excluded(fields[2], doc_dirs):
            added, removed = fields[0], fields[1]
            counted[fields[2]] = max(1, (int(added) if added.isdigit() else 1) + (int(removed) if removed.isdigit() else 0))
    limits = classify_floor.thresholds({})
    total = sum(counted.values())
    return {"floor": classify_floor.floor_of(len(counted), total, {}, limits), "files": sorted(counted), "lines": total}


def mark_closed(root: Path, item: dict, feature: str) -> dict:
    """The classification of a feature whose gate just passed, with what re-entry needs later."""
    return {**item, "closed": True, "closed_tree": snapshot_tree(root), "closed_spec": spec_digest(root, feature)}


def drifted(root: Path, classifications: dict) -> tuple[str, dict] | None:
    """The most recent closed M+ feature whose code moved at least to the S floor while its spec did not."""
    current = None
    for feature, item in reversed(list(classifications.items())):
        if not isinstance(item, dict) or not item.get("closed") or not item.get("closed_tree"):
            continue
        if classify_floor.rank(str(item.get("effective") or ""), classify_floor.COMPLEXITY) < classify_floor.rank("M", classify_floor.COMPLEXITY):
            continue
        if spec_digest(root, feature) != item.get("closed_spec"):
            return None  # the spec of the newest closed feature moved too: someone updated it
        current = current or snapshot_tree(root)
        if not current:
            return None
        found = delta(root, item["closed_tree"], current)
        if found["floor"] in ("S", "M"):
            return feature, found
        return None  # only the newest closed feature is checked
    return None


def describe(feature: str, found: dict) -> str:
    return (f"{feature} was closed, and since then {len(found['files'])} files and {found['lines']} lines changed "
            f"(floor {found['floor']}) while docs for it did not")
