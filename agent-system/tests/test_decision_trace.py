"""Decision trace: verdict events carry node, inputs, and fingerprint without content; manual trace; per-feature view."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import feature_project, fingerprint, opt_in, run, stamped, write  # noqa: E402


def events(root: Path) -> list[dict]:
    path = root / ".cursor" / "timeline" / "events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def last(root: Path, kind: str) -> dict:
    return [item for item in events(root) if item["event"] == kind][-1]


def test_verdict_events_carry_the_trace() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = feature_project(Path(tmp), status1="done", status2="done")
        opt_in(root)
        for script, extra in (("validate_spec.py", []), ("check_proofs.py", ["--allow-inline"]), ("validate_tasks.py", [])):
            done = run(script, ["--root", str(root), "--feature", "reset", *extra])
            assert done.returncode == 0, (script, done.stdout, done.stderr)
        write(root, "docs/reviews/reset.md", stamped(root))
        gate = run("validate_verification.py", ["--root", str(root), "--feature", "reset"])
        assert gate.returncode == 0, gate.stdout

        expected = {
            "SPEC_VALIDATION_COMPLETED": ("spec_check", {"docs/specs/reset.md"}),
            "TASK_VALIDATION_COMPLETED": ("tasks_check", {"docs/tasks/reset.md", "docs/specs/reset.md"}),
            "PROOF_EXECUTION_COMPLETED": ("proofs", {"docs/tasks/reset.md", ".cursor/agent-system/proofs/reset.json"}),
            "VERIFICATION_COMPLETED": ("gate", {"docs/specs/reset.md", "docs/tasks/reset.md", "docs/reviews/reset.md", ".cursor/agent-system/proofs/reset.json"}),
        }
        current = fingerprint(root)
        for kind, (node, inputs) in expected.items():
            event = last(root, kind)
            assert event["feature"] == "reset", kind
            assert event["node"] == node, kind
            assert inputs <= set(event["inputs"]), (kind, event["inputs"])
            assert all(not item.startswith("/") and ":" not in item for item in event["inputs"]), event["inputs"]
            assert isinstance(event["fingerprint"], str) and len(event["fingerprint"]) >= 12, kind
        assert last(root, "VERIFICATION_COMPLETED")["fingerprint"] == current
        raw = (root / ".cursor" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        assert "TOKEN_TTL" not in raw  # file content never reaches the trace
        assert "Token expires" not in raw  # neither does spec text


def test_manual_trace_redacts_and_checks_the_node() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        opt_in(root)
        base = ["--root", str(root), "--event", "REVIEW_COMPLETED", "--summary", "review x", "--feature", "x"]
        done = run("record_event.py", [*base, "--node", "review", "--inputs", "docs/reviews/x.md,.env"])
        assert done.returncode == 0, done.stderr
        event = last(root, "REVIEW_COMPLETED")
        assert event["node"] == "review"
        assert set(event["inputs"]) == {"docs/reviews/x.md", "[redacted-path]"}
        assert ".env" not in json.dumps(event)
        assert event["fingerprint"]
        unknown = run("record_event.py", [*base, "--node", "ghost-node"])
        assert unknown.returncode == 2 and "Unknown workflow node" in unknown.stderr
        orphan = run("record_event.py", [*base, "--inputs", "docs/a.md"])
        assert orphan.returncode == 2
        plain = run("record_event.py", ["--root", str(root), "--event", "CHECKPOINT_CREATED", "--summary", "Next: x"])
        assert plain.returncode == 0
        assert "node" not in last(root, "CHECKPOINT_CREATED")


def test_feature_view_marks_code_changes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = feature_project(Path(tmp))
        opt_in(root)
        assert run("validate_verification.py", ["--root", str(root), "--feature", "reset"]).returncode == 1
        write(root, "src/reset.py", "TOKEN_TTL = 30\n")
        assert run("validate_verification.py", ["--root", str(root), "--feature", "reset"]).returncode == 1
        other = run("record_event.py", ["--root", str(root), "--event", "REVIEW_COMPLETED", "--summary", "other", "--feature", "other", "--node", "review"])
        assert other.returncode == 0, other.stderr
        assert run("validate_verification.py", ["--root", str(root), "--feature", "reset"]).returncode == 1

        done = run("timeline_view.py", ["--root", str(root), "--feature", "reset", "--json"])
        assert done.returncode == 0, done.stderr
        trace = json.loads(done.stdout)["events"]
        assert [item["event"] for item in trace] == ["VERIFICATION_COMPLETED"] * 3
        assert [item["code_changed"] for item in trace] == [False, True, False]
        assert all(item["node"] == "gate" and item["fingerprint"] for item in trace)
        assert trace[0]["time"] <= trace[1]["time"] <= trace[2]["time"]

        text = run("timeline_view.py", ["--root", str(root), "--feature", "reset"])
        assert text.stdout.count("code changed") == 1
        assert "other" not in text.stdout
        assert "inputs: " in text.stdout
        none = run("timeline_view.py", ["--root", str(root), "--feature", "ghost"])
        assert "No events for feature ghost" in none.stdout
        plain = run("timeline_view.py", ["--root", str(root)])
        assert plain.returncode == 0 and "Agent: " in plain.stdout
