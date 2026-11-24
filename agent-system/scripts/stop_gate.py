"""Goal loop for the Claude Code main session: an M+ feature may stop only when validate_verification.py exits 0.

Called by hook.py on the Claude Code `Stop` event. It blocks with the gate failures as the reason, and stops
blocking (escalating to the user) at `limits.max_revisions` blocks, at the feature's cost budget, or when a continued
stop arrives with no change to the code or to the gate's documents (spec, tasks, review, proofs) since the previous block. `AGENT_WORKBENCH_STOP_GATE=off` or a
`STOP_GATE_WAIVED` event turns it off. Any error lets the session stop: the hook fails open.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import classify_floor  # noqa: E402
import workflow  # noqa: E402
from artifacts import load_layout, proofs_file, record, resolve_layout, workspace_fingerprint  # noqa: E402
from lib import load_state, read_json, save_state, timeline_dir  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
ENV_SWITCH = "AGENT_WORKBENCH_STOP_GATE"
DEFAULT_BUDGET_USD = 25.0
# US$ per million tokens; defaults are Claude Opus 5.5 list rates. Override in layout.json overrides.stop_gate.prices.
DEFAULT_PRICES = {"input": 4.0, "output": 20.0, "cache_read": 0.2, "cache_creation": 5.0}
USAGE_FIELDS = {"input_tokens": "input", "output_tokens": "output", "cache_read_input_tokens": "cache_read", "cache_creation_input_tokens": "cache_creation"}
TRANSCRIPT_MAX_BYTES = 50 * 1024 * 1024
GATE_TIMEOUT = 15
SHOWN_FAILURES = 6
MAX_OPEN = 1  # open features checked per stop (the most recent); one gate run fits the hook timeout


def parse_time(value) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def settings(root: Path) -> dict:
    try:
        overrides = load_layout(root).get("overrides") or {}
    except Exception:
        overrides = {}
    custom = overrides.get("stop_gate") if isinstance(overrides, dict) and isinstance(overrides.get("stop_gate"), dict) else {}
    budget = custom.get("max_usd_per_feature")
    prices = dict(DEFAULT_PRICES)
    if isinstance(custom.get("prices"), dict):
        prices.update({key: float(value) for key, value in custom["prices"].items() if key in prices and isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0})
    try:
        limit = workflow.max_revisions(workflow.load(workflow.default_path()))
    except workflow.WorkflowError:
        limit = 3
    return {
        "budget": float(budget) if isinstance(budget, (int, float)) and not isinstance(budget, bool) and budget > 0 else DEFAULT_BUDGET_USD,
        "prices": prices,
        "max_blocks": limit,
    }


def transcript_usage(raw_path: str, since: datetime | None) -> dict:
    """Token totals of a Claude Code transcript (last usage per message id), counting messages at or after `since`."""
    totals = dict.fromkeys(USAGE_FIELDS.values(), 0)
    try:
        path = Path(os.path.expanduser(raw_path))
        if path.suffix != ".jsonl" or not path.is_file() or path.stat().st_size > TRANSCRIPT_MAX_BYTES:
            return totals
        by_message: dict[str, dict] = {}
        with path.open(encoding="utf-8", errors="replace") as handle:
            for index, line in enumerate(handle):
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                message = entry.get("message") if isinstance(entry, dict) else None
                usage = message.get("usage") if isinstance(message, dict) else None
                if not isinstance(usage, dict):
                    continue
                stamp = parse_time(entry.get("timestamp")) if entry.get("timestamp") else None
                if since and stamp and stamp < since:
                    continue
                key = str(message.get("id") or f"line-{index}")
                by_message[key] = {name: int(usage[field]) for field, name in USAGE_FIELDS.items() if isinstance(usage.get(field), int) and not isinstance(usage.get(field), bool)}
        for usage in by_message.values():
            for name, value in usage.items():
                totals[name] += value
    except (OSError, ValueError):
        pass
    return totals


def subagent_usage(root: Path, since: datetime | None) -> dict:
    totals = dict.fromkeys(USAGE_FIELDS.values(), 0)
    path = timeline_dir(root) / "events.jsonl"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []
    except OSError:
        return totals
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("event") != "SUBAGENT_STOPPED" or not isinstance(event.get("tokens"), dict):
            continue
        stamp = parse_time(event.get("timestamp"))
        if since and stamp and stamp < since:
            continue
        for name in totals:
            value = event["tokens"].get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                totals[name] += value
    return totals


def cost_usd(tokens: dict, prices: dict) -> float:
    return sum(tokens.get(name, 0) * prices[name] for name in prices) / 1_000_000


def run_gate(root: Path, feature: str) -> tuple[int | None, list[str]]:
    """Exit code and FAIL messages of the gate; None when it could not run in time (the caller fails open)."""
    try:
        done = subprocess.run(
            [sys.executable, "-I", str(SCRIPTS / "validate_verification.py"), "--root", str(root), "--feature", feature, "--json", "--no-record"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GATE_TIMEOUT, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, []
    try:
        data = json.loads(done.stdout or "{}")
    except json.JSONDecodeError:
        data = {}
    if done.returncode == 2:
        return 2, [str(data.get("error") or (done.stderr or "configuration error").strip()[:200])]
    items = data.get("results") if isinstance(data.get("results"), list) else []
    fails = [str(item.get("message")) for item in items if isinstance(item, dict) and item.get("level") == "FAIL"]
    return done.returncode, fails


def artifact_digest(root: Path, feature: str) -> str:
    """Digest of the documents the gate reads for a feature: spec, tasks, review, security assessment, and proofs.

    The workspace fingerprint leaves these out on purpose (a review must not invalidate itself), so on its own it
    cannot tell that the agent is writing them. Without this, an agent that is producing the spec, tasks or review
    after the code is reported as making no progress."""
    digest = hashlib.sha256()
    try:
        layout = resolve_layout(root)
        paths = [root / layout[key] / f"{feature}.md" for key in ("specs_dir", "tasks_dir", "reviews_dir", "security_dir") if layout.get(key)]
        paths.append(proofs_file(root, feature))
    except Exception:
        return ""
    for path in paths:
        try:
            digest.update(path.name.encode() + b"\x00" + path.read_bytes() if path.is_file() else b"-")
        except OSError:
            digest.update(b"?")
    return digest.hexdigest()


def gate_state(state: dict) -> dict:
    value = state.get("stop_gate")
    value = value if isinstance(value, dict) else {}
    value.setdefault("waived", [])
    if not isinstance(value.get("features"), dict):
        value["features"] = {}
    return value


def escalate(root: Path, state: dict, gate: dict, feature: str, entry: dict, fingerprint: str, reason: str, text: str) -> dict:
    """Tell the user once per workspace state and let the session stop."""
    key = fingerprint if reason == "no_progress" else reason
    first = entry.get("escalated") != key and not (reason != "no_progress" and reason in entry.get("escalated_reasons", []))
    entry["escalated"] = key
    if reason != "no_progress":
        entry["escalated_reasons"] = sorted(set(entry.get("escalated_reasons", [])) | {reason})
    state["stop_gate"] = gate
    save_state(root, state)
    if not first:
        return {}
    record(root, "STOP_GATE_ESCALATED", f"stop gate escalated for {feature}", reason, feature, "orchestrator")
    return {"systemMessage": text}


def has_artifacts(root: Path, feature: str) -> bool:
    """The feature's spec and tasks exist in this checkout (a feature from another branch has none here)."""
    try:
        layout = resolve_layout(root)
    except Exception:
        return True
    return (root / layout["specs_dir"] / f"{feature}.md").is_file() and (root / layout["tasks_dir"] / f"{feature}.md").is_file()


