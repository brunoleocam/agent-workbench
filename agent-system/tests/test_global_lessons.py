"""Global lessons: promotion only by the user, the leak filter, session injection with precedence, and the opt-out."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SCRIPTS, opt_in, write  # noqa: E402


def env_for(home: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in {"CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"}}
    env["AGENT_WORKBENCH_HOME"] = str(home)
    return env


def lessons(home: Path, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PYTHON, str(SCRIPTS / "lessons.py"), "--root", str(root), *args], text=True, capture_output=True,
                          env=env_for(home), check=False, encoding="utf-8", errors="replace")


def add(home: Path, root: Path, title: str, *extra: str, scope: str = "project", description: str = "Prefer behavior over internals.") -> str:
    done = lessons(home, root, "add", "--category", "testing", "--title", title, "--description", description, "--scope", scope, *extra)
    assert done.returncode == 0, done.stderr
    return done.stdout.split()[0]


def session(home: Path, root: Path) -> str:
    done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps({"hook_event_name": "sessionStart", "workspace_roots": [str(root)]}),
                          text=True, capture_output=True, env=env_for(home), check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}").get("additional_context", "")


def project(tmp: Path, name: str = "billing-portal") -> Path:
    root = tmp / name
    opt_in(root)
    return root


def test_promote_creates_the_global_store_only_for_confirmed_lessons() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        home, root = tmp / "home", project(tmp)
        first = add(home, root, "Use a fake clock in expiry tests", "--evidence", "TEST-004")
        second = add(home, root, "Name tests after behavior")
        assert not (home / "lessons.json").exists()
        refused = lessons(home, root, "promote", "--id", second)
        assert refused.returncode == 1 and "only a confirmed lesson" in refused.stderr
        assert not (home / "lessons.json").exists()

        assert lessons(home, root, "confirm", "--id", first).returncode == 0
        done = lessons(home, root, "promote", "--id", first)
        assert done.returncode == 0, done.stderr
        stored = json.loads((home / "lessons.json").read_text(encoding="utf-8"))["lessons"]
        assert len(stored) == 1
        assert stored[0]["scope"] == "global" and stored[0]["status"] == "confirmed"
        assert stored[0]["title"] == "Use a fake clock in expiry tests"
        assert stored[0]["evidence"] == []
        assert "billing-portal" not in (home / "lessons.json").read_text(encoding="utf-8")
        assert lessons(home, root, "promote", "--id", first).returncode == 1  # duplicate title in the global store

        # Agents may propose a global candidate; it only loads once the user confirms it.
        candidate = add(home, root, "Keep migrations reversible", scope="global")
        listed = json.loads(lessons(home, root, "list", "--scope", "global", "--json").stdout)
        assert {item["status"] for item in listed} == {"confirmed", "candidate"}
        assert lessons(home, root, "confirm", "--id", candidate, "--scope", "global").returncode == 0
        assert lessons(home, root, "list", "--scope", "global", "--status", "confirmed").stdout.count("LESSON-") == 2
        project_file = json.loads((root / ".cursor/agent-system/lessons.json").read_text(encoding="utf-8"))["lessons"]
        assert [item["id"] for item in project_file] == [first, second]  # the project store is unchanged by global work


def test_leak_filter_refuses_project_details() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        home, root = tmp / "home", project(tmp)
        leaking = {
            "project path": f"Config lives under {root}",
            "project name": "The billing-portal job is slow on Mondays",
            "absolute path": "Read C:/x/y before running",
            "unix path": "Logs go to /var/log/app/ by default",
            "url": "See https://exemplo.com for the rule",
            "secret": "Use token=abc123456789 for the fixture",
            "home path": "Notes are in ~/work/client-x/notes",
            "unc path": "Open \\\\fileserver\\share\\notes first",
            "www url": "See www.example.com for the rule",
            "bare url": "Docs at example.com/path explain it",
            "name variant": "The BillingPortal job is slow on Mondays",
            "name words": "The Billing Portal job is slow on Mondays",
        }
        for label, text in leaking.items():
            if label != "secret":  # a secret never gets into the project store in the first place
                lesson = add(home, root, f"Lesson about {label.replace(' ', '-')}", "--context", text)
                assert lessons(home, root, "confirm", "--id", lesson).returncode == 0, label
                done = lessons(home, root, "promote", "--id", lesson)
                assert done.returncode == 1 and "global lesson must not carry project details" in done.stderr, (label, done.stderr)
                assert not (home / "lessons.json").exists(), label
            direct = lessons(home, root, "add", "--category", "testing", "--title", f"Global {label}", "--description", "x", "--context", text, "--scope", "global")
            assert direct.returncode == 1, label
        clean = add(home, root, "Retry flaky network calls with backoff")
        assert lessons(home, root, "confirm", "--id", clean).returncode == 0
        assert lessons(home, root, "promote", "--id", clean).returncode == 0


def test_session_injects_project_then_global_and_respects_the_opt_out() -> None:
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        home, root = tmp / "home", project(tmp)
        for index in range(6):
            lesson = add(home, root, f"Project rule number {index}")
            assert lessons(home, root, "confirm", "--id", lesson).returncode == 0
        for title in ("Global rule alpha", "Global rule beta", "Global rule gamma", "Global rule delta", "project rule NUMBER 2"):
            lesson = add(home, root, title, scope="global")
            assert lessons(home, root, "confirm", "--id", lesson, "--scope", "global").returncode == 0, title

        # Make the duplicate the newest global lesson, so only the title check can keep it out.
        store = home / "lessons.json"
        data = json.loads(store.read_text(encoding="utf-8"))
        for index, item in enumerate(data["lessons"]):
            item["confirmed_at"] = f"2026-11-12T10:00:0{index}+00:00"
        data["lessons"][-1]["confirmed_at"] = "2026-11-12T11:00:00+00:00"
        store.write_text(json.dumps(data), encoding="utf-8")

        context = session(home, root)
        project_part, _, global_part = context.partition("Global lessons:")
        assert sum(f"Project rule number {index}" in project_part for index in range(6)) == 5
        assert "(+1 more" in project_part
        shown = [title for title in ("alpha", "beta", "gamma", "delta") if f"Global rule {title}" in global_part]
        assert len(shown) == 3, global_part
        assert "number 2" not in global_part.lower()  # same normalized title as a project lesson: the project wins
        assert len(context) <= 900

        write(root, ".cursor/agent-system/layout.json", json.dumps({"global_lessons": False}))
        off = session(home, root)
        assert "Global lessons" not in off and "Project rule number" in off
        refused = lessons(home, root, "list", "--scope", "global")
        assert refused.returncode == 2 and "off for this project" in refused.stderr
        assert lessons(home, root, "promote", "--id", "LESSON-001").returncode == 2
