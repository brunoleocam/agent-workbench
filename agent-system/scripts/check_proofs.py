"""Run the TEST commands of a feature and record verification proofs with the real exit code.

Commands run without a shell, from the project root, with a timeout. Executables outside the allowlist,
commands that install, publish, or remove packages, and inline code (python -c, node -e) are refused, also
behind wrappers like `uv run`. A TEST runs the project's test runner or test files. The policy is not a sandbox:
a test file still runs whatever it contains.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artifacts import (  # noqa: E402
    Block,
    Bundle,
    ConfigError,
    add_common_args,
    config_error,
    inside,
    load_bundle,
    load_proofs,
    project_root,
    proofs_file,
    record,
    resolve_layout,
    truthy,
    workspace_fingerprint,
)
from lib import redact, redact_secrets, utc_now, write_json  # noqa: E402

ALLOWED_EXECUTABLES = {
    "python", "python3", "py", "pytest", "uv", "poetry", "tox", "nox", "hatch",
    "node", "npm", "pnpm", "yarn", "bun", "deno", "vitest", "jest", "tsc",
    "dotnet", "go", "cargo", "mvn", "mvnw", "gradle", "gradlew", "java",
    "php", "composer", "phpunit", "pest", "ruby", "bundle", "rake", "rspec", "make", "ctest",
}
PACKAGE_TOOLS = {"npm", "pnpm", "yarn", "bun", "deno", "composer", "cargo", "uv", "poetry", "bundle", "gem", "dotnet", "go", "mvn", "mvnw", "gradle", "gradlew", "pip", "hatch", "make"}
MUTATING = {
    "install", "i", "in", "un", "r", "it", "install-test", "cit", "install-ci-test", "add", "ci", "publish", "unpublish", "uninstall",
    "remove", "rm", "update", "upgrade", "up", "link", "require", "deploy", "push", "get", "login", "logout", "dlx",
    "create", "init",
}
DOWNLOADERS = {("npm", "exec"), ("npm", "x"), ("bun", "x")}
DOWNLOAD_TOOLS = {"npx", "pnpx", "bunx"}
INSTALL_ON_BARE = {"yarn", "bundle"}
SHELL_TOKENS = {"&&", "||", "|", ";", ">", ">>", "<", "2>", "2>&1", "&"}
SHELL_SEPARATORS = re.compile(r"&&|\|\||[;|&\n]")
SHELL_EXPANSION = re.compile(r"\$\(|`|<<|<\(|>\(")
PYTHON_NAME = re.compile(r"(?:python|pypy)(?:\d+(?:\.\d+)?)?")
PIP_NAME = re.compile(r"pip(?:\d+(?:\.\d+)?)?")
# -[no-value flags][c|m|W|X][attached rest]
PYTHON_FLAG = re.compile(r"-([bBdEhiIOPqsSuvVx]*)([cmWX]?)(.*)")
# python -m <module> runs that module with its own arguments; only test tooling or project modules count as a test.
PYTHON_TEST_MODULES = {
    "pytest", "unittest", "doctest", "nose2", "coverage", "tox", "nox", "mypy", "ruff", "flake8", "pylint", "black",
    "isort", "pyright", "bandit", "behave", "green", "py_compile", "compileall", "django",
}
# interpreter -> (flags that take inline code, flags whose next argument is a value, combined-flag pattern)
INLINE_INTERPRETERS = {
    "node": ({"-e", "--eval", "-p", "--print", "-pe", "-ep"}, {"-r", "--require", "--import", "--loader", "--experimental-loader", "-C", "--conditions", "--input-type"}, None),
    "bun": ({"-e", "--eval", "-p", "--print"}, {"-r", "--preload"}, None),
    "ruby": ({"-e"}, {"-I", "-r", "-C"}, re.compile(r"-[wWvdnpals]*e.*")),
    "rake": ({"-e", "-E", "-p", "--execute", "--execute-print", "--execute-continue"}, {"-f", "-I", "-r", "-R", "-C"}, None),
    "php": ({"-r", "-R", "-B", "-E"}, {"-d", "-c", "-z"}, None),
    "make": ({"--eval", "-E"}, {"-f", "-C", "-I", "-j", "-o", "-W"}, None),
    "bash": (set(), set(), re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")),
    "sh": (set(), set(), re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")),
    "zsh": (set(), set(), re.compile(r"-[a-zA-Z]*c[a-zA-Z]*")),
    "perl": ({"-e", "-E"}, {"-I", "-M", "-m"}, re.compile(r"-(?![IMm])[a-zA-Z0-9]*[eE].*")),
}
REMOTE_CODE = ("data:", "http:", "https:")
DENO_REMOTE = REMOTE_CODE + ("npm:", "jsr:")
# package managers that can start a binary directly: `yarn run node -e`, `pnpm node -e`
SCRIPT_RUNNERS = {"npm", "pnpm", "yarn", "bun"}
STDIN_INTERPRETERS = {"bash", "sh", "zsh", "dash", "ksh", "python", "py", "node", "ruby", "perl", "php", "pwsh", "powershell", "bun", "deno"}
PIPE = re.compile(r"(?<!\|)\|(?!\|)")
BATCH_META = re.compile(r"[&|<>^%\r\n]")
# Case-insensitive shells: any of these arguments means a command string, even if the shell was allowed with --allow.
SHELL_COMMAND_FLAGS = {"pwsh": {"-c", "-command", "-encodedcommand", "-ec", "-e"}, "powershell": {"-c", "-command", "-encodedcommand", "-ec", "-e"}, "cmd": {"/c", "/k", "/r"}}
# tool -> subcommands that run another command, which gets the same policy
WRAPPERS = {"uv": {"run"}, "poetry": {"run"}, "hatch": {"run"}, "pnpm": {"exec"}, "yarn": {"exec", "node"}, "bundle": {"exec"}, "tox": {"exec", "e"}}
WRAPPER_VALUE_FLAGS = {
    "--package", "--python", "-p", "--with", "--with-requirements", "--with-editable", "--extra", "--group",
    "--only-group", "--env-file", "--project", "--directory", "--index", "--index-url", "-C", "--filter", "-F",
    "--dir", "--cwd", "--gemfile", "-e", "--env",
}
EXE_SUFFIXES = (".exe", ".cmd", ".bat", ".ps1", ".sh")
OUTPUT_TAIL = 20_000
MD_TAIL_LINES = 30
DEFAULT_TIMEOUT = 600
MAX_TIMEOUT = 86_400


def split_command(raw: str) -> list[str]:
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] == "`":
        text = text[1:-1].strip()
    if text.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("Command looks like a JSON list but is invalid") from exc
        if not isinstance(data, list) or not data or not all(isinstance(item, str) for item in data):
            raise ValueError("Command JSON must be a non-empty list of strings")
        return data
    lexer = shlex.shlex(text, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ""
    parts = list(lexer)
    if not parts:
        raise ValueError("Command is empty")
    return parts


def exe_name(value: str) -> str:
    name = Path(value).name.lower()
    for suffix in EXE_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    if PYTHON_NAME.fullmatch(name):
        return "python"
    if PIP_NAME.fullmatch(name):
        return "pip"
    return name


def looks_like_file(item: str) -> bool:
    """A script argument; anything else may be the value of an unknown option that hides a later -c/-e."""
    return "." in item or "/" in item or "\\" in item


def python_invocation(args: list[str]) -> tuple[str, str]:
    """('inline'|'module'|'script'|'', target) for the arguments of a python interpreter."""
    index = 0
    while index < len(args):
        item = args[index]
        if item == "-":
            return "inline", ""
        if item.startswith("--") or not item.startswith("-"):
            if not item.startswith("-") and looks_like_file(item):
                return "script", item
            index += 1
            continue
        match = PYTHON_FLAG.fullmatch(item)
        kind, rest = (match.group(2), match.group(3)) if match else ("", "")
        if kind == "c":
            return "inline", ""
        if kind == "m":
            return "module", (rest or (args[index + 1] if index + 1 < len(args) else "")).lower()
        index += 2 if kind in {"W", "X"} and not rest else 1
    return "", ""


def project_module(module: str, cwd: Path | None) -> bool:
    if cwd is None or not re.fullmatch(r"[A-Za-z_][\w.]*", module):
        return False
    first = module.split(".")[0]
    return (cwd / first).is_dir() or (cwd / f"{first}.py").is_file()


def subcommands(args: list[str]) -> tuple[list[str], str]:
    """Positional words before `--`, and the first word that is not the value of a preceding flag."""
    lowered = [item.lower() for item in args]
    before = lowered[: lowered.index("--")] if "--" in lowered else lowered
    positional = [item for item in before if not item.startswith("-")]
    after_values, skip = "", False
    for item in before:
        if skip:
            skip = False
            continue
        if item.startswith("-"):
            skip = "=" not in item
            continue
        after_values = item
        break
    return positional, after_values


def install_refusal(argv: list[str]) -> str | None:
    """Package install, publish, or download; checked in argv and in every shell segment."""
    name = exe_name(argv[0])
    if name in DOWNLOAD_TOOLS:
        return "command downloads and runs packages"
    positional, after_values = subcommands(argv[1:])
    first = positional[0] if positional else ""
    candidates = {first, after_values}
    if first in {"pip", "tool", "global", "self"} and len(positional) > 1:
        candidates.add(positional[1])
    if name in PACKAGE_TOOLS and candidates & MUTATING:
        return "command installs, publishes, or removes packages"
    if any((name, item) in DOWNLOADERS for item in candidates) or (name in INSTALL_ON_BARE and not first):
        return "command installs or downloads packages"
    if name == "pip":
        return "command installs packages"
    if name in {"python", "py"}:
        kind, target = python_invocation(argv[1:])
        if kind == "module" and (target in {"pip", "ensurepip", "venv"} or (target in {"uv", "poetry"} and candidates & MUTATING)):
            return "command installs packages"
        if kind == "script" and target.lower().endswith("setup.py") and set(positional[1:]) & {"install", "develop", "upload"}:
            return "command installs packages"
    return None


def inline_code(argv: list[str], cwd: Path | None = None) -> bool:
    """Code given on the command line (python -c, node -e, bash -c...) instead of a test runner or test file."""
    name = exe_name(argv[0])
    args = argv[1:]
    if name in SHELL_COMMAND_FLAGS:
        return any(item.lower() in SHELL_COMMAND_FLAGS[name] for item in args)
    if name in {"python", "py"}:
        kind, target = python_invocation(args)
        if kind == "module" and target == "coverage" and "run" in args:
            return inline_code(["python", *args[args.index("run") + 1:]], cwd)
        if kind == "module" and target == "django" and set(args) & {"shell", "dbshell", "runscript"}:
            return True
        return kind == "inline" or (kind == "module" and target not in PYTHON_TEST_MODULES and not project_module(target, cwd))
    if name == "deno":
        first = next((item.lower() for item in args if not item.startswith("-")), "")
        return first in {"eval", "repl"} or (first == "run" and any(item.lower().startswith(DENO_REMOTE) for item in args))
    if name in {"mvn", "mvnw"}:
        return any(item.lower().startswith(("exec:", "org.codehaus.mojo:exec")) for item in args)
    spec = INLINE_INTERPRETERS.get(name)
    if spec is None:
        return False
    inline, valued, combined = spec
    index = 0
    while index < len(args):
        item = args[index]
        flag, _, attached = item.partition("=")
        if item in inline or (item.startswith("--") and flag in inline) or (combined and not item.startswith("--") and combined.fullmatch(item)):
            return True
        if item in valued or (item.startswith("--") and flag in valued):
            value = attached if attached else (args[index + 1] if index + 1 < len(args) else "")
            if value.lower().startswith(REMOTE_CODE):
                return True
            index += 1 if attached else 2
            continue
        if item == "-":
            return True
        if not item.startswith("-") and looks_like_file(item):
            return False
        index += 1
    return False


def wrapped_command(argv: list[str]) -> list[str] | None:
    """The command that `uv run`, `poetry run`, `bundle exec`, `yarn node`... would start."""
    names = WRAPPERS.get(exe_name(argv[0]))
    if not names:
        return None
    tokens, index = argv[1:], 0
    while index < len(tokens):
        item = tokens[index]
        if item.startswith("-"):
            index += 2 if item in WRAPPER_VALUE_FLAGS else 1
            continue
        if item.lower() not in names:
            return None
        if item.lower() == "node":
            return ["node", *tokens[index + 1:]]
        rest, start = tokens[index + 1:], 0
        while start < len(rest) and rest[start].startswith("-"):
            start += 2 if rest[start] in WRAPPER_VALUE_FLAGS else 1
        inner = rest[start:]
        if not inner or (":" in inner[0] and exe_name(argv[0]) == "hatch"):
            return None
        if inner[0].lower().endswith(".py"):
            return ["python", *inner]
        return inner
    return None


def runner_target(argv: list[str]) -> list[str] | None:
    """The interpreter or package tool a package manager would start: `yarn run node -e`, `pnpm node -e`."""
    if exe_name(argv[0]) not in SCRIPT_RUNNERS:
        return None
    index = 1
    while index < len(argv):
        item = argv[index]
        if item.startswith("-"):
            index += 2 if item in WRAPPER_VALUE_FLAGS else 1
            continue
        if exe_name(item) in SCANNED_IN_SHELL:
            return argv[index:]
        if item.lower() not in {"run", "run-script"}:
            return None
        index += 1
    return None


def policy_refusal(argv: list[str], allowed: set[str] | None, allow_inline: bool = False, cwd: Path | None = None) -> str | None:
    """allowed=None skips the executable list (shell segments, already double opt-in)."""
    name = exe_name(argv[0])
    if allowed is not None and name not in allowed:
        return f"executable '{name}' is not allowed; pass --allow {name} if this runner is intended"
    refusal = install_refusal(argv)
    if refusal:
        return refusal
    if not allow_inline and inline_code(argv, cwd):
        return "command runs inline code or a module that is not a test runner; point the TEST at the project's test runner or a test file, or pass --allow-inline with the user's authorization"
    inner = wrapped_command(argv)
    if inner:
        refusal = policy_refusal(inner, allowed, allow_inline, cwd)
        if refusal:
            return refusal
    target = runner_target(argv)
    if target:
        refusal = policy_refusal(target, None, allow_inline, cwd)
        if refusal:
            return refusal
    if allowed is not None and any(item in SHELL_TOKENS for item in argv[1:]):
        return "command uses shell operators; set 'Shell: yes' and pass --allow-shell"
    return None


def batch_refusal(found: str, argv: list[str], windows: bool = os.name == "nt") -> str | None:
    """Windows runs .cmd/.bat (npm.cmd, gradlew.bat) through cmd.exe, which parses these characters even inside arguments."""
    if windows and found.lower().endswith((".cmd", ".bat")) and any(BATCH_META.search(item) for item in argv[1:]):
        return "argument has a cmd.exe metacharacter (& | < > ^ % or a newline) and the executable is a .cmd/.bat file; set 'Shell: yes' and pass --allow-shell"
    return None


SCANNED_IN_SHELL = set(INLINE_INTERPRETERS) | set(SHELL_COMMAND_FLAGS) | PACKAGE_TOOLS | DOWNLOAD_TOOLS | {"python", "py", "deno", "mvn", "mvnw", "uv", "poetry", "hatch"}


def shell_refusal(text: str, allow_inline: bool = False, cwd: Path | None = None) -> str | None:
    """Best effort over a shell string: every segment and every interpreter or package tool inside it."""
    if not allow_inline and SHELL_EXPANSION.search(text):
        return "command uses shell substitution or a heredoc; pass --allow-inline with the user's authorization"
    for piped in PIPE.split(text)[1:] if not allow_inline else []:
        try:
            argv = split_command(SHELL_SEPARATORS.split(piped)[0])
        except ValueError:
            continue
        name = exe_name(argv[0]) if argv else ""
        if name in STDIN_INTERPRETERS and ((name in {"bash", "sh", "zsh", "dash", "ksh"} and "-s" in argv[1:]) or all(item.startswith("-") for item in argv[1:])):
            return "command pipes code into an interpreter; pass --allow-inline with the user's authorization"
    for segment in SHELL_SEPARATORS.split(text):
        try:
            argv = split_command(segment)
        except ValueError:
            continue
        for index, item in enumerate(argv):
            if index == 0 or exe_name(item) in SCANNED_IN_SHELL:
                refusal = policy_refusal(argv[index:], None, allow_inline, cwd)
                if refusal:
                    return refusal
    return None


def kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=15, check=False)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


def run_process(command, shell: bool, cwd: Path, timeout: int) -> tuple[int | None, bytes, bytes, bool]:
    kwargs = {"cwd": str(cwd), "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "stdin": subprocess.DEVNULL, "shell": shell}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(command, **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err, False
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            out, err = b"", b""
        return None, out or b"", err or b"", True


def tail(data: bytes) -> str:
    text = redact_secrets(data.decode("utf-8", errors="replace"))
    return text if len(text) <= OUTPUT_TAIL else "…" + text[-OUTPUT_TAIL:]


def requirement_ids(test: Block, bundle: Bundle) -> list[str]:
    reqs = test.ids("requirements", "REQ")
    if bundle.spec:
        criteria = {block.id: block for block in bundle.spec.of_kind("AC")}
        for item in test.ids("acceptance", "AC"):
            block = criteria.get(item)
            if block:
                reqs += [req for req in block.ids("requirements", "REQ") if req not in reqs]
    return reqs


def task_ids(test: Block, bundle: Bundle) -> list[str]:
    tasks = test.ids("task", "TASK")
    for task in bundle.task_blocks():
        if test.id in task.ids("verification", "TEST") and task.id not in tasks:
            tasks.append(task.id)
    return tasks


def test_timeout(test: Block, default: int) -> int:
    raw = test.get("timeout").rstrip("s ")
    if raw.isdigit() and 1 <= int(raw) <= MAX_TIMEOUT:
        return int(raw)
    return default


def execute(test: Block, bundle: Bundle, args, allowed: set[str]) -> dict:
    root = bundle.root
    proof = {
        "test": test.id,
        "title": test.title,
        "requirements": requirement_ids(test, bundle),
        "acceptance": test.ids("acceptance", "AC"),
        "task": task_ids(test, bundle),
        "required": truthy(test.get("required"), True),
        "command": redact(test.get("command"), 300),
        "shell": truthy(test.get("shell"), False),
        "exit_code": None,
        "status": "ERROR",
        "reason": "",
        "started_at": None,
        "finished_at": None,
        "duration_s": None,
        "stdout_tail": "",
        "stderr_tail": "",
    }
    raw = test.get("command")
    if not raw:
        proof["reason"] = "TEST has no Command"
        return proof
    try:
        cwd = inside(root, root / test.get("cwd")) if test.get("cwd") else root
    except ConfigError as exc:
        proof["status"], proof["reason"] = "REFUSED", str(exc)
        return proof
    if not cwd.is_dir():
        proof["reason"] = "working directory not found"
        return proof
    if proof["shell"]:
        if not args.allow_shell:
            proof["status"], proof["reason"] = "REFUSED", "Shell: yes requires --allow-shell"
            return proof
        command, display = raw.strip().strip("`"), "shell"
        refusal = shell_refusal(command, args.allow_inline, cwd)
        if refusal:
            proof["status"], proof["reason"] = "REFUSED", refusal
            return proof
    else:
        try:
            argv = split_command(raw)
        except ValueError as exc:
            proof["reason"] = str(exc)
            return proof
        refusal = policy_refusal(argv, allowed, args.allow_inline, cwd)
        if refusal:
            proof["status"], proof["reason"] = "REFUSED", refusal
            return proof
        if Path(argv[0]).is_absolute():
            found = argv[0] if Path(argv[0]).is_file() else None
        elif "/" in argv[0] or "\\" in argv[0]:
            try:
                resolved = inside(root, cwd / argv[0])
            except ConfigError as exc:
                proof["status"], proof["reason"] = "REFUSED", str(exc)
                return proof
            found = str(resolved) if resolved.is_file() else None
        else:
            found = shutil.which(argv[0])
        if not found:
            proof["reason"] = f"executable not found: {exe_name(argv[0])} (environment problem, not an application failure)"
            return proof
        refusal = batch_refusal(found, argv)
        if refusal:
            proof["status"], proof["reason"] = "REFUSED", refusal
            return proof
        command, display = [found, *argv[1:]], "argv"
    if args.dry_run:
        proof["status"], proof["reason"] = "PLANNED", f"would run ({display})"
        return proof
    timeout = test_timeout(test, args.timeout)
    proof["started_at"] = utc_now()
    started = time.monotonic()
    try:
        code, out, err, timed_out = run_process(command, proof["shell"], cwd, timeout)
    except OSError as exc:
        proof["finished_at"] = utc_now()
        proof["reason"] = f"could not start: {exc.__class__.__name__} (environment problem)"
        return proof
    proof["finished_at"] = utc_now()
    proof["duration_s"] = round(time.monotonic() - started, 3)
    proof["stdout_tail"], proof["stderr_tail"] = tail(out), tail(err)
    proof["exit_code"] = code
    if timed_out:
        proof["status"], proof["reason"] = "TIMEOUT", f"exceeded {timeout}s (process tree killed)"
    elif code == 0:
        proof["status"] = "PASS"
    else:
        proof["status"], proof["reason"] = "FAIL", f"exit code {code}"
    return proof


def render_markdown(data: dict) -> str:
    fp = data.get("fingerprint") or {}
    lines = [
        "# Verification Proofs",
        "",
        f"Feature: {data.get('feature')}",
        f"Updated: {data.get('updated_at')}",
        f"Workspace fingerprint: {fp.get('digest', '')[:16]} ({fp.get('mode')}, head {str(fp.get('head') or '-')[:12]}, {fp.get('changed_files')} changed files)",
        "",
        "Generated by check_proofs.py. The JSON next to this file is the source of truth.",
        "",
    ]
    for proof in data.get("proofs", []):
        lines += [
            f"## {proof.get('id')}",
            "",
            f"- Test: {proof.get('test')} {proof.get('title') or ''}".rstrip(),
            f"- Requirement: {', '.join(proof.get('requirements') or []) or '-'}",
            f"- Acceptance Criterion: {', '.join(proof.get('acceptance') or []) or '-'}",
            f"- Task: {', '.join(proof.get('task') or []) or '-'}",
            f"- Command: `{proof.get('command')}`",
            f"- Exit Code: {proof.get('exit_code')}",
            f"- Status: {proof.get('status')}" + (f" ({proof.get('reason')})" if proof.get("reason") else ""),
            f"- Executed: {proof.get('started_at') or '-'} ({proof.get('duration_s')}s)",
            f"- Fingerprint: {str(proof.get('fingerprint') or '')[:16]}",
            "",
        ]
        for label, key in (("stdout", "stdout_tail"), ("stderr", "stderr_tail")):
            text = (proof.get(key) or "").rstrip()
            if text:
                shown = "\n".join(text.splitlines()[-MD_TAIL_LINES:]).replace("```", "'''")
                lines += [f"{label} (last {MD_TAIL_LINES} lines):", "", "```text", shown, "```", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TEST commands and record verification proofs.")
    add_common_args(parser)
    parser.add_argument("--tasks", help="tasks path relative to the root (overrides --feature)")
    parser.add_argument("--spec", help="spec path, to link proofs to requirements")
    parser.add_argument("--tests", help="extra file with TEST definitions")
    parser.add_argument("--only", action="append", default=[], metavar="TEST-NNN", help="run only these tests (repeatable)")
    parser.add_argument("--task", action="append", default=[], metavar="TASK-NNN", help="run the tests of these tasks (repeatable)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"default seconds per test (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--allow", action="append", default=[], metavar="EXE", help="extra allowed executable (repeatable)")
    parser.add_argument("--allow-shell", action="store_true", help="permit tests marked 'Shell: yes'")
    parser.add_argument("--allow-inline", action="store_true", help="permit inline code (python -c, node -e...); only with the user's authorization")
    parser.add_argument("--dry-run", action="store_true", help="show what would run; record nothing")
    parser.add_argument("--fingerprint", action="store_true", help="print the current workspace fingerprint and exit")
    args = parser.parse_args()
    if not 1 <= args.timeout <= MAX_TIMEOUT:
        return config_error(f"--timeout must be between 1 and {MAX_TIMEOUT}", args.json)
    try:
        if args.fingerprint:
            root = project_root(args.root)
            print(json.dumps(workspace_fingerprint(root, resolve_layout(root)), indent=2))
            return 0
        bundle = load_bundle(args, need=("tasks",))
        tests = bundle.test_blocks()
        if args.only:
            tests = [test for test in tests if test.id in set(args.only)]
        if args.task:
            wanted = set(args.task)
            tests = [test for test in tests if wanted & set(task_ids(test, bundle))]
        if not tests:
            raise ConfigError("No TEST definition matched.")
        existing = load_proofs(bundle.root, bundle.slug)
    except ConfigError as exc:
        return config_error(str(exc), args.json)

    layout_allow = (bundle.layout.get("proof_allow") or []) if isinstance(bundle.layout.get("proof_allow"), list) else []
    allowed = ALLOWED_EXECUTABLES | {exe_name(item) for item in [*args.allow, *layout_allow] if isinstance(item, str)}
    order = {test.id: index for index, test in enumerate(bundle.test_blocks(), start=1)}
    record_on = not args.no_record and not args.dry_run
    record(bundle.root, "PROOF_EXECUTION_STARTED", f"check_proofs {bundle.slug}: {len(tests)} checks", "started", bundle.slug, "tester", record_on)
    before = workspace_fingerprint(bundle.root, bundle.layout)
    results = [execute(test, bundle, args, allowed) for test in tests]
    after = workspace_fingerprint(bundle.root, bundle.layout)
    changed = before["digest"] != after["digest"]
    for proof in results:
        proof["id"] = f"PROOF-{order[proof['test']]:03d}"
        proof["fingerprint"] = before["digest"]

    counts: dict[str, int] = {}
    for proof in results:
        counts[proof["status"]] = counts.get(proof["status"], 0) + 1
    if not args.dry_run:
        merged = {test: proof for test, proof in (existing.get("by_test") or {}).items() if test in order}
        merged.update({proof["test"]: proof for proof in results})
        data = {
            "version": 1,
            "feature": bundle.slug,
            "updated_at": utc_now(),
            "fingerprint": before,
            "proofs": sorted(merged.values(), key=lambda item: order.get(item.get("test"), 10_000)),
        }
        target = proofs_file(bundle.root, bundle.slug)
        write_json(target, data)
        target.with_suffix(".md").write_text(render_markdown(data), encoding="utf-8")

    failed = counts.get("FAIL", 0) + counts.get("TIMEOUT", 0)
    broken = counts.get("ERROR", 0) + counts.get("REFUSED", 0)
    code = 1 if failed or (changed and args.strict) else 2 if broken else 0
    summary = " ".join(f"{key.lower()}={value}" for key, value in sorted(counts.items()))
    if args.json:
        print(json.dumps({"ok": code == 0, "feature": bundle.slug, "counts": counts, "fingerprint": before, "changed_during_run": changed, "proofs": results}, indent=2, ensure_ascii=False))
    else:
        for proof in results:
            reason = f" ({proof['reason']})" if proof["reason"] else ""
            linked = ",".join(proof["acceptance"]) or "-"
            print(f"[{proof['status']}] {proof['test']} ({linked}) exit={proof['exit_code']} {proof['duration_s'] or 0}s{reason}: {proof['command']}")
        if changed:
            label = "FAIL" if args.strict else "WARN"
            print(f"[{label}] Workspace changed while the checks ran; proofs keep the fingerprint from before the run, so the gate will treat them as stale. Rerun with the workspace still, or ignore generated files in git.")
        if not args.dry_run:
            print(f"Proofs written to {proofs_file(bundle.root, bundle.slug).relative_to(bundle.root).as_posix()} ({summary}).")
    record(bundle.root, "PROOF_EXECUTION_COMPLETED", f"check_proofs {bundle.slug}", ("passed " if code == 0 else "failed ") + summary, bundle.slug, "tester", record_on)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
