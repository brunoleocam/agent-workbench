"""Spec before code: ask once or twice for a classification or a spec before the first production code file.

Called by hook.py on the Claude Code `PreToolUse` event for file-writing tools. The Stop gate only looks at the end of a
turn, so code written first and a spec written after it passed (benchmark medium round, 6 of 6 plugin runs). This check
asks at the first production code write instead. It never blocks more than `MAX_ASKS` times per project, it allows the
write as soon as a classification is recorded or any spec exists, and any error allows the write (fail open).
`AGENT_WORKBENCH_SPEC_FIRST=off` turns it off.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import resolve_layout  # noqa: E402
from lib import load_state, save_state  # noqa: E402

ENV_SWITCH = "AGENT_WORKBENCH_SPEC_FIRST"
MAX_ASKS = 2
CODE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".c", ".cpp", ".h", ".swift", ".sql", ".sh"}
SKIP_DIRS = {"docs", "doc", "tests", "test", "__tests__", "spec", "specs", "node_modules", "scripts", "examples", ".agent-system", ".claude", ".cursor", ".git", "design"}


# Shell writes: redirects (`> app/main.py`, `>> x.py`, `cat > x.py <<EOF`), `tee`, `sed -i`. The agents create most files this way.
PATH = r"([\w./-]+)"
SHELL_WRITE = [re.compile(r">>?\s*" + PATH), re.compile(r"tee\s+(?:-a\s+)?" + PATH), re.compile(r"sed\s+-i\S*\s+(?:-\S+\s+)*(?:'[^']*'|\"[^\"]*\"|\S+)\s+" + PATH)]


def shell_targets(command: str) -> list[str]:
    return [found for pattern in SHELL_WRITE for found in pattern.findall(command or "")]


def is_production_code(root: Path, raw: str) -> bool:
    if not raw:
        return False
    try:
        relative = Path(raw).resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    if relative.suffix.lower() not in CODE_SUFFIXES or any(part in SKIP_DIRS for part in relative.parts[:-1]):
        return False
    name = relative.name.lower()
    return not (name.startswith("test_") or name.endswith(("_test.py", ".test.ts", ".test.js", ".spec.ts", ".spec.js")) or name == "conftest.py")


def has_spec(root: Path) -> bool:
    try:
        folder = root / str(resolve_layout(root).get("specs_dir") or "docs/specs")
    except Exception:
        folder = root / "docs" / "specs"
    return folder.is_dir() and any(folder.glob("*.md"))


def decide(root: Path, payload: dict) -> dict:
    """The PreToolUse reply for one project: {} to allow, or a deny with the reason."""
    if os.environ.get(ENV_SWITCH, "").strip().lower() in {"off", "0", "false", "no"}:
        return {}
    targets = [str(payload.get("file_path") or "")] + shell_targets(str(payload.get("command") or ""))
    if not any(is_production_code(root, target if os.path.isabs(target) else str(root / target)) for target in targets):
        return {}
    state = load_state(root)
    if state.get("classification") or state.get("classifications") or has_spec(root):
        return {}
    asked = state.get("spec_first_asks") if isinstance(state.get("spec_first_asks"), int) else 0
    if asked >= MAX_ASKS:
        return {}
    state["spec_first_asks"] = asked + 1
    save_state(root, state)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "Agent Workbench: no spec and no classification yet, and this writes production code. Decide first. "
                "Small change (XS or S): `python .agent-system/scripts/classify_floor.py --declared S --feature <slug>`, then write the code. "
                "Anything larger: write docs/specs/<slug>.md first (requirements and acceptance criteria), then the code. "
                "Shared state used by several processes (database, lock, token store) needs a test that runs two processes."
            ),
        }
    }
