"""Command hook for Cursor and Claude Code. Logs objective events only for opted-in projects.

Cursor sends camelCase events (sessionStart); Claude Code sends PascalCase events (SessionStart)
with a different payload. Claude payloads are translated to the Cursor shape, handled once,
and the reply is translated back.

Fail open: print valid JSON and exit 0. Never log secrets or file contents.
"""

from __future__ import annotations

import json
import os
import re
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
    lint = reply.get("design_lint")
    if event == "PostToolUse" and lint:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": redact(lint, 1500)}}
    return {}


def is_claude(payload: dict) -> bool:
    name = str(payload.get("hook_event_name") or "")
    return bool(name) and name[0].isupper()


LINT_SHOWN = 8  # findings passed to the agent; the rest is a count


def design_lint(path: str, roots: list[Path]) -> str:
    """Informational lint summary for one edited UI file. Empty when clean, not a UI file, or on any error."""
    try:
        import lint_design

        file = Path(path)
        if file.suffix.lower() not in lint_design.EXTENSIONS or not file.is_file():
            return ""
        resolved = file.resolve()
        root = next((item for item in roots if item.resolve() in resolved.parents), None)
        if root is None:  # outside every workspace root: not this project's UI
            return ""
        design, tokens = root / "DESIGN.md", root / "design" / "tokens.css"
        findings = lint_design.lint_paths([file], design if design.is_file() else None, tokens if tokens.is_file() else None)
    except Exception:
        return ""
    if not findings:
        return ""
    counts = lint_design.summary(findings)
    lines = [f"Design lint (informational) for {file.name}: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2. P0 blocks review."]
    lines += [f"line {item.line}: {item.rule} {item.message} Fix: {item.suggestion}" for item in findings[:LINT_SHOWN]]
    if len(findings) > LINT_SHOWN:
        lines.append(f"{len(findings) - LINT_SHOWN} more; run lint_design.py {file.name} for the full list.")
    return "\n".join(lines)


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


# Summary lines of common runners. A bare "error:" or "failed" in a log line is not a failure: a passing run can print both.
FAIL_COUNT = re.compile(r"\b(\d+)\s+(?:failed|failures?|errors?)\b|\b(?:failed|failures|errors)\s*[=:]\s*(\d+)\b", re.IGNORECASE)
FAIL_LINE = re.compile(
    r"^\s*(?:\[(?:INFO|ERROR)\]\s*)?(?:FAIL(?:ED)?\b|--- FAIL\b|not ok\b|\[FAIL\]|(?:BUILD\s+)?FAILURE\b|BUILD FAILED\b|Test Run Failed|npm ERR! (?:Test failed|code ELIFECYCLE))",
    re.MULTILINE,
)


def re_failed(text: str) -> bool:
    for found in FAIL_COUNT.finditer(text):
        if int(found.group(1) or found.group(2)) > 0:
            return True
    return bool(FAIL_LINE.search(text))


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
                context += f". Roadmap ({ROADMAP_REL}): {roadmap}. Update the task line when its status changes."
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
        report = design_lint(path, workspace_roots(payload)) if path else ""
        if report:
            for root in roots:
                log(root, payload, "DESIGN_LINT", report.splitlines()[0], result="warning", files=[path])
            return {"design_lint": report}
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
            reply = handle(payload)
            reply.pop("design_lint", None)  # Cursor's afterFileEdit has no channel back to the agent
            emit(reply)
    except Exception:
        if name == "subagentStart":
            emit({"permission": "allow"})
        else:
            emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
