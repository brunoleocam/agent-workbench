"""Harness tests (no network, no cost): python benchmark/runner/test_harness.py"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent
sys.path.insert(0, str(HERE))
import bench_lib as B  # noqa: E402

POLICY = json.loads((BENCH / "policy.json").read_text())


class Lib(unittest.TestCase):
    def test_baseline_proof(self):
        ok = B.arm_proof({"plugins": [], "skills": ["update-config"], "agents": []}, "baseline")
        self.assertTrue(ok["ok"])
        bad = B.arm_proof({"plugins": [{"name": "agent-workbench"}], "skills": [], "agents": []}, "baseline")
        self.assertFalse(bad["ok"])
        bad2 = B.arm_proof({"plugins": [], "skills": ["agent-workbench:debug"], "agents": []}, "baseline")
        self.assertFalse(bad2["ok"])
        self.assertFalse(B.arm_proof(None, "baseline")["ok"])

    def test_workbench_proof(self):
        init = {"plugins": [{"name": "agent-workbench", "path": "/opt/plugin"}], "skills": [], "agents": []}
        self.assertTrue(B.arm_proof(init, "workbench", "/opt/plugin")["ok"])
        self.assertFalse(B.arm_proof(init, "workbench", "/home/x/.claude/plugins")["ok"])
        self.assertFalse(B.arm_proof({"plugins": [], "skills": [], "agents": []}, "workbench")["ok"])

    def test_lean_proof_and_copy(self):
        init = {"plugins": [{"name": "agent-workbench", "path": "/opt/plugin"}], "skills": ["x"], "agents": ["agent-workbench:reviewer"]}
        self.assertTrue(B.arm_proof(init, "lean", "/opt/plugin")["ok"])
        full = dict(init, skills=["agent-workbench:tdd"], agents=["agent-workbench:reviewer", "agent-workbench:tester"])
        self.assertFalse(B.arm_proof(full, "lean")["ok"])
        sys.path.insert(0, str(HERE))
        import run
        with tempfile.TemporaryDirectory() as t:
            plug = Path(t) / "p"
            run.make_plugin_copy(plug, lean=True)
            self.assertFalse((plug / "skills").exists())
            self.assertEqual([p.name for p in (plug / "agents").iterdir()], ["reviewer.md"])
            self.assertEqual(list(json.loads((plug / "hooks" / "claude-hooks.json").read_text())["hooks"]), ["Stop", "PreToolUse"])
            self.assertEqual(sorted(p.name[:2] for p in (plug / "rules").iterdir()), [f"0{i}" for i in range(9)])

    def test_needs_reply_and_policy(self):
        self.assertTrue(B.needs_reply("Summary.\n\nDo you approve the spec?"))
        self.assertFalse(B.needs_reply("All done.\n\nWhat a day?\n\nTests pass."))
        self.assertEqual(B.choose_answer(POLICY, "x\n\nDo you approve the spec?")[0], "approve_spec")
        self.assertEqual(B.choose_answer(POLICY, "Which option for the ADR?")[0], "approve_architecture")
        self.assertEqual(B.choose_answer(POLICY, "Do you accept the risk?")[0], "accept_risk")
        self.assertEqual(B.choose_answer(POLICY, "Anything else?")[0], "generic")

    def test_hidden_tests_not_in_agent_inputs(self):
        sys.path.insert(0, str(HERE))
        import run
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            plug = Path(t) / "p"
            run.make_plugin_copy(plug)
            names = {p.name for p in plug.rglob("*")}
            self.assertNotIn("hidden", names)
            self.assertFalse(any(n.startswith("test_acceptance") for n in names))
            self.assertFalse((plug / "benchmark").exists())
            ws = Path(t) / "ws"
            run.prepare_workspace("simple", "baseline", ws, plug)
            self.assertEqual(sorted(p.name for p in ws.iterdir() if p.name != ".git"), ["SPEC.md"])
        for spec in (BENCH / "specs").glob("*.md"):
            self.assertNotIn("hidden", spec.read_text().lower())


class Pipeline(unittest.TestCase):
    """Whole path with the stub, local backend: run -> score. Slow (starts real servers)."""

    def test_end_to_end(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            for arm in ("baseline", "workbench"):
                r = subprocess.run([sys.executable, str(HERE / "run.py"), "--project", "simple", "--arm", arm,
                                    "--round", "1", "--backend", "local", "--runs-dir", t,
                                    "--claude-bin", str(HERE / "claude_stub.cmd" if sys.platform == "win32" else HERE / "claude_stub.sh")],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                run = json.loads((Path(t) / f"simple-{arm}-r1" / "run.json").read_text())
                self.assertTrue(run["valid"], run)
                self.assertEqual(run["intervention_count"], 1)
                self.assertEqual(run["interventions"][0]["node"], "approve_spec")
                self.assertEqual(run["stop_reason"], "finished")
                self.assertAlmostEqual(run["usage"]["cost_usd"], 1.0)
            s = subprocess.run([sys.executable, str(HERE / "score.py"), "--run", str(Path(t) / "simple-baseline-r1"),
                                "--backend", "local", "--no-install", "--skip-mutation"], capture_output=True, text=True)
            self.assertEqual(s.returncode, 0, s.stdout + s.stderr)
            sc = json.loads((Path(t) / "simple-baseline-r1" / "score.json").read_text())
            self.assertEqual(sc["hidden"]["passed"], sc["hidden"]["expected_total"])
            rep = subprocess.run([sys.executable, str(HERE / "report.py"), "--project", "simple", "--runs-dir", t],
                                 capture_output=True, text=True)
            self.assertIn("hidden_pass_rate", rep.stdout)

    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
            (Path(t) / "simple-baseline-r1").mkdir()
            r = subprocess.run([sys.executable, str(HERE / "run.py"), "--project", "simple", "--arm", "baseline",
                                "--round", "1", "--backend", "local", "--runs-dir", t], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
