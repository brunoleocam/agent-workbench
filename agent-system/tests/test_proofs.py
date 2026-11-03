"""check_proofs execution, command policy, fingerprint, and the verification gate."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from support import REVIEW_PASS, feature_project, fingerprint, opt_in, py_command, run, stamped, tasks, write  # noqa: E402

from artifacts import resolve_layout, workspace_fingerprint  # noqa: E402


def proof_run(args: list[str]):
    """Unit tests use python -c for varied exit codes; the policy needs explicit authorization for that."""
    return run("check_proofs.py", [*args, "--allow-inline"])


def proofs(root: Path) -> dict:
    data = json.loads((root / ".cursor/agent-system/proofs/reset.json").read_text(encoding="utf-8"))
    return {item["test"]: item for item in data["proofs"]}


def test_check_proofs_exit_codes_and_timeout() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(
            Path(raw),
            cmd1=py_command("print('token=abc123supersecret'); raise SystemExit(0)"),
            cmd2=py_command("import sys; sys.stderr.write('boom'); raise SystemExit(3)"),
        )
        done = proof_run(["--root", str(root), "--feature", "reset"])
        assert done.returncode == 1, done.stdout + done.stderr
        result = proofs(root)
        assert result["TEST-001"]["status"] == "PASS" and result["TEST-001"]["exit_code"] == 0
        assert result["TEST-001"]["requirements"] == ["REQ-001"] and result["TEST-001"]["task"] == ["TASK-001"]
        assert "abc123supersecret" not in result["TEST-001"]["stdout_tail"]
        assert result["TEST-002"]["status"] == "FAIL" and result["TEST-002"]["exit_code"] == 3
        assert "boom" in result["TEST-002"]["stderr_tail"]
        assert result["TEST-001"]["id"] == "PROOF-001" and result["TEST-001"]["fingerprint"]
        write(root, "docs/tasks/reset.md", tasks(cmd1=py_command("raise SystemExit(0)")).split("### TEST-002")[0])
        proof_run(["--root", str(root), "--feature", "reset"])
        assert set(proofs(root)) == {"TEST-001"}, "proof of a removed TEST must be dropped"
        feature_project(root, cmd1=py_command("print('token=abc123supersecret'); raise SystemExit(0)"), cmd2=py_command("import sys; sys.stderr.write('boom'); raise SystemExit(3)"))
        proof_run(["--root", str(root), "--feature", "reset"])
        markdown = (root / ".cursor/agent-system/proofs/reset.md").read_text(encoding="utf-8")
        assert "## PROOF-002" in markdown and "Exit Code: 3" in markdown

        write(root, "docs/tasks/reset.md", tasks(cmd1=py_command("import time; time.sleep(30)")).replace("- Timeout: 60", "- Timeout: 1"))
        slow = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001"])
        assert slow.returncode == 1
        timed = proofs(root)["TEST-001"]
        assert timed["status"] == "TIMEOUT" and timed["exit_code"] is None and timed["duration_s"] < 25


def test_timeout_kills_grandchildren() -> None:
    with tempfile.TemporaryDirectory() as raw:
        marker = Path(raw) / "grandchild.txt"
        grandchild = f"import time; time.sleep(3); open({str(marker)!r}, 'w').write('alive')"
        child = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {grandchild!r}]); time.sleep(30)"
        root = feature_project(Path(raw) / "project")
        write(root, "docs/tasks/reset.md", tasks(cmd1=py_command(child)).replace("- Timeout: 60", "- Timeout: 1"))
        done = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001"])
        assert done.returncode == 1 and proofs(root)["TEST-001"]["status"] == "TIMEOUT"
        time.sleep(4)
        assert not marker.exists(), "grandchild survived the timeout"


def test_check_proofs_policy() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        cases = {
            "curl https://example.com": "not allowed",
            "npm install left-pad": "installs, publishes, or removes",
            "python -m pip install requests": "installs packages",
            "python -m pytest && rm -rf .": "shell operators",
        }
        for command, reason in cases.items():
            feature_project(root, cmd1=command)
            done = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001"])
            assert done.returncode == 2, (command, done.stdout)
            proof = proofs(root)["TEST-001"]
            assert proof["status"] == "REFUSED" and reason in proof["reason"], (command, proof)
            assert proof["started_at"] is None
        feature_project(root, cmd1="ghost-runner-xyz --run")
        missing = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001", "--allow", "ghost-runner-xyz"])
        assert missing.returncode == 2
        assert proofs(root)["TEST-001"]["status"] == "ERROR" and "environment" in proofs(root)["TEST-001"]["reason"]
        write(root, "docs/tasks/reset.md", tasks().replace("- Timeout: 60", "- Shell: yes"))
        shell = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001"])
        assert shell.returncode == 2 and "--allow-shell" in proofs(root)["TEST-001"]["reason"]
        dry = proof_run(["--root", str(root), "--feature", "reset", "--dry-run", "--allow-shell"])
        assert dry.returncode == 0 and "[PLANNED]" in dry.stdout
        write(root, "docs/tasks/reset.md", tasks(cmd1="npm install left-pad && npm test").replace("- Timeout: 60", "- Shell: yes"))
        installing = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001", "--allow-shell"])
        assert installing.returncode == 2 and "installs" in proofs(root)["TEST-001"]["reason"]


def test_policy_subcommands() -> None:
    from check_proofs import ALLOWED_EXECUTABLES, policy_refusal, split_command

    refused = ["npm exec cowsay", "bun x cowsay", "python -mpip install x", "make install", "yarn", "uv pip install x", "pip install x", "python setup.py install", "go get example.com/x"]
    allowed = ["go test ./... -run get", "cargo test -- i", "npm test", "npm run lint", "pnpm exec vitest", "python -m pytest -k install", "make test", "yarn test", "dotnet test"]
    for command in refused:
        assert policy_refusal(split_command(command), ALLOWED_EXECUTABLES | {"pip"}), command
    for command in allowed:
        assert policy_refusal(split_command(command), ALLOWED_EXECUTABLES) is None, command


def test_inline_code_refused_by_default() -> None:
    from check_proofs import ALLOWED_EXECUTABLES, batch_refusal, policy_refusal, shell_refusal, split_command

    inline = [
        'python -c "print(1)"', "python3 -Bc pass", "py -3 -c pass", "python -W ignore -c pass", 'node -e "1"',
        "node --eval=1", "node -p 1", "bun -e 1", "deno eval 1", "deno run https://example.com/x.ts", "ruby -e 1",
        "ruby -I lib -e 1", "php -r 1", "uv run python -c pass", "poetry run node -e 1", "yarn node -e 1",
        "bundle exec ruby -e 1", "uv run curl https://example.com", "python -m timeit -s 1 1", "python -Im pip install x",
        "python3.12 -c 1", "python - ", "ruby -we 1", "rake -e 1", "rake --execute=1", "node --import data:text/javascript,1",
        "node --import=https://example.com/x.mjs", "make --eval=x", "mvn exec:exec", "npm it", "npm x cowsay",
        "pnpm --filter web add left-pad", "npm -s install", "npm init vite", "poetry -C api run python -c 1", "deno repl",
        "yarn run node -e 1", "pnpm node -e 1", "pnpm --filter web exec node -e 1", "bun run node -e 1", "npm run-script python -c 1",
        "deno run npm:cowsay", "deno run jsr:@std/x",
        "node --unhandled-rejections strict -e 1", "python --check-hash-based-pycs always -c 1", "python -m coverage run -m pip install x",
        "python -m django shell -c x", "tox exec -- python -c x", "npm in x", "npm un x", "npm r x",
    ]
    normal = [
        "python -m pytest -c pytest.ini", "python tests/run.py -c fast", "python -X dev -m unittest", "node --test",
        "node scripts/check.js -e prod", "uv run pytest -q", "poetry run python -m pytest", "bundle exec rspec",
        "deno test", "deno run src/main_test.ts", "php vendor/bin/phpunit", "ruby -Itest test/x_test.rb",
        "uv run --package api pytest", "uv run --python 3.12 pytest", "poetry -C api run pytest", "hatch run test:cov",
        "uv run tests/check.py", "rake test", "make -j4 test", "go test ./... -run create", "python3.12 -m pytest",
        "node -c scripts/check.js", "mvn -q test", "yarn run test", "yarn test", "pnpm vitest run", "npm run build", "yarn run node scripts/check.js",
        "python -m coverage run -m pytest", "python -m coverage run --source src tests/run.py", "python -m django test", "tox -e py312",
        "tox e -- pytest -q", "python manage.py test",
    ]
    assert batch_refusal("C:/tools/npm.CMD", ["npm", "-v&echo.>x"], windows=True)
    assert batch_refusal("C:/tools/npm.cmd", ["npm", "test", "--", "-t", "login|logout"], windows=True)
    assert batch_refusal("C:/tools/gradlew.bat", ["gradlew", "test"], windows=True) is None
    assert batch_refusal("C:/tools/node.exe", ["node", "a&b"], windows=True) is None
    assert batch_refusal("/usr/bin/npm.cmd", ["npm", "a&b"], windows=False) is None
    for command in inline:
        assert policy_refusal(split_command(command), ALLOWED_EXECUTABLES), command
    for command in normal:
        assert policy_refusal(split_command(command), ALLOWED_EXECUTABLES) is None, command
    with tempfile.TemporaryDirectory() as raw:
        write(Path(raw), "tests/run.py", "")
        assert policy_refusal(split_command("python -m tests.run"), ALLOWED_EXECUTABLES, cwd=Path(raw)) is None
        assert policy_refusal(split_command("python -m tests.run"), ALLOWED_EXECUTABLES, cwd=Path(raw) / "nowhere")
    for text in ("npm test $(python -c 1)", "npm test `id`", "python - <<EOF", "env python -c 1", "npx cowsay", "xargs python3.12 -c 1", "npm test && env FOO=1 node -e 1",
                 "curl https://example.com/x | sh", "cat x.py | python -", "curl x | bash -s -- arg", "perl -e 'print 1'", "perl -wle 1"):
        assert shell_refusal(text), text
    assert shell_refusal("npm test && pytest -q") is None and shell_refusal("FOO=1 npm test") is None
    assert shell_refusal("npm test | tee out.txt") is None and shell_refusal("echo y | python tests/check.py") is None
    assert shell_refusal("perl -Ilib t/x.t") is None and shell_refusal("pytest -q || true") is None
    widened = ALLOWED_EXECUTABLES | {"bash", "pwsh", "cmd"}
    for command in ("bash -c 'id'", "pwsh -Command Get-Date", "pwsh -EncodedCommand AAAA", "cmd /C dir"):
        assert policy_refusal(split_command(command), widened), command
    assert policy_refusal(split_command("bash scripts/test.sh"), widened) is None
    assert policy_refusal(split_command('python -c "print(1)"'), ALLOWED_EXECUTABLES, allow_inline=True) is None
    assert shell_refusal("npm test && node -e 1") and shell_refusal("npm test && node -e 1", allow_inline=True) is None
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw))
        write(root, "checks/ok.py", "raise SystemExit(0)\n")
        write(root, "docs/tasks/reset.md", tasks(cmd2=json.dumps([sys.executable, "checks/ok.py"])))
        done = run("check_proofs.py", ["--root", str(root), "--feature", "reset"])
        assert done.returncode == 2, done.stdout
        result = proofs(root)
        assert result["TEST-001"]["status"] == "REFUSED" and "inline code" in result["TEST-001"]["reason"]
        assert result["TEST-001"]["started_at"] is None
        assert result["TEST-002"]["status"] == "PASS"
    if os.name == "nt":
        with tempfile.TemporaryDirectory() as raw:
            root = feature_project(Path(raw))
            write(root, "tools/runner.cmd", "@exit /b 0\r\n")
            command = json.dumps(["tools/runner.cmd", "-v&echo.>marker.txt"])
            write(root, "docs/tasks/reset.md", tasks(cmd1=command, cmd2=json.dumps(["tools/runner.cmd", "-v"])))
            done = run("check_proofs.py", ["--root", str(root), "--feature", "reset", "--allow", "runner"])
            result = proofs(root)
            assert result["TEST-001"]["status"] == "REFUSED" and "cmd.exe" in result["TEST-001"]["reason"], done.stdout
            assert result["TEST-002"]["status"] == "PASS", done.stdout
            assert not (root / "marker.txt").exists()


def test_proofs_keep_fingerprint_from_before_the_run() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw), cmd1=py_command("open('src/reset.py', 'w').write('TOKEN_TTL = 99\\n')"))
        before = workspace_fingerprint(root, resolve_layout(root))["digest"]
        done = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001"])
        assert done.returncode == 0 and "[WARN] Workspace changed" in done.stdout, done.stdout
        assert proofs(root)["TEST-001"]["fingerprint"] == before
        strict = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001", "--strict"])
        assert strict.returncode == 0, "content unchanged on the second run"
        write(root, "docs/tasks/reset.md", tasks(cmd1=py_command("open('src/reset.py', 'a').write('#\\n')")))
        strict = proof_run(["--root", str(root), "--feature", "reset", "--only", "TEST-001", "--strict"])
        assert strict.returncode == 1 and "[FAIL] Workspace changed" in strict.stdout


def test_fingerprint_tracks_code_not_harness_docs() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw))
        layout = resolve_layout(root)
        first = workspace_fingerprint(root, layout)["digest"]
        write(root, "docs/reviews/reset.md", REVIEW_PASS)
        write(root, "docs/progress/CURRENT.md", "# now\n")
        write(root, ".cursor/agent-system/state.json", "{}")
        assert workspace_fingerprint(root, layout)["digest"] == first
        write(root, "src/reset.py", "TOKEN_TTL = 16\n")
        assert workspace_fingerprint(root, layout)["digest"] != first
        if shutil.which("git"):
            git = ["git", "-C", str(root), "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
            subprocess.run([*git, "init", "-q"], check=True)
            subprocess.run([*git, "add", "-A"], check=True)
            subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
            clean = workspace_fingerprint(root, layout)
            assert clean["mode"] == "git" and clean["changed_files"] == 0
            write(root, "docs/reviews/reset.md", REVIEW_PASS)
            assert workspace_fingerprint(root, layout)["digest"] == clean["digest"]
            write(root, "src/new_module.py", "x = 1\n")
            dirty = workspace_fingerprint(root, layout)
            assert dirty["changed_files"] == 1 and dirty["digest"] != clean["digest"]


def test_fingerprint_in_repository_subdirectory() -> None:
    if not shutil.which("git"):
        return
    with tempfile.TemporaryDirectory() as raw:
        repo = Path(raw)
        root = feature_project(repo / "app")
        write(repo, "other/service.py", "y = 1\n")
        git = ["git", "-C", str(repo), "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "init"], check=True)
        layout = resolve_layout(root)
        clean = workspace_fingerprint(root, layout)
        write(root, "src/reset.py", "TOKEN_TTL = 16\n")
        changed = workspace_fingerprint(root, layout)
        assert changed["changed_files"] == 1 and changed["digest"] != clean["digest"]
        write(root, "src/reset.py", "TOKEN_TTL = 17\n")
        assert workspace_fingerprint(root, layout)["digest"] != changed["digest"]
        write(repo, "other/service.py", "y = 2\n")
        write(root, "docs/reviews/reset.md", REVIEW_PASS)
        assert workspace_fingerprint(root, layout)["changed_files"] == 1


def test_validate_verification_gate() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw), status1="done", status2="done")
        opt_in(root)
        args = ["--root", str(root), "--feature", "reset"]
        missing = run("validate_verification.py", args)
        assert missing.returncode == 1
        assert "TEST-001 has no proof" in missing.stdout and "Review is required and was not found." in missing.stdout

        assert proof_run(args).returncode == 0
        write(root, "docs/reviews/reset.md", stamped(root))
        passed = run("validate_verification.py", args)
        assert passed.returncode == 0, passed.stdout + passed.stderr
        events = (root / ".cursor/timeline/events.jsonl").read_text(encoding="utf-8")
        assert "PROOF_EXECUTION_COMPLETED" in events and "VERIFICATION_COMPLETED" in events
        state = json.loads((root / ".cursor/agent-system/state.json").read_text(encoding="utf-8"))
        assert state["verification"]["reset"]["gate"] == "passed" and state["phase"] == "verified"

        write(root, "src/reset.py", "TOKEN_TTL = 30\n")
        stale = run("validate_verification.py", args)
        assert stale.returncode == 1 and "predates the current workspace" in stale.stdout
        assert proof_run(args).returncode == 0

        write(root, "docs/reviews/reset.md", stamped(root, REVIEW_PASS.replace("status: PASS", "status: FAIL", 1)))
        failed_review = run("validate_verification.py", args)
        assert failed_review.returncode == 1 and "Review status is FAIL." in failed_review.stdout, failed_review.stdout
        write(root, "docs/reviews/reset.md", stamped(root))
        tasks_text = (root / "docs/tasks/reset.md").read_text(encoding="utf-8")
        write(root, "docs/tasks/reset.md", tasks_text.replace("raise SystemExit(0)", "raise SystemExit(0)  ", 1))
        changed = run("validate_verification.py", args)
        assert changed.returncode == 1 and "command changed after its proof" in changed.stdout, changed.stdout
        write(root, "docs/tasks/reset.md", tasks_text)
        assert run("validate_verification.py", args).returncode == 0

        blocking = REVIEW_PASS.replace("- Severity: minor\n- Status: resolved", "- Severity: blocker\n- Status: open")
        write(root, "docs/reviews/reset.md", stamped(root, blocking))
        assert "FIND-001 (blocker) is still open" in run("validate_verification.py", args).stdout
        accepted = REVIEW_PASS.replace("- Status: resolved", "- Status: accepted")
        write(root, "docs/reviews/reset.md", stamped(root, accepted))
        assert "accepted as residual risk without a Justification" in run("validate_verification.py", args).stdout
        write(root, "docs/reviews/reset.md", stamped(root, accepted) + "- Justification: cosmetic, tracked in TASK-009\n")
        assert run("validate_verification.py", args).returncode == 0

        spec = (root / "docs/specs/reset.md").read_text(encoding="utf-8").replace("security_risk: LOW", "security_risk: HIGH")
        write(root, "docs/specs/reset.md", spec)
        high = run("validate_verification.py", args)
        assert high.returncode == 1 and "Security review is required" in high.stdout
        write(root, "docs/security/reset.md", "---\nstatus: FAIL\n---\n# Security Assessment\n## High Findings\n### SEC-001: SQL injection\n- Severity: HIGH\n- Classification: confirmed\n- Status: open\n- Location: src/reset.py:1\n")
        sec = run("validate_verification.py", args)
        assert "Security review status is FAIL." in sec.stdout and "SEC-001 (high) is still open" in sec.stdout

        write(root, "docs/tasks/reset.md", tasks(status1="done", status2="in_progress"))
        assert "TASK-002 is in_progress" in run("validate_verification.py", args).stdout


def test_report_fingerprint_must_match_exactly() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw), status1="done", status2="done")
        args = ["--root", str(root), "--feature", "reset"]
        assert proof_run(args).returncode == 0
        digest = fingerprint(root)

        write(root, "docs/reviews/reset.md", REVIEW_PASS)
        missing = run("validate_verification.py", args)
        assert missing.returncode == 1 and "Review has no fingerprint" in missing.stdout, missing.stdout

        other = digest[:-1] + ("0" if digest[-1] != "0" else "1")
        for recorded in (other, digest[:12], digest + "0"):
            write(root, "docs/reviews/reset.md", REVIEW_PASS.replace("---\n", f"---\nfingerprint: {recorded}\n", 1))
            stale = run("validate_verification.py", args)
            assert stale.returncode == 1 and "[FAIL] Review was recorded for another workspace state" in stale.stdout, recorded

        write(root, "docs/reviews/reset.md", stamped(root))
        exact = run("validate_verification.py", args)
        assert exact.returncode == 0 and "Review fingerprint matches the current workspace." in exact.stdout, exact.stdout

        spec = (root / "docs/specs/reset.md").read_text(encoding="utf-8").replace("security_risk: LOW", "security_risk: HIGH")
        write(root, "docs/specs/reset.md", spec)
        security = "---\nstatus: PASS\n---\n# Security Assessment\n"
        write(root, "docs/security/reset.md", security)
        assert "Security review has no fingerprint" in run("validate_verification.py", args).stdout
        write(root, "docs/security/reset.md", security.replace("---\n", f"---\nfingerprint: {other}\n", 1))
        assert "[FAIL] Security review was recorded for another workspace state" in run("validate_verification.py", args).stdout
        write(root, "docs/security/reset.md", stamped(root, security))
        assert run("validate_verification.py", args).returncode == 0

        small = spec.replace("security_risk: HIGH", "security_risk: LOW").replace("complexity: M", "complexity: S")
        write(root, "docs/specs/reset.md", small)
        write(root, "docs/reviews/reset.md", REVIEW_PASS.replace("---\n", f"---\nfingerprint: {other}\n", 1))
        optional = run("validate_verification.py", args)
        assert optional.returncode == 0 and "[WARN] Review was recorded for another workspace state" in optional.stdout, optional.stdout


def test_small_change_needs_no_review() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = feature_project(Path(raw), status1="done", status2="done")
        spec = (root / "docs/specs/reset.md").read_text(encoding="utf-8").replace("complexity: M", "complexity: S")
        write(root, "docs/specs/reset.md", spec)
        args = ["--root", str(root), "--feature", "reset"]
        assert proof_run(args).returncode == 0
        done = run("validate_verification.py", args)
        assert done.returncode == 0, done.stdout
        assert "not required" in done.stdout
