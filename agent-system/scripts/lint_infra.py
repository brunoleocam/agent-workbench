"""Infrastructure lint for Dockerfiles, Docker Compose files, and Kubernetes manifests.

Reports P0 (blocking), P1, and P2 findings with file, line, rule, severity, message, and suggestion.
Heuristic: Dockerfile instructions and YAML read line by line, without a YAML parser. Block and compact
lists, trailing comments, and one-line flow mappings ({a: b}) are read; anchors and aliases, multi-line flow
collections, and templates ({{ }}) may be read only in part. Standard library only.

A secret value is never printed: a P0-SECRET-LITERAL finding names the key and the line.

Exit codes: 0 without P0 findings, 1 with at least one P0, 2 on a usage error or an unreadable file.
Suppress one rule on a line, or on the line after the comment:
    # infra-lint-disable P0-DOCKER-SOCKET -- <reason>
A suppression without "-- <reason>" is ignored and reported as P1-SUPPRESSION-NO-REASON.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SKIP_DIRS = {"node_modules", "dist", "build", ".git", "vendor", ".venv"}
HOOK_MAX_BYTES = 512 * 1024  # the hook skips larger files to stay inside its timeout; the CLI reads every file
DB_PORTS = {5432, 3306, 1433, 27017, 6379, 11211, 9200, 5672, 9092}
SECRET_WORDS = ("PASSWORD", "PASSWD", "SECRET", "TOKEN", "API_KEY", "APIKEY", "PRIVATE_KEY", "ACCESS_KEY")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet"}
POD_KINDS = WORKLOADS | {"Pod", "ReplicaSet", "Job", "CronJob"}
SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}

COMPOSE_NAME = re.compile(r"^(?:docker-)?compose[\w.-]*\.ya?ml$", re.IGNORECASE)
SUPPRESS = re.compile(r"infra-lint-disable\b(.*)$", re.IGNORECASE)
RULE_ID = re.compile(r"P[012]-[A-Z-]+")
INLINE_COMMENT = re.compile(r"\s+#.*$")
PIPE_TO_SHELL = re.compile(r"\b(?:curl|wget)\b[^|;&]*\|\s*(?:sudo\s+)?(?:ba|z|da|k)?sh\b")
BUILD_STEP = re.compile(r"\bnpm\s+(?:install|ci)\b|\byarn\s+install\b|\bgo\s+build\b|\bmvn\b|\bgradle\b|\bcargo\s+build\b")
PIP_INSTALL = re.compile(r"\bpip3?\s+install\b")
YAML_KEY = re.compile(r"^(\s*)(-\s+)?([\w.-]+)\s*:(?:\s+(.*)|\s*)$")
NUMBER_OR_DURATION = re.compile(r"^\d+(?:\.\d+)?(?:ms|s|m|h|d|w)?$", re.IGNORECASE)


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    severity: str
    message: str
    suggestion: str


class Source:
    """One file's lines and its findings."""

    def __init__(self, display: str, path: Path, text: str) -> None:
        self.display = display
        self.path = path
        self.text = text
        self.lines = text.splitlines()
        self.findings: list[Finding] = []

    def add(self, line: int, rule: str, message: str, suggestion: str) -> None:
        self.findings.append(Finding(self.display, line, rule, rule[:2], message, suggestion))


# --- YAML helpers -----------------------------------------------------------------------------


def unquote(value: str | None) -> str:
    """A scalar without quotes or a trailing comment; "" for an empty value or a comment alone."""
    value = (value or "").strip()
    if not value or value.startswith("#"):
        return ""
    if value[0] in "'\"":
        end = value.find(value[0], 1)
        return value[1:end] if end > 0 else value[1:]
    return INLINE_COMMENT.sub("", value).strip()


def flow_pairs(value: str) -> list[tuple[str, str]]:
    """The key/value pairs of a one-line flow mapping such as {name: X, value: Y}."""
    value = unquote(value) if not value.strip().startswith("{") else INLINE_COMMENT.sub("", value.strip())
    if not (value.startswith("{") and value.endswith("}")):
        return []
    pairs = []
    for part in value[1:-1].split(","):
        key, sep, item = part.partition(":")
        if sep and key.strip():
            pairs.append((key.strip().strip("'\""), unquote(item)))
    return pairs


def indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def meaningful(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith("#")


def is_item(line: str) -> bool:
    stripped = line.lstrip(" ")
    return stripped == "-" or stripped.startswith("- ")


def children(lines: list[tuple[int, str]], start: int) -> list[tuple[int, str]]:
    """The lines nested under lines[start]: deeper lines, plus a compact list ("- " at the key's own indent)."""
    base = indent(lines[start][1])
    match = YAML_KEY.match(lines[start][1])
    compact = bool(match) and not unquote(match.group(4))
    out = []
    for number, line in lines[start + 1:]:
        if not meaningful(line):
            continue
        level = indent(line)
        if level > base or (compact and level == base and is_item(line)):
            out.append((number, line))
            continue
        break
    return out


def yaml_keys(block: list[tuple[int, str]]) -> dict[str, tuple[int, str, int]]:
    """Keys at the block's first indentation: name -> (line, raw value, position in block)."""
    if not block:
        return {}
    key_indent = indent(block[0][1])
    keys: dict[str, tuple[int, str, int]] = {}
    for position, (number, line) in enumerate(block):
        match = YAML_KEY.match(line)
        if indent(line) == key_indent and match and not match.group(2):
            keys.setdefault(match.group(3), (number, match.group(4) or "", position))
    return keys


def list_items(lines: list[tuple[int, str]]) -> list[tuple[int, dict[str, str], str]]:
    """Each list item with its direct keys: (line, {key: value}, scalar text for an item without keys)."""
    items: list[tuple[int, dict[str, str], str]] = []
    current: tuple[int, dict[str, str], str] | None = None
    key_column = -1
    item_indent = next((indent(line) for _, line in lines if meaningful(line) and is_item(line)), -1)
    for number, line in lines:
        if not meaningful(line):
            continue
        if is_item(line) and indent(line) == item_indent:
            if current:
                items.append(current)
            body = line.lstrip(" ")[1:].strip()
            key_column = indent(line) + (len(line.lstrip(" ")) - len(line.lstrip(" ")[1:].lstrip(" ")))
            fields: dict[str, str] = {}
            scalar = ""
            if body.startswith("{"):
                fields.update(flow_pairs(body))
            else:
                match = YAML_KEY.match(body)
                if match and not body.startswith(("'", '"')):
                    fields[match.group(3)] = unquote(match.group(4))
                else:
                    scalar = unquote(body)
            current = (number, fields, scalar)
        elif current is not None and indent(line) == key_column:
            match = YAML_KEY.match(line)
            if match and not match.group(2):
                current[1].setdefault(match.group(3), unquote(match.group(4)))
    if current:
        items.append(current)
    return items


# --- shared checks ----------------------------------------------------------------------------


def is_secret_key(key: str) -> bool:
    upper = key.upper()
    return any(word in upper for word in SECRET_WORDS)


def is_literal_secret(key: str, value: str) -> bool:
    value = (value or "").strip()
    if not value or value.startswith("$") or value.lower() in ("null", "~"):
        return False
    if NUMBER_OR_DURATION.match(value):
        return False
    if key.upper().endswith("_FILE") and (value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value)):
        return False
    return True


def check_secret(src: Source, line: int, key: str, value: str, where: str) -> None:
    if is_secret_key(key) and is_literal_secret(key, value):
        src.add(
            line, "P0-SECRET-LITERAL",
            f"{key} has a literal value in {where}; the value is not shown.",
            "Inject it at runtime: an env_file outside the repository, the platform's secret store, Docker secrets (a _FILE variable), or a Kubernetes Secret (secretKeyRef). Rotate it if it was ever committed.",
        )


def image_problem(ref: str) -> str:
    """Why an image reference is not pinned, or "" when it is pinned or cannot be judged."""
    ref = unquote(ref)
    if not ref or "$" in ref or "{{" in ref or "@sha256:" in ref:
        return ""
    name = ref.rsplit("/", 1)[-1]
    if ":" not in name:
        return f"Image {ref} has no tag."
    if name.split(":", 1)[1].lower() == "latest":
        return f"Image {ref} uses the latest tag."
    return ""


def check_image(src: Source, line: int, ref: str) -> None:
    problem = image_problem(ref)
    if problem:
        src.add(line, "P0-UNPINNED-IMAGE", problem, "Pin a version tag (node:20.11-alpine) or a digest (@sha256:...), so every build runs the same image.")


