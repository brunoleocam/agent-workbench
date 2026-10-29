"""Cursor command hook. Logs objective events only for opted-in projects.

Fail open: print valid JSON and exit 0. Never log secrets or file contents.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    append_event,
    base_event,
    load_state,
    opted_in,
    project_owns_hook,
    ROADMAP_REL,
    redact,
    roadmap_summary,
    safe_files,
    save_state,
    should_skip_duplicate_edit,
    workspace_roots,
)

TEST_CMD = ("pytest", "npm test", "pnpm test", "yarn test", "dotnet test", "go test", "cargo test", "vitest", "jest")


def emit(payload: dict) -> None:
    # ASCII-only JSON: the reader's encoding (cp1252 or UTF-8 on Windows) cannot garble it.
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))


def read_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def targets(payload: dict) -> list[Path]:
    script = Path(__file__).resolve()
    found = []
    for root in workspace_roots(payload):
        if not opted_in(root):
            continue
        project_script = (root / ".cursor" / "agent-system" / "scripts" / "hook.py").resolve()
        if project_owns_hook(root) and script != project_script:
            continue
        found.append(root)
    return found


def log(root: Path, payload: dict, kind: str, summary: str, result: str = "completed", files=None) -> None:
    state = load_state(root)
    event = base_event(payload, state, kind, summary, result)
    event["files"] = safe_files(files or [])
    append_event(root, event)
    if kind == "SUBAGENT_STARTED":
        state["active_agent"] = event["agent"]
        save_state(root, state)
    elif kind == "SUBAGENT_STOPPED":
        state["active_agent"] = "orchestrator"
        save_state(root, state)
    elif kind == "SESSION_STARTED" and event.get("session"):
        state["session_id"] = event["session"]
        save_state(root, state)


def test_result(command: str, output: str) -> tuple[str, str] | None:
    lowered = command.lower()
    if not any(token in lowered for token in TEST_CMD):
        return None
    text = output or ""
    failed = bool(re_failed(text))
    kind = "TEST_FAILED" if failed else "TEST_COMPLETED"
    return kind, redact(text, 120) or ("failed" if failed else "completed")


def re_failed(text: str) -> bool:
    lowered = text.lower()
    if "0 failed" in lowered or "failed=0" in lowered:
        return False
    return "failed" in lowered or "error:" in lowered


def handle(payload: dict) -> dict:
    name = str(payload.get("hook_event_name") or "")
    roots = targets(payload)

    if name == "workspaceOpen":
        return {}

    if name == "subagentStart":
        for root in roots:
            log(
                root,
                payload,
                "SUBAGENT_STARTED",
                payload.get("task") or payload.get("subagent_type") or "subagent started",
            )
        return {"permission": "allow"}

    if name == "subagentStop":
        for root in roots:
            files = payload.get("modified_files") or []
            log(
                root,
                payload,
                "SUBAGENT_STOPPED",
                payload.get("summary") or payload.get("status") or "subagent stopped",
                result=str(payload.get("status") or "completed"),
                files=files,
            )
        return {}

    if name == "sessionStart":
        context = ""
        for root in roots:
            log(root, payload, "SESSION_STARTED", "Session started")
            state = load_state(root)
            task = state.get("active_task") or "none"
            nxt = state.get("next_step") or "Classify the request."
            context = f"Agent system state: task={task}; phase={state.get('phase')}; next={nxt}"
            roadmap = roadmap_summary(root)
            if roadmap:
                context += f". Roadmap ({ROADMAP_REL}): {roadmap}. Atualize a linha da tarefa ao mudar o status."
        if context:
            return {"additional_context": redact(context, 500)}
        return {}

    if name == "sessionEnd":
        for root in roots:
            log(root, payload, "SESSION_ENDED", "Session ended", result=str(payload.get("reason") or "completed"))
        return {}

    if name == "afterFileEdit":
        path = str(payload.get("file_path") or "")
        for root in roots:
            if path and should_skip_duplicate_edit(root, path):
                continue
            log(root, payload, "FILE_EDIT", f"Edited {Path(path).name}" if path else "Edited a file", files=[path])
        return {}

    if name == "postToolUseFailure":
        for root in roots:
            log(
                root,
                payload,
                "TOOL_FAILURE",
                f"{payload.get('tool_name') or 'tool'} failed",
                result=str(payload.get("failure_type") or "error"),
            )
        return {}

    if name == "afterShellExecution":
        command = str(payload.get("command") or "")
        output = str(payload.get("output") or "")
        classified = test_result(command, output)
        if classified:
            kind, result = classified
            for root in roots:
                log(root, payload, kind, redact(command, 120), result=result)
        return {}

    if name == "afterAgentResponse":
        text = str(payload.get("text") or "")
        for root in roots:
            log(root, payload, "AGENT_RESPONSE", f"Agent response ({len(text)} chars)")
        return {}

    if name == "stop":
        return {}

    return {}


def main() -> int:
    payload = read_input()
    try:
        emit(handle(payload))
    except Exception:
        name = str(payload.get("hook_event_name") or "")
        if name == "subagentStart":
            emit({"permission": "allow"})
        else:
            emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
