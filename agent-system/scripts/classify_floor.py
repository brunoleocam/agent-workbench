"""Deterministic floor for the request classification, measured from the git diff.

The model declares the complexity; this script measures the change (files, lines, attack surfaces) against a git base
and refuses a declaration below the floor unless a justification is recorded. Exit codes: 0 accepted (also a justified
downgrade or an unknown floor), 1 declared below the floor, 2 bad argument.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import ConfigError, harness_doc_dirs, load_layout, resolve_layout  # noqa: E402
from lib import append_event, apply_semantic_state, load_state, local_stamp, opted_in, redact, save_state, utc_now  # noqa: E402

COMPLEXITY = ("XS", "S", "M", "L", "XL")
SECURITY = ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
DEFAULTS = {"m_files": 6, "m_lines": 300, "s_files": 2, "s_lines": 20}
# Word-level name heuristics (path segments split on separators and camelCase), so `AUTHORS` or `secretary` do not
# match. A hint for the floor, not a security verdict.
SURFACE_WORDS = {
    "authentication": {"auth", "authn", "authz", "authentication", "authorization", "login", "logout", "signin", "signup", "jwt", "oauth", "password", "passwords"},
    "file_upload": {"upload", "uploads", "uploader", "multer", "attachment", "attachments"},
    "payments": {"payment", "payments", "stripe", "checkout", "billing", "invoice", "invoices"},
    "cryptography": {"crypto", "cryptography", "encrypt", "encryption", "decrypt", "cipher"},
    "multi_tenant": {"tenant", "tenants", "tenancy"},
    "secrets_config": {"secret", "secrets", "vault", "credentials"},
}
SURFACE_DIRS = {"api": {"api", "controllers", "routes"}, "database": {"migrations", "prisma"}}
INFRA_NAMES = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
# Tooling and caches only; build outputs such as bin/ or dist/ count when they are tracked or not ignored.
FLOOR_SKIP = {".git", ".cursor", ".agent-system", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv", ".tox", ".next", ".gradle"}
DEFAULT_BRANCHES = ("main", "master", "origin/main", "origin/master")
WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


def rank(value: str, order: tuple[str, ...]) -> int:
    return order.index(value) if value in order else -1


def git(root: Path, args: list[str]) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.decode("utf-8", errors="replace") if done.returncode == 0 else None


def head(root: Path) -> str | None:
    out = git(root, ["rev-parse", "HEAD"])
    return out.strip() if out else None


def default_base(root: Path) -> str | None:
    """Where the current work started: the merge base with the default branch when on another branch, else HEAD.

    Measuring against HEAD alone would let a change shrink to nothing once it is committed.
    """
    current = head(root)
    if not current:
        return None
    candidates = []
    remote_head = (git(root, ["symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD"]) or "").strip()
    if remote_head:
        candidates.append(remote_head)
    candidates += [name for name in DEFAULT_BRANCHES if name not in candidates]
    for name in candidates:
        tip = (git(root, ["rev-parse", "-q", "--verify", f"{name}^{{commit}}"]) or "").strip()
        if not tip or tip == current:
            continue
        merge_base = (git(root, ["merge-base", "HEAD", tip]) or "").strip()
        if merge_base and merge_base != current:
            return merge_base
    return current


def words(relative: str) -> set[str]:
    found = set()
    for segment in relative.replace("\\", "/").split("/"):
        for piece in re.split(r"[^A-Za-z0-9]+", segment):
            found |= {item.lower() for item in WORD.findall(piece)}
            found.add(piece.lower())
    return found


def surfaces_of(relative: str, listed: dict[str, set[str]]) -> set[str]:
    lowered = relative.lower()
    parts = lowered.split("/")
    names = words(relative)
    found = {name for name, paths in listed.items() if relative in paths}
    found |= {name for name, vocabulary in SURFACE_WORDS.items() if names & vocabulary}
    found |= {name for name, dirs in SURFACE_DIRS.items() if any(part in dirs for part in parts[:-1])}
    if parts[-1] == ".env.example":
        found.add("secrets_config")
    if lowered.endswith(".sql"):
        found.add("database")
    if parts[-1] in INFRA_NAMES or lowered.endswith(".tf") or lowered.startswith(".github/workflows/"):
        found.add("infrastructure")
    return found


def excluded(relative: str, doc_dirs: list[str]) -> bool:
    parts = relative.split("/")
    if any(part in FLOOR_SKIP for part in parts[:-1]):
        return True
    return relative.lower().endswith(".md") and any(relative.startswith(folder + "/") for folder in doc_dirs)


def line_count(path: Path) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return 1
    if b"\0" in data[:8192]:  # binary: one change, as git numstat reports it
        return 1
    return max(1, len(data.splitlines()))


def thresholds(layout: dict) -> dict:
    overrides = layout.get("overrides") if isinstance(layout.get("overrides"), dict) else {}
    custom = overrides.get("classification_floor") if isinstance(overrides.get("classification_floor"), dict) else {}
    return {key: custom[key] if isinstance(custom.get(key), int) and not isinstance(custom.get(key), bool) and custom[key] > 0 else value
            for key, value in DEFAULTS.items()}


def floor_of(files: int, lines: int, surfaces: dict, limits: dict) -> str:
    if files >= limits["m_files"] or lines >= limits["m_lines"] or surfaces:
        return "M"
    if files >= limits["s_files"] or lines >= limits["s_lines"]:
        return "S"
    return "XS"


def measure(root: Path, base: str | None = None) -> dict:
    """Files, lines and surfaces changed against `base` (default: default_base), plus untracked files. floor None without git."""
    root = root.resolve()
    if (git(root, ["rev-parse", "--is-inside-work-tree"]) or "").strip() != "true":
        return {"floor": None, "security_floor": None, "files": [], "lines": 0, "surfaces": {}, "base": None, "reason": "not a git repository"}
    base = base or default_base(root)
    try:
        raw = load_layout(root)
        layout = resolve_layout(root, raw)
    except ConfigError as exc:
        return {"floor": None, "security_floor": None, "files": [], "lines": 0, "surfaces": {}, "base": base, "reason": str(exc)}
    doc_dirs = harness_doc_dirs(layout)
    lines: dict[str, int] = {}
    if base:
        # --no-renames: a rename is reported as a deletion plus an addition, so a moved and edited file is never lost.
        numstat = git(root, ["diff", "--numstat", "--no-renames", "-z", base, "--", "."])
        if numstat is None:
            return {"floor": None, "security_floor": None, "files": [], "lines": 0, "surfaces": {}, "base": base, "reason": f"unknown base {base}"}
        for record in numstat.split("\0"):
            fields = record.split("\t")
            if len(fields) == 3 and fields[2]:
                added, removed = fields[0], fields[1]
                lines[fields[2]] = max(1, (int(added) if added.isdigit() else 1) + (int(removed) if removed.isdigit() else 0))
    others = git(root, ["ls-files", "--others", "--exclude-standard", "-z", "--", "."]) or ""
    for relative in filter(None, others.split("\0")):
        lines[relative] = line_count(root / relative)
    counted = {path.replace("\\", "/"): count for path, count in lines.items() if not excluded(path.replace("\\", "/"), doc_dirs)}
    signals = raw.get("signals") if isinstance(raw.get("signals"), dict) else {}
    listed_raw = signals.get("attack_surfaces") if isinstance(signals.get("attack_surfaces"), dict) else {}
    listed = {str(name): {str(item) for item in items} for name, items in listed_raw.items() if isinstance(items, list)}
    surfaces: dict[str, list[str]] = {}
    for relative in sorted(counted):
        for name in sorted(surfaces_of(relative, listed)):
            surfaces.setdefault(name, []).append(relative)
    limits = thresholds(raw)
    total = sum(counted.values())
    return {
        "floor": floor_of(len(counted), total, surfaces, limits),
        "security_floor": "MEDIUM" if surfaces else "NONE",
        "files": sorted(counted),
        "lines": total,
        "surfaces": surfaces,
        "base": base,
        "thresholds": limits,
        "reason": "",
    }


def describe(found: dict) -> str:
    if found["floor"] is None:
        return f"floor unknown ({found['reason']})"
    text = f"floor {found['floor']} ({len(found['files'])} files, {found['lines']} lines"
    if found["surfaces"]:
        text += "; surfaces: " + ", ".join(sorted(found["surfaces"]))
    return text + ")"


def record(root: Path, feature: str, kind: str, summary: str, result: str, classification: dict) -> None:
    if not opted_in(root):
        return
    try:
        state = load_state(root)
        event = {
            "timestamp": utc_now(),
            "local_time": local_stamp(),
            "session": state.get("session_id") or "",
            "agent": "orchestrator",
            "event": kind,
            "task": state.get("active_task"),
            "feature": redact(feature, 80) if feature else None,
            "files": [],
            "summary": redact(summary, 240),
            "result": redact(result, 160),
            "classification": {key: classification.get(key) for key in ("declared", "floor", "effective", "security", "downgraded")},
        }
        append_event(root, event)
        state = apply_semantic_state(state, event)
        store(state, classification)
        save_state(root, state)
    except (OSError, ValueError) as exc:
        print(f"[WARN] timeline not updated: {exc.__class__.__name__}", file=sys.stderr)


MAX_KEPT = 50


def classifications(state: dict) -> dict:
    """Classifications per feature slug (a dict); a state from before 0.7.0 review fixes kept one under `classification`."""
    kept = state.get("classifications")
    kept = dict(kept) if isinstance(kept, dict) else {}
    legacy = state.get("classification")
    if not kept and isinstance(legacy, dict) and legacy.get("feature"):
        kept[str(legacy["feature"])] = legacy
    return kept


def store(state: dict, classification: dict) -> None:
    """Keep one classification per feature. A new classification reopens the feature and drops an earlier waiver."""
    feature = classification.get("feature")
    state["classification"] = classification
    if not feature:
        return
    kept = classifications(state)
    kept.pop(feature, None)
    kept[feature] = classification
    state["classifications"] = dict(list(kept.items())[-MAX_KEPT:])
    gate = state.get("stop_gate") if isinstance(state.get("stop_gate"), dict) else None
    if gate and isinstance(gate.get("waived"), list) and feature in gate["waived"]:
        gate["waived"] = [item for item in gate["waived"] if item != feature]
    if gate and isinstance(gate.get("features"), dict):
        gate["features"].pop(feature, None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a declared complexity against the floor measured from the git diff.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--feature", default="", help="feature slug the classification belongs to")
    parser.add_argument("--declared", required=True, type=str.upper, choices=COMPLEXITY)
    parser.add_argument("--security", type=str.upper, choices=SECURITY, help="declared security risk")
    parser.add_argument("--base", help="git ref to measure against (default: the base recorded for this feature, else the merge base with the default branch, else HEAD)")
    parser.add_argument("--justification", default="", help="why a complexity below the floor is right; recorded in the timeline")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    previous = classifications(load_state(root)).get(args.feature) if opted_in(root) and args.feature else None
    base = args.base
    if not base and isinstance(previous, dict) and previous.get("base"):
        base = str(previous["base"])
    found = measure(root, base)
    floor = found["floor"]
    below = floor is not None and rank(args.declared, COMPLEXITY) < rank(floor, COMPLEXITY)
    justification = args.justification.strip()
    downgraded = below and bool(justification)
    effective = floor if below and not downgraded else args.declared
    if not args.feature and not (below and not downgraded) and rank(effective, COMPLEXITY) >= rank("M", COMPLEXITY):
        print("[ERROR] an M or larger classification needs --feature <slug>, the stem of its spec and tasks.", file=sys.stderr)
        return 2
    security = args.security
    security_below = bool(security) and found["security_floor"] and rank(security, SECURITY) < rank(found["security_floor"], SECURITY)
    if below and not downgraded:
        status, code = "FAIL", 1
        message = f"Declared {args.declared} is below the {describe(found)}. Reclassify, or pass --justification with the reason."
    elif downgraded:
        status, code = "WARN", 0
        message = f"Declared {args.declared} accepted below the {describe(found)}, justified: {justification}"
    elif floor is None:
        status, code = "WARN", 0
        message = f"Declared {args.declared} recorded; {describe(found)}."
    else:
        status, code = "PASS", 0
        message = f"Declared {args.declared} meets the {describe(found)}."
    if security_below:
        message += f" Security {security} is below MEDIUM for a change on an attack surface; assess it (rule 01)."
    classification = {
        "feature": args.feature or None,
        "declared": args.declared,
        "floor": floor,
        "effective": effective,
        "security": security,
        "downgraded": downgraded,
        "justification": redact(justification, 200) if downgraded else "",
        "base": found["base"],
        "at": utc_now(),
    }
    if not args.no_record:
        kind = "CLASSIFICATION_DOWNGRADED" if downgraded else "CLASSIFICATION_RECORDED"
        record(root, args.feature, kind, f"declared {args.declared}, {describe(found)}", status.lower() + (f": {justification}" if downgraded else ""), classification)
    if args.json:
        print(json.dumps({"status": status, "message": message, **classification, "measure": {k: found[k] for k in ("files", "lines", "surfaces", "thresholds") if k in found}}, indent=2, ensure_ascii=False))
    else:
        print(f"[{status}] {message}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
