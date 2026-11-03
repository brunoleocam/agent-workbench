"""Shared helpers for the spec-driven agent system. Stdlib only."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SYSTEM_DIR = Path(__file__).resolve().parents[1]
# Plugin root when run from the plugin; the project's .cursor when run from a project copy.
BASE_DIR = SYSTEM_DIR.parent
MANAGED_MARK = "agent-system-managed"

SECRET_PATH = re.compile(
    r"(^|[\\/])(\.env|.*\.pem|id_rsa|id_ed25519|credentials|secrets?)(\.|$|[\\/])",
    re.IGNORECASE,
)
SECRET_TEXT = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|authorization|bearer)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
AUTH_HEADER = re.compile(r"\bauthorization\s*[:=]\s*(?:[A-Za-z-]+\s+)?[^\s\"']+", re.IGNORECASE)
AUTH_SCHEME = re.compile(r"\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.IGNORECASE)
SECRET_FLAG = re.compile(r"(--?(?:api[_-]?key|secret|token|password|passwd|pwd))(\s+)\S+", re.IGNORECASE)
SECRET_TOKEN = re.compile(r"\b(?:ghp|gho|ghs|github_pat|sk|sk_live|rk_live|xox[abprs]|AKIA|ASIA|glpat)[-_A-Za-z0-9]{12,}\b")
URL_CREDENTIALS = re.compile(r"(\w+://)[^/\s:@]+:[^/\s@]+@")
USER_FLAG = re.compile(r"((?:^|\s)(?:-u|--user)(?:\s+|=)[^\s:]+:)\S+")
BUILTIN_AGENTS = {
    "generalpurpose",
    "explore",
    "cursor-guide",
    "ci-investigator",
    "bugbot",
    "security-review",
    "best-of-n-runner",
    "docs-researcher",
    "agents-memory-updater",
    "supermemory-context-gatherer",
    "shell",
}

SEMANTIC_EVENTS = {
    "PROJECT_INITIALIZED",
    "REQUIREMENT_CREATED",
    "REQUIREMENT_UPDATED",
    "SPEC_CREATED",
    "SPEC_UPDATED",
    "ADR_CREATED",
    "ADR_UPDATED",
    "TASK_CREATED",
    "TASK_STARTED",
    "TASK_BLOCKED",
    "TASK_COMPLETED",
    "CHANGE_REQUEST_CREATED",
    "IMPLEMENTATION_STARTED",
    "IMPLEMENTATION_COMPLETED",
    "FILE_EDIT",
    "TEST_STARTED",
    "TEST_COMPLETED",
    "TEST_FAILED",
    "EVAL_STARTED",
    "EVAL_COMPLETED",
    "REVIEW_STARTED",
    "REVIEW_FAILED",
    "REVIEW_COMPLETED",
    "REWORK_STARTED",
    "REWORK_COMPLETED",
    "CHECKPOINT_CREATED",
    "SESSION_STARTED",
    "SESSION_ENDED",
    "SUBAGENT_STARTED",
    "SUBAGENT_STOPPED",
    "TOOL_FAILURE",
    "SHELL",
    "AGENT_RESPONSE",
    "SPEC_VALIDATION_STARTED",
    "SPEC_VALIDATION_COMPLETED",
    "TASK_VALIDATION_STARTED",
    "TASK_VALIDATION_COMPLETED",
    "PROOF_EXECUTION_STARTED",
    "PROOF_EXECUTION_COMPLETED",
    "VERIFICATION_COMPLETED",
    "SECURITY_REVIEW_STARTED",
    "SECURITY_REVIEW_COMPLETED",
    "LESSON_PROPOSED",
    "LESSON_CONFIRMED",
    "LESSON_REJECTED",
}
VERIFICATION_STEPS = {
    "SPEC_VALIDATION_COMPLETED": "spec",
    "TASK_VALIDATION_COMPLETED": "tasks",
    "PROOF_EXECUTION_COMPLETED": "proofs",
    "VERIFICATION_COMPLETED": "gate",
    "SECURITY_REVIEW_COMPLETED": "security",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def local_stamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def opted_in(root: Path) -> bool:
    return (root / ".cursor" / "agent-system" / "state.json").is_file()


def project_owns_hook(root: Path) -> bool:
    hook = root / ".cursor" / "hooks.json"
    if not hook.is_file():
        return False
    try:
        text = hook.read_text(encoding="utf-8")
    except OSError:
        return False
    return "agent-system/scripts/hook.py" in text.replace("\\", "/")


def workspace_roots(payload: dict) -> list[Path]:
    roots = payload.get("workspace_roots") or []
    if not roots:
        env = os.environ.get("CURSOR_PROJECT_DIR") or os.environ.get("CLAUDE_PROJECT_DIR")
        if env:
            roots = [env]
    found = []
    for raw in roots:
        if raw:
            found.append(Path(raw))
    return found


def redact_secrets(text: str) -> str:
    """Mask secrets and keep the line structure, for captured command output."""
    if not text:
        return ""
    cleaned = AUTH_HEADER.sub("[redacted]", text)
    cleaned = AUTH_SCHEME.sub(r"\1 [redacted]", cleaned)
    cleaned = SECRET_TEXT.sub("[redacted]", cleaned)
    cleaned = SECRET_FLAG.sub(r"\1\2[redacted]", cleaned)
    cleaned = SECRET_TOKEN.sub("[redacted]", cleaned)
    cleaned = USER_FLAG.sub(r"\1[redacted]", cleaned)
    return URL_CREDENTIALS.sub(r"\1[redacted]@", cleaned)


def redact(text: str, limit: int = 160) -> str:
    if not text:
        return ""
    cleaned = redact_secrets(text.replace("\n", " "))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > limit:
        return cleaned[: limit - 1] + "…"
    return cleaned


def safe_files(paths) -> list[str]:
    out = []
    for raw in paths or []:
        if not raw:
            continue
        text = str(raw)
        if SECRET_PATH.search(text):
            out.append("[redacted-path]")
        else:
            out.append(text)
    return out


def state_path(root: Path) -> Path:
    return root / ".cursor" / "agent-system" / "state.json"


def load_state(root: Path) -> dict:
    return read_json(state_path(root), {})


ROADMAP_REL = "docs/progress/ROADMAP.md"
ROADMAP_POSITION = re.compile(r"voc[eê]\s+est[aá]\s+aqui\s*:\s*(.+)", re.IGNORECASE)
ROADMAP_ITEM = re.compile(r"^\s*[-*]\s+\[([xX~ !])\]")


def roadmap_summary(root: Path) -> str:
    """One line with the current position and task counts, or "" without a roadmap."""
    path = root / ROADMAP_REL
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return ""
    position = ""
    counts = {"x": 0, "~": 0, " ": 0, "!": 0}
    for line in lines:
        if not position:
            found = ROADMAP_POSITION.search(line)
            if found:
                position = found.group(1).strip().strip("*_` ")
        item = ROADMAP_ITEM.match(line)
        if item:
            counts[item.group(1).lower()] += 1
    total = sum(counts.values())
    if not position and not total:
        return ""
    parts = [f"{counts['x']}/{total} feitas"]
    if counts["~"]:
        parts.append(f"{counts['~']} em andamento")
    if counts["!"]:
        parts.append(f"{counts['!']} bloqueadas")
    return redact(f"{position or 'posição não marcada'} | {', '.join(parts)}", 200)


def confirmed_lessons(root: Path, limit: int = 5) -> str:
    """Titles of the newest confirmed lessons for session context. Candidates never load."""
    path = root / ".cursor" / "agent-system" / "lessons.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ""
    items = [item for item in (data.get("lessons") or []) if isinstance(item, dict) and item.get("status") == "confirmed"] if isinstance(data, dict) else []
    if not items:
        return ""
    items.sort(key=lambda item: str(item.get("confirmed_at") or ""), reverse=True)
    shown = "; ".join(f"[{item.get('category')}] {redact(str(item.get('title') or ''), 90)}" for item in items[:limit])
    more = f" (+{len(items) - limit} em lessons.py list --status confirmed)" if len(items) > limit else ""
    return f"Lições confirmadas: {shown}{more}"


def save_state(root: Path, state: dict) -> None:
    write_json(state_path(root), state)


def append_event(root: Path, event: dict) -> None:
    path = root / ".cursor" / "timeline" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def should_skip_duplicate_edit(root: Path, file_path: str, window_s: int = 20) -> bool:
    agg_path = root / ".cursor" / "agent-system" / "agg.json"
    now = datetime.now(timezone.utc).timestamp()
    agg = read_json(agg_path, {})
    last = agg.get(file_path)
    if isinstance(last, (int, float)) and now - last < window_s:
        return True
    agg[file_path] = now
    if len(agg) > 200:
        agg = dict(sorted(agg.items(), key=lambda item: item[1])[-100:])
    write_json(agg_path, agg)
    return False


def agent_name(payload: dict, state: dict) -> str:
    explicit = payload.get("subagent_type") or payload.get("agent")
    if explicit:
        return str(explicit)
    active = state.get("active_agent")
    if active:
        return str(active)
    if payload.get("conversation_id") or payload.get("session_id"):
        if state.get("active_agent") == "orchestrator":
            return "orchestrator"
    if state:
        return str(state.get("active_agent") or "unknown")
    return "unknown"


def base_event(payload: dict, state: dict, kind: str, summary: str, result: str = "completed") -> dict:
    return {
        "timestamp": utc_now(),
        "local_time": local_stamp(),
        "session": payload.get("conversation_id") or payload.get("session_id") or state.get("session_id") or "",
        "agent": agent_name(payload, state),
        "event": kind,
        "task": state.get("active_task"),
        "files": [],
        "summary": redact(summary, 240),
        "result": redact(result, 160),
    }


def apply_semantic_state(state: dict, event: dict) -> dict:
    kind = event.get("event")
    task = event.get("task")
    if task:
        state["active_task"] = task
    if kind == "TASK_STARTED":
        state["phase"] = "implementation"
    elif kind == "TASK_BLOCKED":
        blocked = state.setdefault("blocked_tasks", [])
        if task and task not in blocked:
            blocked.append(task)
        state["phase"] = "blocked"
    elif kind == "TASK_COMPLETED":
        done = state.setdefault("completed_tasks", [])
        if task and task not in done:
            done.append(task)
        state["blocked_tasks"] = [item for item in state.get("blocked_tasks", []) if item != task]
        state["pending_tasks"] = [item for item in state.get("pending_tasks", []) if item != task]
    elif kind == "CHANGE_REQUEST_CREATED":
        crs = state.setdefault("open_change_requests", [])
        label = event.get("summary") or task
        if label and label not in crs:
            crs.append(label)
        state["phase"] = "change-management"
    elif kind in {"REVIEW_COMPLETED", "REVIEW_FAILED"}:
        state["review_status"] = event.get("result")
        state["phase"] = "review"
    elif kind == "CHECKPOINT_CREATED":
        state["last_checkpoint"] = event.get("timestamp")
        state["phase"] = "checkpoint"
        if event.get("summary"):
            state["next_step"] = event["summary"]
    elif kind == "SESSION_STARTED":
        if event.get("session"):
            state["session_id"] = event["session"]
    elif kind == "SUBAGENT_STARTED":
        state["active_agent"] = event.get("agent") or state.get("active_agent")
    elif kind == "SUBAGENT_STOPPED":
        state["active_agent"] = "orchestrator"
    step = VERIFICATION_STEPS.get(kind)
    feature = event.get("feature")
    if step and feature:
        verification = state.get("verification")
        if not isinstance(verification, dict):
            verification = {}
        entry = verification.setdefault(str(feature), {})
        entry[step] = event.get("result")
        entry["updated_at"] = event.get("timestamp")
        if len(verification) > 50:
            ordered = sorted(verification.items(), key=lambda item: str(item[1].get("updated_at") or ""))
            verification = dict(ordered[-50:])
        state["verification"] = verification
        if kind == "VERIFICATION_COMPLETED":
            state["phase"] = "verified" if str(event.get("result")).startswith("passed") else "verification"
    return state
