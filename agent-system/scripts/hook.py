"""Command hook for Cursor and Claude Code. Logs objective events only for opted-in projects.

Cursor sends camelCase events (sessionStart); Claude Code sends PascalCase events (SessionStart)
with a different payload. Claude payloads are translated to the Cursor shape, handled once,
and the reply is translated back.

Fail open: print valid JSON and exit 0. Never log secrets or file contents.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    append_event,
    base_event,
    confirmed_lessons,
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

TEST_CMD = (
    "pytest", "unittest", "npm test", "npm run test", "pnpm test", "yarn test", "bun test", "dotnet test", "go test",
    "cargo test", "vitest", "jest", "phpunit", "pest", "mvn test", "mvn verify", "gradle test", "gradlew test", "rspec",
)
# check_proofs.py records the real exit code itself; counting it here too would duplicate the result.
DETERMINISTIC_CMD = ("check_proofs.py", "validate_verification.py")


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


CLAUDE_FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [value.get(key) for key in ("stdout", "stderr", "output", "error")]
        return "\n".join(str(part) for part in parts if part)
    return str(value)


def from_claude(payload: dict) -> dict:
    """Cursor-shaped copy of a Claude Code hook payload. Unknown events map to an empty name."""
    name = str(payload.get("hook_event_name") or "")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ""
    out = {
        "host": "claude",
        "workspace_roots": [root] if root else [],
        "session_id": payload.get("session_id") or "",
    }
    if payload.get("agent_type"):
        out["subagent_type"] = payload["agent_type"]
    tool_input = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    if name == "SessionStart":
        out["hook_event_name"] = "sessionStart"
    elif name == "SessionEnd":
        out["hook_event_name"] = "sessionEnd"
        out["reason"] = payload.get("reason") or "completed"
    elif name == "SubagentStart":
        out["hook_event_name"] = "subagentStart"
        out["task"] = f"{payload.get('agent_type') or 'subagent'} started"
    elif name == "SubagentStop":
        out["hook_event_name"] = "subagentStop"
        # The subagent's last message can hold anything; log only who stopped.
        out["summary"] = f"{payload.get('agent_type') or 'subagent'} stopped"
    elif name == "PostToolUse" and payload.get("tool_name") in CLAUDE_FILE_TOOLS:
        out["hook_event_name"] = "afterFileEdit"
        out["file_path"] = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    elif name == "PostToolUse" and payload.get("tool_name") == "Bash":
        out["hook_event_name"] = "afterShellExecution"
        out["command"] = tool_input.get("command") or ""
        out["output"] = _text(payload.get("tool_response"))
    elif name == "PostToolUseFailure":
        out["hook_event_name"] = "postToolUseFailure"
        out["tool_name"] = payload.get("tool_name") or "tool"
        out["failure_type"] = "error"
    elif name == "Stop":
        out["hook_event_name"] = "afterAgentResponse"
        out["text"] = _text(payload.get("last_assistant_message"))
    else:
        out["hook_event_name"] = ""
    return out


def to_claude(event: str, reply: dict) -> dict:
    """Claude Code reply for a Cursor-shaped result. Only SessionStart carries data back."""
    context = reply.get("additional_context")
    if event == "SessionStart" and context:
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    return {}


def is_claude(payload: dict) -> bool:
    name = str(payload.get("hook_event_name") or "")
    return bool(name) and name[0].isupper()


def targets(payload: dict) -> list[Path]:
    script = Path(__file__).resolve()
    found = []
    for root in workspace_roots(payload):
        if not opted_in(root):
            continue
        project_script = (root / ".cursor" / "agent-system" / "scripts" / "hook.py").resolve()
        # .cursor/hooks.json only routes Cursor events; under Claude Code the plugin hook is the only one.
        if payload.get("host") != "claude" and project_owns_hook(root) and script != project_script:
            continue
        found.append(root)
    return found


def log(root: Path, payload: dict, kind: str, summary: str, result: str = "completed", files=None, inferred: bool = False) -> None:
    state = load_state(root)
    event = base_event(payload, state, kind, summary, result)
    event["files"] = safe_files(files or [])
    if inferred:
        event["inferred"] = True
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
    if any(token in lowered for token in DETERMINISTIC_CMD):
        return None
    if not any(token in lowered for token in TEST_CMD):
        return None
    text = output or ""
    failed = bool(re_failed(text))
    kind = "TEST_FAILED" if failed else "TEST_COMPLETED"
    return kind, "inferred from output: " + (redact(text, 100) or ("failed" if failed else "no failure text"))


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
            lessons = confirmed_lessons(root)
            if lessons:
                context += f". {lessons}"
        if context:
            return {"additional_context": redact(context, 900)}
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
                log(root, payload, kind, redact(command, 120), result=result, inferred=True)
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
    name = str(payload.get("hook_event_name") or "")
    try:
        if is_claude(payload):
            emit(to_claude(name, handle(from_claude(payload))))
        else:
            emit(handle(payload))
    except Exception:
        if name == "subagentStart":
            emit({"permission": "allow"})
        else:
            emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