def open_features(root: Path, state: dict, gate: dict) -> list[tuple[str, dict]]:
    """Classified M+ features to gate on this stop, most recent first, at most MAX_OPEN.

    Skipped: closed (gate passed), waived, already escalated at a limit, and features whose spec and tasks are not in
    this checkout once they were asked about. So a dead or exhausted newer feature never shadows an older one.
    """
    found = []
    for feature, item in reversed(list(classify_floor.classifications(state).items())):
        if not isinstance(item, dict) or item.get("closed") or feature in gate["waived"]:
            continue
        if classify_floor.rank(str(item.get("effective") or ""), classify_floor.COMPLEXITY) < classify_floor.rank("M", classify_floor.COMPLEXITY):
            continue
        entry = gate["features"].get(feature) or {}
        if entry.get("escalated_reasons"):
            continue
        if not has_artifacts(root, feature) and entry.get("blocks"):
            continue
        found.append((feature, item))
        if len(found) >= MAX_OPEN:
            break
    return found  # each gate run costs up to GATE_TIMEOUT inside the hook's 20 s


def unclassified(root: Path, state: dict, gate: dict, fingerprint: str) -> dict:
    """Ask once per workspace state for a classification when the work since its base has an M+ floor that no
    classification recorded for that base (open, closed, or waived) reaches: an early XS does not cover a grown change."""
    base = classify_floor.default_base(root)
    found = classify_floor.measure(root, base)
    if found["floor"] is None or classify_floor.rank(found["floor"], classify_floor.COMPLEXITY) < classify_floor.rank("M", classify_floor.COMPLEXITY):
        return {}
    floor = classify_floor.rank(found["floor"], classify_floor.COMPLEXITY)
    for item in classify_floor.classifications(state).values():
        if isinstance(item, dict) and item.get("base") == found["base"] and (
                classify_floor.rank(str(item.get("effective") or ""), classify_floor.COMPLEXITY) >= floor
                or (item.get("downgraded") and classify_floor.rank(str(item.get("floor") or ""), classify_floor.COMPLEXITY) >= floor)):
            return {}
    if gate.get("unclassified_fp") == fingerprint:
        return {}  # asked once for this workspace state
    gate["unclassified_fp"] = fingerprint
    state["stop_gate"] = gate
    save_state(root, state)
    record(root, "STOP_GATE_BLOCKED", "stop blocked: unclassified change", classify_floor.describe(found), None, "orchestrator")
    return {"decision": "block", "reason": (
        f"Agent Workbench: this change has a {classify_floor.describe(found)} and no open classification. "
        "Run `python .agent-system/scripts/classify_floor.py --feature <slug> --declared <XS|S|M|L|XL>` before finishing. "
        "If you are waiting for the user's decision, say so and stop."
    )}