def check_docker_socket(src: Source) -> None:
    for number, line in enumerate(src.lines, start=1):
        if "/var/run/docker.sock" in line and not line.strip().startswith("#"):
            src.add(number, "P0-DOCKER-SOCKET", "The Docker socket is mounted; the container can control the host.", "Remove the mount. If a CI agent really needs Docker, isolate it on its own host and suppress with a reason.")


def is_root_user(value: str) -> bool:
    return value.split(":", 1)[0].strip().lower() in ("root", "0")


# --- Dockerfile -------------------------------------------------------------------------------


def is_dockerfile(name: str) -> bool:
    lower = name.lower()
    return lower == "dockerfile" or lower.startswith("dockerfile.") or lower.endswith(".dockerfile")


def instructions(src: Source) -> list[tuple[int, str, str]]:
    """(line, INSTRUCTION, arguments) with continuation lines joined and comments removed."""
    out = []
    parts: list[str] = []
    start = 0
    for number, line in enumerate(src.lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not parts:
            start = number
        if stripped.endswith("\\"):
            parts.append(stripped[:-1].strip())
            continue
        parts.append(stripped)
        word, _, rest = " ".join(item for item in parts if item).partition(" ")
        out.append((start, word.upper(), rest.strip()))
        parts = []
    if parts:
        word, _, rest = " ".join(item for item in parts if item).partition(" ")
        out.append((start, word.upper(), rest.strip()))
    return out


def split_args(rest: str) -> list[str]:
    try:
        return shlex.split(rest, posix=True)
    except ValueError:
        return rest.split()


def compose_services(src_lines: list[str]) -> list[tuple[int, str, list[tuple[int, str]]]]:
    """(line, name, block) for each service under the top-level services: key."""
    lines = list(enumerate(src_lines, start=1))
    start = next((index for index, (_, line) in enumerate(lines) if re.match(r"^services:\s*(?:#.*)?$", line)), None)
    if start is None:
        return []
    body = children(lines, start)
    if not body:
        return []
    service_indent = indent(body[0][1])
    services = []
    for number, line in body:
        match = YAML_KEY.match(line)
        if indent(line) == service_indent and match and not match.group(2):
            index = next(i for i, item in enumerate(lines) if item[0] == number)
            services.append((number, match.group(3), children(lines, index)))
    return services


def built_dockerfile(folder: Path, block: list[tuple[int, str]]) -> Path | None:
    """The Dockerfile a Compose service builds, or None when it has no build key."""
    keys = yaml_keys(block)
    if "build" not in keys:
        return None
    inline = unquote(keys["build"][1])
    context, dockerfile = inline or ".", "Dockerfile"
    if not inline:
        nested = yaml_keys(children(block, keys["build"][2]))
        context = unquote(nested.get("context", (0, ".", 0))[1]) or "."
        dockerfile = unquote(nested.get("dockerfile", (0, "Dockerfile", 0))[1]) or "Dockerfile"
    return (folder / context / dockerfile).resolve()


def compose_healthcheck_for(dockerfile: Path) -> bool:
    """True when a Compose file in the Dockerfile's folder builds it in a service that has a healthcheck."""
    folder = dockerfile.parent
    target = dockerfile.resolve()
    for item in sorted(folder.iterdir()) if folder.is_dir() else []:
        if not (item.is_file() and COMPOSE_NAME.match(item.name)):
            continue
        try:
            text = item.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for _, _, block in compose_services(text.splitlines()):
            if built_dockerfile(folder, block) == target and "healthcheck" in yaml_keys(block):
                return True
    return False


def lint_dockerfile(src: Source) -> None:
    stages: list[dict] = []
    by_alias: dict[str, dict] = {}
    dockerignore_reported = False
    pip_with_gcc = "gcc" in src.text and bool(PIP_INSTALL.search(src.text))
    build_steps: list[int] = []
    for line, word, rest in instructions(src):
        args = [item for item in split_args(rest) if not item.startswith("--")]
        if word == "FROM":
            image = args[0] if args else ""
            parent = by_alias.get(image.lower())
            stage = {
                "line": line,
                "user": parent["user"] if parent else None,
                "user_line": parent["user_line"] if parent else line,
                "healthcheck": parent["healthcheck"] if parent else False,
            }
            stages.append(stage)
            if image and not parent and image.lower() != "scratch":
                check_image(src, line, image)
            if len(args) >= 3 and args[1].lower() == "as":
                by_alias[args[2].lower()] = stage
        elif word in ("ENV", "ARG"):
            tokens = split_args(rest)
            if not tokens:
                continue
            if "=" in tokens[0]:
                for token in tokens:
                    key, sep, value = token.partition("=")
                    if sep:
                        check_secret(src, line, key, value, f"Dockerfile {word}")
            elif word == "ENV" and len(tokens) >= 2:
                check_secret(src, line, tokens[0], " ".join(tokens[1:]), "Dockerfile ENV")
        elif not stages:
            continue
        elif word == "USER":
            stages[-1]["user"] = args[0] if args else ""
            stages[-1]["user_line"] = line
        elif word == "HEALTHCHECK":
            stages[-1]["healthcheck"] = rest.strip().upper() != "NONE"
        elif word == "RUN":
            if PIPE_TO_SHELL.search(rest):
                src.add(line, "P1-PIPE-TO-SHELL", "RUN downloads a script and runs it in one step, unverified.", "Download to a file, check its checksum or signature, then run it; or install from a package manager.")
            if BUILD_STEP.search(rest) or (pip_with_gcc and PIP_INSTALL.search(rest)):
                build_steps.append(line)
        elif word in ("COPY", "ADD"):
            sources = args[:-1]
            if word == "ADD" and any(item.startswith(("http://", "https://")) for item in sources):
                src.add(line, "P1-ADD-REMOTE", "ADD fetches a remote URL without verification.", "Download with RUN and a checksum check, or use ADD --checksum=sha256:...")
            if not dockerignore_reported and any(item in (".", "./") for item in sources):
                folder = src.path.parent
                if not (folder / ".dockerignore").is_file() and not (folder / f"{src.path.name}.dockerignore").is_file():
                    src.add(line, "P1-NO-DOCKERIGNORE", f"{word} . copies the whole context and there is no .dockerignore.", "Add a .dockerignore that excludes .git, .env, node_modules, and build output.")
                    dockerignore_reported = True
        elif word in ("CMD", "ENTRYPOINT"):
            if rest and not rest.lstrip().startswith("["):
                src.add(line, "P2-SHELL-FORM-CMD", f"{word} in shell form runs under /bin/sh, so the process does not receive the stop signal.", f'Use the exec form: {word} ["executable", "arg"].')
    if not stages:
        return
    final = stages[-1]
    if final["user"] is None:
        src.add(final["line"], "P0-ROOT-USER", "The final stage has no USER, so the container runs as root.", "Add USER with a non-root user (for example USER 1000) at the end of the final stage.")
    elif is_root_user(final["user"]):
        src.add(final["user_line"], "P0-ROOT-USER", f"The final stage runs as {final['user']}, which is root.", "Switch to a non-root user (for example USER 1000) in the final stage.")
    if not final["healthcheck"] and not compose_healthcheck_for(src.path):
        src.add(final["line"], "P1-NO-HEALTHCHECK", "The final stage has no HEALTHCHECK, and no Compose service that builds this Dockerfile has a healthcheck.", "Add HEALTHCHECK to the final stage, or a healthcheck to the service in docker-compose.yml.")
    if len(stages) == 1 and build_steps:
        src.add(build_steps[0], "P2-SINGLE-STAGE", "A single-stage image installs build dependencies or compiles, so build tools ship to production.", "Build in a first stage and copy only the output into a smaller final stage.")


# --- Docker Compose ---------------------------------------------------------------------------


def split_short_port(short: str) -> tuple[str, list[str]]:
    """(host_ip, [published, target]) from a short-syntax port such as 127.0.0.1:5432:5432 or [::1]:5432:5432."""
    short = short.strip()
    host_ip = ""
    if short.startswith("["):
        end = short.find("]")
        host_ip, short = short[1:end], short[end + 1:].lstrip(":")
        return host_ip, short.split(":")
    parts = short.split(":")
    if len(parts) >= 3:
        host_ip = ":".join(parts[:-2])
        parts = parts[-2:]
    return host_ip, parts


def port_entries(value: str, nested: list[tuple[int, str]], line: int) -> list[tuple[int, str, list[str]]]:
    """(line, host_ip, ports) for each published port, short or long syntax, block or flow list."""
    entries = []
    value = unquote(value) if not value.strip().startswith("[") else INLINE_COMMENT.sub("", value.strip())
    if value.startswith("["):
        for raw in value.strip("[]").split(","):
            if raw.strip():
                host_ip, ports = split_short_port(unquote(raw))
                entries.append((line, host_ip, ports))
        return entries
    for number, fields, scalar in list_items(nested):
        if fields:
            entries.append((number, fields.get("host_ip", ""), [fields.get("target", ""), fields.get("published", "")]))
        elif scalar:
            host_ip, ports = split_short_port(scalar)
            entries.append((number, host_ip, ports))
    return entries


def public_db_port(host_ip: str, ports: list[str]) -> int | None:
    if host_ip.strip("[]") in LOOPBACK:
        return None
    for port in ports:
        number = port.split("/")[0].strip().strip("'\"")
        if number.isdigit() and int(number) in DB_PORTS:
            return int(number)
    return None


def lint_compose(src: Source) -> None:
    for number, name, block in compose_services(src.lines):
        if not block:
            continue
        keys = yaml_keys(block)

        def nested(key: str) -> list[tuple[int, str]]:
            return children(block, keys[key][2]) if key in keys else []

        if "image" in keys and "build" not in keys:
            check_image(src, keys["image"][0], keys["image"][1])
        if "privileged" in keys and unquote(keys["privileged"][1]).lower() == "true":
            src.add(keys["privileged"][0], "P0-PRIVILEGED", f"Service {name} runs privileged.", "Remove privileged: true; grant only the capabilities it needs with cap_add.")
        if "environment" in keys:
            where = f"the environment of service {name}"
            inline = INLINE_COMMENT.sub("", keys["environment"][1].strip())
            for key, value in flow_pairs(inline):
                check_secret(src, keys["environment"][0], key, value, where)
            if inline.startswith("[") and inline.endswith("]"):
                for raw in inline[1:-1].split(","):
                    key, sep, value = unquote(raw).partition("=")
                    if sep:
                        check_secret(src, keys["environment"][0], key.strip(), value, where)
            for line_number, line in nested("environment"):
                stripped = line.strip()
                if is_item(line):
                    key, sep, value = unquote(stripped[1:]).partition("=")
                    if sep:
                        check_secret(src, line_number, key.strip(), value, where)
                else:
                    match = YAML_KEY.match(stripped)
                    if match:
                        check_secret(src, line_number, match.group(3), unquote(match.group(4)), where)
        if "ports" in keys:
            for line_number, host_ip, ports in port_entries(keys["ports"][1], nested("ports"), keys["ports"][0]):
                port = public_db_port(host_ip, ports)
                if port:
                    src.add(line_number, "P0-DB-PORT-PUBLIC", f"Port {port} of service {name} is published on all interfaces.", "Do not publish it; other services reach it on the Compose network. For local access bind it to 127.0.0.1:")
        deploy = "\n".join(line for _, line in nested("deploy"))
        if "restart" not in keys and "restart_policy:" not in deploy:
            src.add(number, "P1-NO-RESTART", f"Service {name} has no restart policy.", "Add restart: unless-stopped (or deploy.restart_policy).")
        if "mem_limit" not in keys and not ("resources:" in deploy and "limits:" in deploy):
            src.add(number, "P1-NO-RESOURCE-LIMITS", f"Service {name} has no memory or CPU limit.", "Add deploy.resources.limits (memory, cpus) or mem_limit.")
        if "logging" not in keys:
            src.add(number, "P2-NO-LOG-ROTATION", f"Service {name} has no logging configuration, so logs can fill the disk.", "Add logging with driver json-file or local and options max-size and max-file.")
    check_docker_socket(src)


# --- Kubernetes -------------------------------------------------------------------------------


def is_manifest(text: str) -> bool:
    return bool(re.search(r"(?m)^apiVersion:\s*\S", text)) and bool(re.search(r"(?m)^kind:\s*\S", text))


def documents(src: Source) -> list[list[tuple[int, str]]]:
    docs: list[list[tuple[int, str]]] = [[]]
    for number, line in enumerate(src.lines, start=1):
        if re.match(r"^---", line):
            docs.append([])
        else:
            docs[-1].append((number, line))
    return [doc for doc in docs if any(meaningful(line) for _, line in doc)]


def container_blocks(doc: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    blocks = []
    for index, (_, line) in enumerate(doc):
        if not re.match(r"^\s*-?\s*containers:\s*(?:#.*)?$", line):
            continue
        nested = children(doc, index)
        if not nested:
            continue
        item_indent = indent(nested[0][1])
        current: list[tuple[int, str]] = []
        for number, text in nested:
            if indent(text) == item_indent and is_item(text):
                if current:
                    blocks.append(current)
                current = [(number, text)]
            elif current:
                current.append((number, text))
        if current:
            blocks.append(current)
    return blocks


def check_security_pair(src: Source, number: int, key: str, value: str) -> None:
    value = value.lower()
    if key == "runAsUser" and value == "0":
        src.add(number, "P0-ROOT-USER", "runAsUser: 0 runs the container as root.", "Set runAsNonRoot: true and a non-zero runAsUser.")
    elif key == "runAsNonRoot" and value == "false":
        src.add(number, "P0-ROOT-USER", "runAsNonRoot: false allows the container to run as root.", "Set runAsNonRoot: true and a non-zero runAsUser.")
    elif key == "privileged" and value == "true":
        src.add(number, "P0-PRIVILEGED", "The container runs privileged.", "Remove privileged: true and add only the capabilities it needs.")
    elif key == "allowPrivilegeEscalation" and value == "true":
        src.add(number, "P0-PRIVILEGED", "allowPrivilegeEscalation: true lets the process gain more privileges.", "Set allowPrivilegeEscalation: false.")


def lint_manifest(src: Source) -> None:
    for doc in documents(src):
        kind = next((match.group(1) for _, line in doc if (match := re.match(r"^kind:\s*(\S+)", line))), "")
        service_type = next((unquote(m.group(1)) for _, text in doc if (m := re.match(r"^\s+type:\s*(\S+)", text))), "ClusterIP")
        for number, line in doc:
            if not meaningful(line):
                continue
            body = line.lstrip(" ")[1:].strip() if is_item(line) else line.strip()
            pairs = flow_pairs(body) if body.startswith("{") else []
            match = YAML_KEY.match(line)
            if match:
                key, raw = match.group(3), match.group(4) or ""
                pairs = [(key, unquote(raw))] + [(f"{inner}", value) for inner, value in flow_pairs(raw)]
            for key, value in pairs:
                if key == "image":
                    check_image(src, number, value)
                check_security_pair(src, number, key, value)
                if kind == "Service" and key in ("port", "targetPort", "nodePort") and value.isdigit() and int(value) in DB_PORTS and service_type in ("LoadBalancer", "NodePort"):
                    src.add(number, "P0-DB-PORT-PUBLIC", f"Service of type {service_type} exposes port {value} outside the cluster.", "Use type ClusterIP for databases, caches, and brokers.")
        for env_list in env_lists(doc):
            for number, fields, _ in list_items(env_list):
                if "name" in fields and "value" in fields:
                    check_secret(src, number, fields["name"], fields["value"], "a Kubernetes env value")
        if kind in POD_KINDS:
            for block in container_blocks(doc):
                text = "\n".join(line for _, line in block)
                first = block[0][0]
                if kind in WORKLOADS and ("readinessProbe:" not in text or "livenessProbe:" not in text):
                    src.add(first, "P1-NO-PROBE", f"A container of this {kind} has no readinessProbe or no livenessProbe.", "Add both probes, so traffic waits for readiness and a stuck process is restarted.")
                if "requests:" not in text or "limits:" not in text:
                    src.add(first, "P1-NO-RESOURCE-LIMITS", f"A container of this {kind} has no resources.requests or no resources.limits.", "Set requests (for scheduling) and limits (at least memory).")
    check_docker_socket(src)


def env_lists(doc: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """The lines of each env: list of the document, one list per key, so each keeps its own indentation."""
    return [children(doc, index) for index, (_, line) in enumerate(doc) if re.match(r"^\s*-?\s*env:\s*(?:#.*)?$", line)]


# --- driver -----------------------------------------------------------------------------------


def kind_of(path: Path, text: str | None = None) -> str:
    """'dockerfile', 'compose', 'manifest', or '' for a file the lint does not read."""
    if is_dockerfile(path.name):
        return "dockerfile"
    if COMPOSE_NAME.match(path.name):
        return "compose"
    if path.suffix.lower() in (".yml", ".yaml"):
        if text is None:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
        return "manifest" if is_manifest(text) else ""
    return ""


def is_candidate(path: Path) -> bool:
    return is_dockerfile(path.name) or path.suffix.lower() in (".yml", ".yaml")


def apply_suppressions(src: Source) -> None:
    allowed: dict[int, set[str]] = {}
    for number, line in enumerate(src.lines, start=1):
        match = SUPPRESS.search(line)
        if not match:
            continue
        rules_part, sep, reason = match.group(1).partition("--")
        ids = set(RULE_ID.findall(rules_part.upper()))
        if not sep or not reason.strip():
            src.findings.append(Finding(src.display, number, "P1-SUPPRESSION-NO-REASON", "P1", "infra-lint-disable without '-- <reason>' is ignored.", "Write the reason after --, for example: # infra-lint-disable P0-DOCKER-SOCKET -- isolated CI runner."))
            continue
        allowed.setdefault(number, set()).update(ids)
        allowed.setdefault(number + 1, set()).update(ids)
    src.findings = [item for item in src.findings if item.rule not in allowed.get(item.line, set())]


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(paths: list[Path]):
    for path in paths:
        if path.is_file():
            if is_candidate(path):
                yield path
            continue
        for folder, dirs, files in os.walk(path):
            dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
            for name in sorted(files):
                candidate = Path(folder) / name
                if is_candidate(candidate):
                    yield candidate


def lint_paths(paths: list[Path], notes: list[str] | None = None, max_bytes: int | None = None) -> list[Finding]:
    """Lint every infrastructure file under paths. Files not read go to notes as "skipped (...)" or "unreadable (...)".

    max_bytes is for the hook only: the CLI reads files of any size, so a P0 in a large file is never missed.
    """
    notes = notes if notes is not None else []
    findings: list[Finding] = []
    for path in iter_files(paths):
        try:
            if max_bytes is not None and path.stat().st_size > max_bytes:
                notes.append(f"{display(path)}: skipped (larger than {max_bytes // 1024} KB)")
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as error:
            notes.append(f"{display(path)}: unreadable ({error.__class__.__name__})")
            continue
        kind = kind_of(path, text)
        if not kind:
            continue
        src = Source(display(path), path, text)
        {"dockerfile": lint_dockerfile, "compose": lint_compose, "manifest": lint_manifest}[kind](src)
        apply_suppressions(src)
        findings += src.findings
    unique = {(item.file, item.line, item.rule, item.message): item for item in findings}
    return sorted(unique.values(), key=lambda item: (item.file, item.line, item.rule))


def by_severity(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda item: (SEVERITY_ORDER.get(item.severity, 3), item.file, item.line, item.rule))


def summary(findings: list[Finding]) -> dict[str, int]:
    return {level: sum(1 for item in findings if item.severity == level) for level in ("P0", "P1", "P2")}


def render_text(findings: list[Finding]) -> str:
    lines = [f"{item.file}:{item.line}: {item.severity} {item.rule} {item.message} Fix: {item.suggestion}" for item in findings]
    counts = summary(findings)
    lines.append(f"infra lint: {counts['P0']} P0, {counts['P1']} P1, {counts['P2']} P2")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Infrastructure lint for Dockerfiles, Compose files, and Kubernetes manifests.")
    parser.add_argument("paths", nargs="*", default=["."], help="files or folders (default: current folder)")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    paths = [Path(item) for item in args.paths]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        print(f"error: not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    notes: list[str] = []
    findings = lint_paths(paths, notes)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    for note in notes:
        print(note, file=sys.stderr)
    if args.format == "json":
        print(json.dumps({"findings": [asdict(item) for item in findings], "summary": summary(findings), "notes": notes}, ensure_ascii=True))
    else:
        print(render_text(findings))
    if summary(findings)["P0"]:
        return 1
    return 2 if notes else 0


if __name__ == "__main__":
    raise SystemExit(main())
