#!/usr/bin/env python3
"""Fake `claude` for harness tests: no network, no cost. Emits stream-json like Claude Code."""
import json
import shutil
import sys
from pathlib import Path

argv = sys.argv[1:]
BENCH = Path(__file__).resolve().parents[1]
if "--version" in argv:
    print("2.1.322 (stub)")
    sys.exit(0)
resume = "--resume" in argv
plugin = "--plugin-dir" in argv
prompt = argv[argv.index("-p") + 1]
spec = Path("SPEC.md").read_text()
project = "simple" if "Warehouse" in spec else ("long" if "(version" in spec else "medium")
with open("stub_specs_seen.txt", "a") as seen:
    seen.write(spec.splitlines()[0] + "\n")
sid = "stub-session"
print(json.dumps({"type": "system", "subtype": "init", "session_id": sid,
                  "plugins": ([{"name": "agent-workbench", "path": argv[argv.index("--plugin-dir") + 1]}] if plugin else []),
                  "skills": (["agent-workbench:feature"] if plugin else ["update-config"]), "agents": []}))
if not resume:
    shutil.copytree(BENCH / "reference" / project / "app", "app", dirs_exist_ok=True)
    Path("requirements.txt").write_text("fastapi\nuvicorn\n")
    text = "I wrote the spec summary.\n\nDo you approve the spec?"
else:
    text = "Done. All verified."
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}],
                  "usage": {"input_tokens": 10, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 0}}}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": text, "session_id": sid,
                  "total_cost_usd": 0.5, "duration_api_ms": 1000, "num_turns": 2,
                  "usage": {"input_tokens": 10, "output_tokens": 20, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 5}}))