def decide(root: Path, payload: dict) -> dict:
    """Claude Code reply for a Stop event: {} to let it stop, a block, or a message for the user.

    It blocks at most once per workspace state: a second stop with nothing changed escalates (once) and stops.
    """
    if os.environ.get(ENV_SWITCH, "").strip().lower() in {"off", "0", "false", "no"}:
        return {}
    state = load_state(root)
    gate = gate_state(state)
    fingerprint = workspace_fingerprint(root)["digest"]
    candidates = open_features(root, state, gate)
    if not candidates:
        return unclassified(root, state, gate, fingerprint)

    failing = None
    changed = False
    for feature, item in candidates:
        code, fails = run_gate(root, feature)
        if code is None:
            return {}  # the gate could not run in time: fail open, change nothing
        if code == 0:
            kept = classify_floor.classifications(state)
            kept[feature] = {**item, "closed": True}
            state["classifications"] = kept
            gate["features"].pop(feature, None)
            changed = True
            continue
        if failing is None:
            failing = (feature, item, code, fails)
    if failing is None:
        if changed:
            state["stop_gate"] = gate
            save_state(root, state)
        return {}

    feature, item, code, fails = failing
    entry = gate["features"].setdefault(feature, {"blocks": 0})
    config = settings(root)
    waive = (f"`python .agent-system/scripts/record_event.py --event STOP_GATE_WAIVED --feature {feature} --summary \"<the user's words>\"`"
             " (only when the user says so)")
    progress = f"{fingerprint}:{artifact_digest(root, feature)}"
    if entry.get("last_fp") == progress:
        return escalate(root, state, gate, feature, entry, progress, "no_progress",
                        f"Agent Workbench: {feature} stopped again without passing the gate and without changing the code since the last reminder. "
                        f"Decide: continue, replan, or waive with {waive}.")
    if entry.get("blocks", 0) >= config["max_blocks"] or "max_blocks" in entry.get("escalated_reasons", []):
        return escalate(root, state, gate, feature, entry, progress, "max_blocks",
                        f"Agent Workbench: the stop gate held {feature} {entry['blocks']} times (limit {config['max_blocks']}) and the gate still fails. "
                        f"Decide: continue fixing, replan, or waive with {waive}.")
    since = parse_time(item.get("at"))
    tokens = transcript_usage(str(payload.get("transcript_path") or ""), since)
    for name, value in subagent_usage(root, since).items():
        tokens[name] += value
    spent = cost_usd(tokens, config["prices"])
    if spent >= config["budget"]:
        return escalate(root, state, gate, feature, entry, progress, "budget",
                        f"Agent Workbench: {feature} reached its estimated cost budget (US$ {spent:.2f} of {config['budget']:.2f}) and the gate still fails. "
                        f"Decide: raise the budget (layout.json overrides.stop_gate.max_usd_per_feature), replan, or waive with {waive}.")

    entry["blocks"] = int(entry.get("blocks", 0)) + 1
    entry["last_fp"] = progress
    state["stop_gate"] = gate
    save_state(root, state)
    record(root, "STOP_GATE_BLOCKED", f"stop blocked for {feature}", f"block {entry['blocks']}/{config['max_blocks']}, US$ {spent:.2f}", feature, "orchestrator")
    shown = "; ".join(fails[:SHOWN_FAILURES]) + (f"; and {len(fails) - SHOWN_FAILURES} more" if len(fails) > SHOWN_FAILURES else "")
    what = "has no valid spec or tasks for the gate" if code == 2 else "does not pass the gate"
    return {"decision": "block", "reason": (
        f"Agent Workbench: {feature} is {item.get('effective')} and {what}: `python .agent-system/scripts/validate_verification.py --feature {feature}` "
        f"({shown or 'see its output'}). Keep working until it exits 0 "
        f"(attempt {entry['blocks']} of {config['max_blocks']}). If you are waiting for the user's decision (spec, ADR, or risk approval), say so and stop."
    )}
