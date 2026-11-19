"""Deterministic floor for the request classification, measured from the git diff.

The model declares the complexity; this script measures the change (files, lines, attack surfaces) against a git base
and refuses a declaration below the floor unless a justification is recorded. Exit codes: 0 accepted (also a justified
downgrade or an unknown floor), 1 declared below the floor, 2 bad argument.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import ConfigError, _excluded, harness_doc_dirs, load_layout, resolve_layout  # noqa: E402
from lib import append_event, apply_semantic_state, load_state, local_stamp, opted_in, redact, save_state, utc_now  # noqa: E402

COMPLEXITY = ("XS", "S", "M", "L", "XL")
SECURITY = ("NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL")
DEFAULTS = {"m_files": 6, "m_lines": 300, "s_files": 2, "s_lines": 20}
# Same name heuristics as init_project.scan_signals, applied to each changed path. A hint, not a verdict.
SURFACE_RULES = {
    "authentication": ("auth", "login", "jwt", "oauth", "password"),
    "file_upload": ("upload", "multer", "attachment"),
    "payments": ("payment", "stripe", "checkout", "billing", "invoice"),
    "cryptography": ("crypto", "encrypt", "cipher"),
    "multi_tenant": ("tenant",),
    "secrets_config": (".env.example", "secrets", "vault"),
}
SURFACE_DIRS = {"api": {"api", "controllers", "routes"}, "database": {"migrations", "prisma"}}
INFRA_NAMES = {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}


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


def surfaces_of(relative: str, listed: dict[str, set[str]]) -> set[str]:
    lowered = relative.lower()
    parts = lowered.split("/")
    found = {name for name, paths in listed.items() if relative in paths}
    found |= {name for name, tokens in SURFACE_RULES.items() if any(token in lowered for token in tokens)}
    found |= {name for name, dirs in SURFACE_DIRS.items() if any(part in dirs for part in parts[:-1])}
    if lowered.endswith(".sql"):
        found.add("database")
    if parts[-1] in INFRA_NAMES or lowered.endswith(".tf") or lowered.startswith(".github/workflows/"):
        found.add("infrastructure")
    return found


def thresholds(layout: dict) -> dict:
    overrides = layout.get("overrides") if isinstance(layout.get("overrides"), dict) else {}
    custom = overrides.get("classification_floor") if isinstance(overrides.get("classification_floor"), dict) else {}
    return {key: custom[key] if isinstance(custom.get(key), int) and not isinstance(custom.get(key), bool) and custom[key] > 0 else value
            for key, value in DEFAULTS.items()}


def measure(root: Path, base: str | None = None) -> dict:
    """Files, lines and surfaces changed against `base` (default HEAD), plus untracked files. floor None without git."""
    root = root.resolve()
    if (git(root, ["rev-parse", "--is-inside-work-tree"]) or "").strip() != "true":
        return {"floor": None, "security_floor": None, "files": [], "lines": 0, "surfaces": {}, "base": None, "reason": "not a git repository"}
    base = base or head(root)
    try:
        raw = load_layout(root)
        layout = resolve_layout(root, raw)
    except ConfigError as exc:
        return {"floor": None, "security_floor": None, "files": [], "lines": 0, "surfaces": {}, "base": base, "reason": str(exc)}
    doc_dirs = harness_doc_dirs(layout)
    lines: dict[str, int] = {}
    if base:
        numstat = git(root, ["diff", "--numstat", "-z", base, "--", "."])
        if numstat is None:
            return {"floor": None, "security_floor": None, "files": [], "lines": 0, "surfaces": {}, "base": base, "reason": f"unknown base {base}"}
        for record in numstat.split("\0"):
            fields = record.split("\t")
            if len(fields) == 3 and fields[2]:
                added, removed = fields[0], fields[1]
                lines[fields[2]] = (int(added) if added.isdigit() else 1) + (int(removed) if removed.isdigit() else 0)
    others = git(root, ["ls-files", "--others", "--exclude-standard", "-z", "--", "."]) or ""
    for relative in filter(None, others.split("\0")):
        try:
            lines[relative] = max(1, len((root / relative).read_bytes().splitlines()))
        except OSError:
            lines[relative] = 1
    counted = {path.replace("\\", "/"): count for path, count in lines.items() if not _excluded(path.replace("\\", "/"), doc_dirs)}
    signals = raw.get("signals") if isinstance(raw.get("signals"), dict) else {}
    listed_raw = signals.get("attack_surfaces") if isinstance(signals.get("attack_surfaces"), dict) else {}
    listed = {str(name): {str(item) for item in items} for name, items in listed_raw.items() if isinstance(items, list)}
    surfaces: dict[str, list[str]] = {}
    for relative in sorted(counted):
        for name in sorted(surfaces_of(relative, listed)):
            surfaces.setdefault(name, []).append(relative)
    limits = thresholds(raw)
    total = sum(counted.values())
    if len(counted) >= limits["m_files"] or total >= limits["m_lines"] or surfaces:
        floor = "M"
    elif len(counted) >= limits["s_files"] or total >= limits["s_lines"]:
        floor = "S"
    else:
        floor = "XS"
    return {
        "floor": floor,
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
        state["classification"] = classification
        save_state(root, state)
    except (OSError, ValueError) as exc:
        print(f"[WARN] timeline not updated: {exc.__class__.__name__}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check a declared complexity against the floor measured from the git diff.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--feature", default="", help="feature slug the classification belongs to")
    parser.add_argument("--declared", required=True, type=str.upper, choices=COMPLEXITY)
    parser.add_argument("--security", type=str.upper, choices=SECURITY, help="declared security risk")
    parser.add_argument("--base", help="git ref to measure against (default: the base recorded for this feature, else HEAD)")
    parser.add_argument("--justification", default="", help="why a complexity below the floor is right; recorded in the timeline")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    previous = load_state(root).get("classification") if opted_in(root) else None
    base = args.base
    if not base and isinstance(previous, dict) and previous.get("feature") == args.feature and previous.get("base"):
        base = str(previous["base"])
    found = measure(root, base)
    floor = found["floor"]
    below = floor is not None and rank(args.declared, COMPLEXITY) < rank(floor, COMPLEXITY)
    justification = args.justification.strip()
    downgraded = below and bool(justification)
    effective = floor if below and not downgraded else args.declared
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
