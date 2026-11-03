"""Traceable Markdown artifacts, project layout, workspace fingerprint, and the shared CLI report. Stdlib only."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import append_event, apply_semantic_state, load_state, local_stamp, opted_in, redact, save_state, utc_now  # noqa: E402

ID_KINDS = ("REQ", "AC", "ADR", "TASK", "TEST", "PROOF", "FIND", "SEC")
ID_RE = re.compile(r"\b(" + "|".join(ID_KINDS) + r")-(\d{3,})\b")
ID_HEADING = re.compile(r"^(#{2,6})\s+(?:\[[ xX~!]\]\s+)?(" + "|".join(ID_KINDS) + r")-(\d{3,})\b\s*[:\-–—]?\s*(.*?)\s*#*\s*$")
ANY_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FIELD_LINE = re.compile(r"^\s*[-*]\s+(?:\*\*)?([^\W\d_][\w /-]{0,40}?)(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.*?)\s*$")
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
EMPTY_VALUES = {"", "-", "none", "n/a", "na", "nenhum", "nenhuma", "—"}

FIELD_ALIASES = {
    "requirements": ("requirements", "requirement", "req", "reqs", "requisitos", "requisito"),
    "acceptance": ("acceptance", "acceptance criteria", "acceptance criterion", "ac", "criteria", "critérios", "criterios", "critério de aceite", "criterios de aceite", "critérios de aceite"),
    "task": ("task", "tasks", "tarefa"),
    "files": ("files", "arquivos"),
    "depends": ("depends on", "depends", "dependencies", "dependências", "dependencias", "depende de"),
    "blocked_by": ("blocked by", "bloqueada por", "bloqueado por"),
    "verification": ("verification", "verify", "tests", "verificação", "verificacao"),
    "done_when": ("done when", "completion", "definition of done", "pronto quando", "critério de conclusão", "criterio de conclusao"),
    "gate": ("gate",),
    "status": ("status",),
    "command": ("command", "comando", "cmd"),
    "shell": ("shell",),
    "timeout": ("timeout",),
    "required": ("required", "obrigatório", "obrigatorio"),
    "expected": ("expected", "expected result", "resultado esperado"),
    "cwd": ("cwd", "working directory"),
    "evidence": ("evidence", "evidência", "evidencia"),
    "severity": ("severity", "severidade"),
    "confidence": ("confidence", "confiança", "confianca"),
    "classification": ("classification", "classificação", "classificacao"),
    "location": ("location", "local"),
    "justification": ("justification", "justificativa"),
    "verification_criterion": ("fix verification",),
    "priority": ("priority", "prioridade"),
    "type": ("type", "tipo"),
}
ALIAS_TO_FIELD = {alias: name for name, aliases in FIELD_ALIASES.items() for alias in aliases}

LAYOUT_DEFAULTS = {
    "specs_dir": "docs/specs",
    "tasks_dir": "docs/tasks",
    "tests_dir": "docs/tests",
    "reviews_dir": "docs/reviews",
    "security_dir": "docs/security",
    "changes_dir": "docs/changes",
    "progress_dir": "docs/progress",
    "adr_dir": "docs/architecture/ADR",
}
FINGERPRINT_SKIP = {
    ".git", ".cursor", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", ".tox", "coverage", ".coverage", "dist", "build", "bin", "obj", "target", ".next", ".gradle",
}
FINGERPRINT_FILE_LIMIT = 5000
FINGERPRINT_BYTES_LIMIT = 5_000_000


class ConfigError(Exception):
    """Bad argument, missing file, invalid JSON, or a path outside the project. Exit code 2."""


@dataclass
class Block:
    id: str
    kind: str
    number: int
    title: str
    level: int
    line: int
    fields: dict = field(default_factory=dict)
    text: str = ""
    source: str = ""

    def get(self, name: str) -> str:
        value = self.fields.get(name, "").strip()
        return "" if value.lower() in EMPTY_VALUES else value

    def ids(self, name: str, kind: str | None = None) -> list[str]:
        return [item for item in ids_in(self.get(name)) if kind is None or item.startswith(kind + "-")]


@dataclass
class Document:
    path: Path
    frontmatter: dict
    blocks: list[Block]
    headings: list[tuple[int, str, int]]
    lines: list[str]

    def of_kind(self, kind: str) -> list[Block]:
        return [block for block in self.blocks if block.kind == kind]

    def section_lines(self, names: tuple[str, ...]) -> list[str] | None:
        wanted = {name.lower() for name in names}
        for index, (level, title, line) in enumerate(self.headings):
            if title.lower().strip() in wanted:
                end = len(self.lines)
                for other_level, _, other_line in self.headings[index + 1 :]:
                    if other_level <= level:
                        end = other_line - 1
                        break
                return self.lines[line:end]
        return None


def ids_in(value: str) -> list[str]:
    seen, out = set(), []
    for kind, number in ID_RE.findall(value or ""):
        item = f"{kind}-{number}"
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def parse_frontmatter(lines: list[str]) -> tuple[dict, int]:
    if not lines or lines[0].strip() != "---":
        return {}, 0
    data = {}
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == "---":
            return data, index + 1
        if ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            data[key.strip().lower()] = value.strip().strip("\"'")
    return {}, 0


def parse_text(text: str, source: str = "") -> tuple[dict, list[Block], list[tuple[int, str, int]], list[str]]:
    lines = text.lstrip("\ufeff").splitlines()
    frontmatter, start = parse_frontmatter(lines)
    blocks: list[Block] = []
    headings: list[tuple[int, str, int]] = []
    current: Block | None = None
    body: list[str] = []
    fence = False

    def close() -> None:
        nonlocal current, body
        if current is not None:
            current.text = "\n".join(body).strip()
            blocks.append(current)
        current, body = None, []

    for index in range(start, len(lines)):
        line = lines[index]
        number = index + 1
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
            if current is not None:
                body.append(line)
            continue
        if fence:
            if current is not None:
                body.append(line)
            continue
        heading = ANY_HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            headings.append((level, heading.group(2), number))
            if current is not None and level <= current.level:
                close()
            found = ID_HEADING.match(line)
            if found:
                close()
                kind, digits = found.group(2), found.group(3)
                current = Block(
                    id=f"{kind}-{digits}",
                    kind=kind,
                    number=int(digits),
                    title=found.group(4).strip(),
                    level=len(found.group(1)),
                    line=number,
                    source=source,
                )
                continue
        if current is None:
            continue
        item = FIELD_LINE.match(line)
        if item:
            name = ALIAS_TO_FIELD.get(item.group(1).strip().lower())
            if name:
                value = item.group(2).strip()
                previous = current.fields.get(name)
                current.fields[name] = f"{previous}, {value}" if previous else value
                continue
        body.append(line)
    close()
    return frontmatter, blocks, headings, lines


def load_document(path: Path) -> Document:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"File not found: {path}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"Cannot read {path.name}: {exc.__class__.__name__}") from exc
    frontmatter, blocks, headings, lines = parse_text(text, str(path))
    return Document(path=path, frontmatter=frontmatter, blocks=blocks, headings=headings, lines=lines)


def inside(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ConfigError(f"Path outside the project root: {candidate}") from exc
    return resolved


def project_root(raw: str) -> Path:
    root = Path(raw or ".").resolve()
    if not root.is_dir():
        raise ConfigError(f"Project root not found: {raw}")
    return root


def load_json_file(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path.name} (line {exc.lineno})") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read {path.name}: {exc.__class__.__name__}") from exc


def load_layout(root: Path) -> dict:
    data = load_json_file(root / ".cursor" / "agent-system" / "layout.json", {})
    if not isinstance(data, dict):
        raise ConfigError("layout.json must contain a JSON object")
    return data


def resolve_layout(root: Path, layout: dict | None = None) -> dict:
    """Directory per artifact kind: overrides, then what init discovered, then docs/ defaults."""
    layout = load_layout(root) if layout is None else layout
    overrides = layout.get("overrides") if isinstance(layout.get("overrides"), dict) else {}
    specs = layout.get("specs") if isinstance(layout.get("specs"), list) else []
    adr_dirs = layout.get("adr_dirs") if isinstance(layout.get("adr_dirs"), list) else []
    discovered = {
        "specs_dir": "docs/specs" if "docs/specs" in specs else (specs[0] if specs else None),
        "tasks_dir": layout.get("tasks_dir"),
        "tests_dir": layout.get("tests_dir"),
        "reviews_dir": layout.get("reviews_dir"),
        "security_dir": layout.get("security_dir"),
        "changes_dir": layout.get("changes_dir"),
        "progress_dir": layout.get("progress_dir"),
        "adr_dir": adr_dirs[0] if adr_dirs else None,
    }
    resolved = {}
    for key, default in LAYOUT_DEFAULTS.items():
        value = overrides.get(key) or discovered.get(key) or default
        if not isinstance(value, str):
            raise ConfigError(f"layout.json: {key} must be a string path")
        resolved[key] = Path(value).as_posix().strip("/")
        inside(root, root / resolved[key])
    extra = [item for item in adr_dirs if isinstance(item, str)]
    resolved["adr_dirs"] = list(dict.fromkeys([resolved["adr_dir"], *extra]))
    return resolved


def check_slug(slug: str) -> str:
    if not SLUG_RE.match(slug or ""):
        raise ConfigError("Feature must be a file stem: letters, digits, hyphen, underscore (max 80).")
    return slug


def artifact_path(root: Path, explicit: str | None, layout: dict, key: str, slug: str | None) -> Path | None:
    if explicit:
        return inside(root, root / explicit)
    if not slug:
        return None
    return inside(root, root / layout[key] / f"{check_slug(slug)}.md")


def harness_doc_dirs(layout: dict) -> list[str]:
    keys = ("specs_dir", "tasks_dir", "tests_dir", "reviews_dir", "security_dir", "changes_dir", "progress_dir")
    return sorted({layout[key] for key in keys if layout.get(key)} | set(layout.get("adr_dirs") or []))


def _excluded(relative: str, doc_dirs: list[str]) -> bool:
    parts = relative.split("/")
    if any(part in FINGERPRINT_SKIP for part in parts[:-1]):
        return True
    # Only Markdown is excluded: a discovered "spec/" folder may hold test code that must keep invalidating proofs.
    if not relative.lower().endswith(".md"):
        return False
    return any(relative.startswith(folder + "/") for folder in doc_dirs)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return "unreadable"
    return digest.hexdigest()


def _git(root: Path, args: list[str]) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.decode("utf-8", errors="replace")


def _git_blob_ids(root: Path, paths: list[str]) -> list[str] | None:
    """Blob ids as `git add` would store them (same end-of-line normalization), for files not yet committed."""
    if not paths:
        return []
    try:
        done = subprocess.run(
            ["git", "-C", str(root), "hash-object", "--stdin-paths"],
            input="\n".join(paths) + "\n", capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    ids = done.stdout.split()
    return ids if done.returncode == 0 and len(ids) == len(paths) else None


def _changed_paths(root: Path) -> list[str]:
    """Modified, added and untracked files from `git status`, relative to the project root."""
    prefix = (_git(root, ["rev-parse", "--show-prefix"]) or "").strip().replace("\\", "/")
    status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=all", "--", "."]) or ""
    records = status.split("\0")
    changed, index = [], 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        code, relative = record[:2], record[3:].replace("\\", "/")
        if code[0] in "RC":
            index += 1
        if prefix:
            if not relative.startswith(prefix):
                continue
            relative = relative[len(prefix):]
        changed.append(relative)
    return changed


def workspace_fingerprint(root: Path, layout: dict | None = None) -> dict:
    """Content of every project file (git blob ids), without harness docs, caches, or .cursor.

    HEAD is not part of the digest: committing the same content keeps the fingerprint, so a review
    recorded before the commit still matches after it.
    """
    layout = layout or resolve_layout(root)
    doc_dirs = harness_doc_dirs(layout)
    head = _git(root, ["rev-parse", "HEAD"])
    entries: list[tuple[str, str]] = []
    changed_count = 0
    inside = (_git(root, ["rev-parse", "--is-inside-work-tree"]) or "").strip() == "true"
    listing = _git(root, ["ls-files", "-s", "-z", "--", "."]) if inside else None
    if listing is not None:
        tracked: dict[str, str] = {}
        for record in listing.split("\0"):
            meta, _, relative = record.partition("\t")
            if relative and len(meta.split()) >= 2:
                tracked[relative.replace("\\", "/")] = meta.split()[1]
        changed = {relative for relative in _changed_paths(root) if not _excluded(relative, doc_dirs)}
        pending = sorted(relative for relative in changed if (root / relative).is_file())
        ids = _git_blob_ids(root, pending)
        hashed = dict(zip(pending, ids)) if ids is not None else {relative: "sha256:" + _hash_file(root / relative) for relative in pending}
        changed_count = len(changed)
        for relative, blob in tracked.items():
            if relative not in changed and not _excluded(relative, doc_dirs):
                entries.append((relative, blob))
        entries += list(hashed.items())
        mode = "git"
        head = head.strip() if head else None
    else:
        mode = "files"
        total = 0
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(name for name in dirnames if name not in FINGERPRINT_SKIP)
            for filename in sorted(filenames):
                path = Path(dirpath) / filename
                relative = path.relative_to(root).as_posix()
                if _excluded(relative, doc_dirs):
                    continue
                if len(entries) >= FINGERPRINT_FILE_LIMIT or total > FINGERPRINT_BYTES_LIMIT * 20:
                    mode = "files-truncated"
                    break
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                total += size
                entries.append((relative, _hash_file(path) if size <= FINGERPRINT_BYTES_LIMIT else f"size:{size}"))
        changed_count = len(entries)
    entries.sort()
    digest = hashlib.sha256(mode.split("-")[0].encode())
    for relative, value in entries:
        digest.update(f"\n{relative}\0{value}".encode())
    return {"mode": mode, "head": head, "changed_files": changed_count, "files": len(entries), "digest": digest.hexdigest()}


TASK_STATUS = {
    "todo": {"todo", "pending", "open", "not started", "a fazer", "pendente"},
    "in_progress": {"in_progress", "in-progress", "in progress", "doing", "wip", "em andamento"},
    "blocked": {"blocked", "bloqueada", "bloqueado"},
    "done": {"done", "completed", "complete", "concluída", "concluida", "feito", "feita"},
    "cancelled": {"cancelled", "canceled", "cancelada", "cancelado", "dropped"},
}


def task_status(value: str) -> str | None:
    lowered = (value or "").strip().lower()
    for name, aliases in TASK_STATUS.items():
        if lowered in aliases:
            return name
    return None


def truthy(value: str, default: bool) -> bool:
    lowered = (value or "").strip().lower()
    if lowered in {"yes", "true", "sim", "y", "1"}:
        return True
    if lowered in {"no", "false", "não", "nao", "n", "0"}:
        return False
    return default


@dataclass
class Bundle:
    root: Path
    layout: dict
    slug: str
    spec: Document | None
    tasks: Document | None
    tests: list[Document]

    def test_blocks(self) -> list[Block]:
        docs = ([self.tasks] if self.tasks else []) + self.tests
        return [block for doc in docs for block in doc.of_kind("TEST")]

    def task_blocks(self) -> list[Block]:
        return self.tasks.of_kind("TASK") if self.tasks else []

    def rel(self, doc: Document | None) -> str | None:
        return doc.path.relative_to(self.root).as_posix() if doc else None


def load_bundle(args, need: tuple[str, ...]) -> Bundle:
    """Spec, tasks, and test docs for one feature. Missing optional docs are skipped; missing required ones raise."""
    root = project_root(args.root)
    layout = resolve_layout(root)
    explicit = {
        "spec": getattr(args, "spec", None),
        "tasks": getattr(args, "tasks", None),
        "tests": getattr(args, "tests", None),
    }
    slug = args.feature
    if slug:
        check_slug(slug)
    else:
        for key in ("tasks", "spec", "tests"):
            if explicit[key]:
                slug = Path(explicit[key]).stem
                break
    if not slug:
        raise ConfigError("Pass --feature <slug> or explicit artifact paths.")
    keys = {"spec": "specs_dir", "tasks": "tasks_dir", "tests": "tests_dir"}
    docs: dict[str, Document | None] = {}
    for name, key in keys.items():
        path = artifact_path(root, explicit[name], layout, key, None if explicit[name] else slug)
        if path is not None and path.is_file():
            docs[name] = load_document(path)
        elif name in need or explicit[name]:
            shown = path.relative_to(root).as_posix() if path is not None else name
            raise ConfigError(f"Required {name} file not found: {shown}")
        else:
            docs[name] = None
    tests = [docs["tests"]] if docs["tests"] else []
    if docs["tasks"] and docs["tests"] and docs["tasks"].path == docs["tests"].path:
        tests = []
    return Bundle(root=root, layout=layout, slug=slug, spec=docs["spec"], tasks=docs["tasks"], tests=tests)


def proofs_file(root: Path, slug: str) -> Path:
    return root / ".cursor" / "agent-system" / "proofs" / f"{check_slug(slug)}.json"


def load_proofs(root: Path, slug: str) -> dict:
    data = load_json_file(proofs_file(root, slug), {})
    if not isinstance(data, dict):
        raise ConfigError("Proof file must contain a JSON object")
    proofs = data.get("proofs") if isinstance(data.get("proofs"), list) else []
    data["by_test"] = {item.get("test"): item for item in proofs if isinstance(item, dict) and item.get("test")}
    return data


class Report:
    """PASS/WARN/FAIL/INFO lines with the shared exit-code contract: 0 ok, 1 gate failed, 2 config error."""

    def __init__(self, title: str, strict: bool = False):
        self.title = title
        self.strict = strict
        self.items: list[dict] = []
        self.data: dict = {}

    def add(self, level: str, code: str, message: str, ref: str = "") -> None:
        self.items.append({"level": level, "code": code, "message": message, "ref": ref})

    def ok(self, code: str, message: str) -> None:
        self.add("PASS", code, message)

    def warn(self, code: str, message: str, ref: str = "") -> None:
        self.add("WARN", code, message, ref)

    def fail(self, code: str, message: str, ref: str = "") -> None:
        self.add("FAIL", code, message, ref)

    def info(self, code: str, message: str) -> None:
        self.add("INFO", code, message)

    def count(self, level: str) -> int:
        return sum(1 for item in self.items if item["level"] == level)

    @property
    def passed(self) -> bool:
        return self.count("FAIL") == 0 and not (self.strict and self.count("WARN"))

    def emit(self, as_json: bool) -> int:
        if as_json:
            payload = {
                "check": self.title,
                "ok": self.passed,
                "strict": self.strict,
                "failures": self.count("FAIL"),
                "warnings": self.count("WARN"),
                "results": self.items,
                **self.data,
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            for item in self.items:
                print(f"[{item['level']}] {item['message']}")
            suffix = " (strict: warnings block)" if self.strict and self.count("WARN") and not self.count("FAIL") else ""
            print(f"{self.title} {'passed' if self.passed else 'failed'}.{suffix}")
        return 0 if self.passed else 1


def config_error(message: str, as_json: bool) -> int:
    text = redact(message, 300)
    if as_json:
        print(json.dumps({"ok": False, "error": text}, ensure_ascii=False))
    else:
        print(f"[ERROR] {text}", file=sys.stderr)
    return 2


def record(root: Path, kind: str, summary: str, result: str, feature: str | None, agent: str, enabled: bool = True) -> None:
    """Append a timeline event for opted-in projects. Telemetry failure never changes the gate result."""
    if not enabled or not opted_in(root):
        return
    try:
        state = load_state(root)
        event = {
            "timestamp": utc_now(),
            "local_time": local_stamp(),
            "session": state.get("session_id") or "",
            "agent": agent,
            "event": kind,
            "task": state.get("active_task"),
            "feature": feature,
            "files": [],
            "summary": redact(summary, 240),
            "result": redact(result, 160),
        }
        append_event(root, event)
        save_state(root, apply_semantic_state(state, event))
    except (OSError, ValueError) as exc:
        print(f"[WARN] timeline not updated: {exc.__class__.__name__}", file=sys.stderr)


def add_common_args(parser) -> None:
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--feature", help="feature slug: the shared file stem under each layout directory")
    parser.add_argument("--json", action="store_true", help="structured output")
    parser.add_argument("--strict", action="store_true", help="warnings also fail the gate")
    parser.add_argument("--no-record", action="store_true", help="do not append a timeline event")
