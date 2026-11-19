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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import (  # noqa: E402
    DESIGN_REL,
    contract_path,
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
    system_dir,
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
PLUGIN_PREFIX = "agent-workbench:"
SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
# Claude Code's own commands that share a name with a plugin skill; only the prefixed form is the plugin's.
CLAUDE_BUILTINS = {"help", "security-review", "init", "review", "status", "agents", "hooks", "memory", "config", "context"}
SKILL_REPEAT_S = 60
SLASH = re.compile(r"\s*/([A-Za-z0-9][A-Za-z0-9:_-]{0,80})(?:\s|$)")


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
        if payload.get("agent_transcript_path"):
            out["agent_transcript_path"] = str(payload["agent_transcript_path"])
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
    elif name == "PostToolUse" and payload.get("tool_name") == "Skill":
        out["hook_event_name"] = "skillUsed"
        out["skill"] = skill_name(tool_input.get("skill"))
    elif name == "UserPromptSubmit":
        out["hook_event_name"] = "skillUsed"
        out["skill"] = slash_skill(payload.get("prompt"))
        out["source"] = "slash"
    elif name == "Stop":
        out["hook_event_name"] = "afterAgentResponse"
        out["text"] = _text(payload.get("last_assistant_message"))
        out["stop"] = True
        out["stop_hook_active"] = bool(payload.get("stop_hook_active"))
        out["transcript_path"] = str(payload.get("transcript_path") or "")
    else:
        out["hook_event_name"] = ""
    return out


def skill_name(value) -> str:
    """Bare skill name ("agent-workbench:tdd" -> "tdd"); empty when it does not look like a skill name."""
    name = str(value or "").strip().lstrip("/")
    name = name.split(":", 1)[1] if name.startswith(PLUGIN_PREFIX) else name
    return name if SKILL_NAME.fullmatch(name) else ""


def known_skills() -> set[str]:
    folders = [Path(__file__).resolve().parents[2] / "skills"]
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        folders.append(Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "skills")
    names: set[str] = set()
    for folder in folders:
        if folder.is_dir():
            names.update(path.parent.name for path in folder.glob("*/SKILL.md"))
    return names


def slash_skill(prompt) -> str:
    """The plugin skill a typed slash command names, or empty. Only the name leaves this function, never the prompt."""
    found = SLASH.match(str(prompt or ""))
    if not found:
        return ""
    typed = found.group(1)
    name = skill_name(typed)
    if name in CLAUDE_BUILTINS and not typed.startswith(PLUGIN_PREFIX):
        return ""  # a bare /help or /security-review runs Claude Code's own command, not the plugin skill
    return name if name in known_skills() else ""


def to_claude(event: str, reply: dict) -> dict:
    """Claude Code reply for a Cursor-shaped result: SessionStart context, PostToolUse lint, and the Stop gate."""
    if event == "Stop":
        return reply.get("stop_gate") or {}
    context = reply.get("additional_context")
    if event == "SessionStart" and context:
        return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}
    lint = "\n".join(item for item in (reply.get("design_lint"), reply.get("infra_lint")) if item)
    if event == "PostToolUse" and lint:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": redact(lint, 3000)}}
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
        design, tokens = contract_path(root, DESIGN_REL), root / "design" / "tokens.css"
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


def infra_lint(path: str, roots: list[Path]) -> str:
    """Informational lint summary for one edited Dockerfile, Compose file, or manifest. Empty when clean or on any error.

    A P0-SECRET-LITERAL finding names the key only, so the summary never carries a secret value.
    """
    try:
        import lint_infra

        file = Path(path)
        if not file.is_file() or not lint_infra.is_candidate(file):
            return ""
        resolved = file.resolve()
        if not any(item.resolve() in resolved.parents for item in roots):  # outside every workspace root
            return ""
        findings = lint_infra.by_severity(lint_infra.lint_paths([file], max_bytes=lint_infra.HOOK_MAX_BYTES))
    except Exception:
        return ""
    if not findings:
        return ""
    counts = lint_infra.summary(findings)
    lines = [f"Infra lint (informational) for {file.name}: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2. P0 blocks review."]
    # Most severe first, and only P0 lines carry the fix, so the P0s survive the context limit.
    lines += [
        f"line {item.line}: {item.rule} {item.message}" + (f" Fix: {item.suggestion}" if item.severity == "P0" else "")
        for item in findings[:LINT_SHOWN]
    ]
    if len(findings) > LINT_SHOWN:
        lines.append(f"{len(findings) - LINT_SHOWN} more; run lint_infra.py {file.name} for the full list.")
    return "\n".join(lines)


def targets(payload: dict) -> list[Path]:
    script = Path(__file__).resolve()
    found = []
    for root in workspace_roots(payload):
        if not opted_in(root):
            continue
        project_script = (system_dir(root) / "scripts" / "hook.py").resolve()
        # .cursor/hooks.json only routes Cursor events; under Claude Code the plugin hook is the only one.
        if payload.get("host") != "claude" and project_owns_hook(root) and script != project_script:
            continue
        found.append(root)
    return found


TRANSCRIPT_MAX_BYTES = 50 * 1024 * 1024
USAGE_FIELDS = {"input_tokens": "input", "output_tokens": "output", "cache_read_input_tokens": "cache_read", "cache_creation_input_tokens": "cache_creation"}


def transcript_tokens(raw_path: str) -> dict | None:
    """Token totals of one Claude Code subagent transcript, numbers only; None when unavailable.

    Each assistant line carries message.usage, and one message spans several lines with the same id, so the last
    usage per id counts. The transcript format is not a documented contract: any surprise means no tokens.
    """
    try:
        path = Path(os.path.expanduser(raw_path))
        if path.suffix != ".jsonl" or "subagents" not in path.parts or not path.is_file():
            return None
        if path.stat().st_size > TRANSCRIPT_MAX_BYTES:
            return None
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
                key = str(message.get("id") or f"line-{index}")
                by_message[key] = {name: int(usage[field]) for field, name in USAGE_FIELDS.items() if isinstance(usage.get(field), int) and not isinstance(usage.get(field), bool)}
        if not by_message:
            return None
        totals = dict.fromkeys(USAGE_FIELDS.values(), 0)
        for usage in by_message.values():
            for name, value in usage.items():
                totals[name] += value
        return totals
    except (OSError, ValueError):
        return None


def log(root: Path, payload: dict, kind: str, summary: str, result: str = "completed", files=None, inferred: bool = False, tokens: dict | None = None) -> None:
    state = load_state(root)
    event = base_event(payload, state, kind, summary, result)
    event["files"] = safe_files(files or [])
    if inferred:
        event["inferred"] = True
    if tokens:
        event["tokens"] = tokens
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


def repeated_skill(root: Path, payload: dict, skill: str) -> bool:
    """A typed slash command followed by the Skill tool for the same skill is one use, not two."""
    try:
        state = load_state(root)
        last = state.get("last_skill") if isinstance(state.get("last_skill"), dict) else {}
        now = time.time()
        session = str(payload.get("session_id") or "")
        same = last.get("name") == skill and last.get("session") == session and now - float(last.get("at") or 0) < SKILL_REPEAT_S
        state["last_skill"] = {"name": skill, "session": session, "at": now}
        save_state(root, state)
        return same
    except (OSError, ValueError, TypeError):
        return False


def stop_reply(root: Path, payload: dict) -> dict:
    """The stop gate's reply for one project; {} on any error, so a broken gate never traps the session."""
    try:
        import stop_gate

        return stop_gate.decide(root, payload)
    except Exception:
        return {}


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
        tokens = transcript_tokens(payload["agent_transcript_path"]) if roots and payload.get("agent_transcript_path") else None
        for root in roots:
            files = payload.get("modified_files") or []
            log(
                root,
                payload,
                "SUBAGENT_STOPPED",
                payload.get("summary") or payload.get("status") or "subagent stopped",
                result=str(payload.get("status") or "completed"),
                files=files,
                tokens=tokens,
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
        reply = {}
        report = design_lint(path, workspace_roots(payload)) if path else ""
        if report:
            for root in roots:
                log(root, payload, "DESIGN_LINT", report.splitlines()[0], result="warning", files=[path])
            reply["design_lint"] = report
        infra = infra_lint(path, workspace_roots(payload)) if path else ""
        if infra:
            for root in roots:
                log(root, payload, "INFRA_LINT", infra.splitlines()[0], result="warning", files=[path])
            reply["infra_lint"] = infra
        return reply

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

    if name == "skillUsed":
        skill = str(payload.get("skill") or "")
        if skill:
            for root in roots:
                if repeated_skill(root, payload, skill):
                    continue
                log(root, payload, "SKILL_USED", skill, result=str(payload.get("source") or "tool"))
        return {}

    if name == "afterAgentResponse":
        text = str(payload.get("text") or "")
        for root in roots:
            log(root, payload, "AGENT_RESPONSE", f"Agent response ({len(text)} chars)")
        if payload.get("stop") and payload.get("host") == "claude":
            for root in roots:
                reply = stop_reply(root, payload)
                if reply:
                    return {"stop_gate": reply}
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
            reply.pop("infra_lint", None)
            emit(reply)
    except Exception:
        if name == "subagentStart":
            emit({"permission": "allow"})
        else:
            emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
