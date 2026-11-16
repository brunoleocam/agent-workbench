"""Infrastructure lint: Dockerfile, Compose, and Kubernetes rules, exit codes, output, suppression, and the hook."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from support import PYTHON, SCRIPTS, opt_in, run, write  # noqa: E402

CLEAN_DOCKERFILE = """FROM node:20.11-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM build AS test
RUN npm test

FROM gcr.io/distroless/nodejs20@sha256:0f3c4e5a6b7c8d9e0f1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f70
COPY --from=build /app/dist /app
USER 1000
HEALTHCHECK CMD ["node", "/app/health.js"]
CMD ["node", "/app/server.js"]
"""

CLEAN_COMPOSE = """services:
  app:
    build: .
    restart: unless-stopped
    environment:
      DB_PASSWORD: ${DB_PASSWORD}
      LOG_LEVEL: info
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "node", "/app/health.js"]
    mem_limit: 512m
    logging:
      driver: json-file
      options:
        max-size: "10m"
  db:
    image: postgres:16.3
    restart: unless-stopped
    ports: ["127.0.0.1:5432:5432"]
    env_file: .env
    deploy:
      resources:
        limits:
          memory: 1g
    logging:
      driver: json-file
"""

CLEAN_K8S = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
        - name: api
          image: registry.example.com/api:1.4.2
          env:
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db
                  key: password
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
          resources:
            requests:
              cpu: 100m
            limits:
              memory: 256Mi
---
apiVersion: v1
kind: Service
metadata:
  name: db
spec:
  type: ClusterIP
  ports:
    - port: 5432
"""

P0_CASES = {
    "P0-UNPINNED-IMAGE": [
        ("Dockerfile", "FROM node:latest\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"node\"]\n"),
        ("Dockerfile", "FROM python\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"python\"]\n"),
        ("docker-compose.yml", "services:\n  cache:\n    image: redis\n    restart: always\n"),
        ("k8s/deploy.yaml", "apiVersion: v1\nkind: Pod\nmetadata:\n  name: x\nspec:\n  containers:\n    - name: x\n      image: nginx:latest\n"),
    ],
    "P0-ROOT-USER": [
        ("Dockerfile", "FROM node:20.11\nHEALTHCHECK CMD true\nCMD [\"node\"]\n"),
        ("Dockerfile", "FROM node:20.11\nUSER root\nHEALTHCHECK CMD true\nCMD [\"node\"]\n"),
        ("pod.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  securityContext:\n    runAsUser: 0\n  containers:\n    - name: x\n      image: nginx:1.27\n"),
    ],
    "P0-PRIVILEGED": [
        ("compose.yaml", "services:\n  app:\n    image: app:1.0\n    privileged: true\n"),
        ("pod.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n    - name: x\n      image: nginx:1.27\n      securityContext:\n        allowPrivilegeEscalation: true\n"),
    ],
    "P0-SECRET-LITERAL": [
        ("Dockerfile", "FROM node:20.11\nENV API_TOKEN=abc123\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"node\"]\n"),
        ("docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    environment:\n      - DB_PASSWD=hunter2\n"),
        ("deploy.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n    - name: x\n      image: nginx:1.27\n      env:\n        - name: STRIPE_APIKEY\n          value: sk_live_123\n"),
    ],
    "P0-DB-PORT-PUBLIC": [
        ("docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n    ports:\n      - \"5432:5432\"\n"),
        ("docker-compose.yml", "services:\n  cache:\n    image: redis:7.2\n    ports: [\"0.0.0.0:6379:6379\"]\n"),
        ("svc.yaml", "apiVersion: v1\nkind: Service\nmetadata:\n  name: db\nspec:\n  type: LoadBalancer\n  ports:\n    - port: 5432\n"),
    ],
    "P0-DOCKER-SOCKET": [
        ("docker-compose.yml", "services:\n  agent:\n    image: agent:2.1\n    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n"),
    ],
}

P1_P2_CASES = {
    "P1-NO-HEALTHCHECK": ("Dockerfile", "FROM node:20.11\nUSER 1000\nCMD [\"node\"]\n"),
    "P1-NO-PROBE": ("deploy.yaml", "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - name: x\n          image: nginx:1.27\n          resources:\n            requests:\n              cpu: 100m\n            limits:\n              memory: 128Mi\n"),
    "P1-NO-RESOURCE-LIMITS": ("docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    restart: always\n    logging:\n      driver: json-file\n"),
    "P1-NO-RESTART": ("docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    mem_limit: 256m\n    logging:\n      driver: json-file\n"),
    "P1-PIPE-TO-SHELL": ("Dockerfile", "FROM debian:12.5\nRUN curl -fsSL https://example.com/install.sh | sh\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"app\"]\n"),
    "P1-NO-DOCKERIGNORE": ("Dockerfile", "FROM node:20.11\nCOPY . .\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"node\"]\n"),
    "P1-ADD-REMOTE": ("Dockerfile", "FROM debian:12.5\nADD https://example.com/tool.tar.gz /opt/\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"tool\"]\n"),
    "P2-SINGLE-STAGE": ("Dockerfile", "FROM node:20.11\nRUN npm ci\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"node\"]\n"),
    "P2-NO-LOG-ROTATION": ("docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    restart: always\n    mem_limit: 256m\n"),
    "P2-SHELL-FORM-CMD": ("Dockerfile", "FROM node:20.11\nUSER 1000\nHEALTHCHECK CMD true\nCMD npm start\n"),
}


def lint(root: Path, *args: str):
    done = run("lint_infra.py", [*args, "--format", "json"], cwd=root)
    report = json.loads(done.stdout) if done.stdout.strip().startswith("{") else {}
    return done.returncode, report, done


def rules(report: dict) -> set[str]:
    return {item["rule"] for item in report.get("findings", [])}


def test_infra_lint_flags_each_p0() -> None:
    for rule, cases in P0_CASES.items():
        for relative, text in cases:
            with tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                write(root, relative, text)
                code, report, done = lint(root, relative)
                assert code == 1, (rule, relative, code, done.stdout, done.stderr)
                assert rule in rules(report), (rule, relative, report)
                finding = next(item for item in report["findings"] if item["rule"] == rule)
                assert set(finding) == {"file", "line", "rule", "severity", "message", "suggestion"}, finding
                assert finding["severity"] == "P0" and finding["line"] >= 1 and finding["message"] and finding["suggestion"]


def test_infra_lint_p1_and_p2_only_warn() -> None:
    for rule, (relative, text) in P1_P2_CASES.items():
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            code, report, done = lint(root, relative)
            assert rule in rules(report), (rule, report, done.stderr)
            assert code == 0, (rule, code, report)


def test_infra_lint_compose_and_k8s_warnings_together() -> None:
    """AC-020: a Compose without restart and a manifest without resources, no P0."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    mem_limit: 256m\n    logging:\n      driver: json-file\n")
        write(root, "k8s/job.yaml", "apiVersion: batch/v1\nkind: Job\nspec:\n  template:\n    spec:\n      containers:\n        - name: x\n          image: busybox:1.36\n")
        code, report, _ = lint(root, ".")
        assert code == 0, report
        assert {"P1-NO-RESTART", "P1-NO-RESOURCE-LIMITS"} <= rules(report), report


def test_infra_lint_clean_fixture_has_no_findings() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "Dockerfile", CLEAN_DOCKERFILE)
        write(root, ".dockerignore", "node_modules\n")
        write(root, "docker-compose.yml", CLEAN_COMPOSE)
        write(root, "k8s/api.yaml", CLEAN_K8S)
        code, report, done = lint(root, ".")
        assert code == 0 and report["findings"] == [], (report, done.stderr)


def test_infra_lint_not_p0_cases() -> None:
    """AC-019: stage alias, digest, numeric USER, interpolated secret, loopback port."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "Dockerfile", CLEAN_DOCKERFILE)
        write(root, "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n    environment:\n      DB_PASSWORD: ${DB_PASSWORD}\n      API_KEY: $API_KEY\n      EMPTY_SECRET: \"\"\n    ports: [\"127.0.0.1:5432:5432\"]\n")
        code, report, _ = lint(root, ".")
        assert code == 0, report
        assert not [item for item in report["findings"] if item["severity"] == "P0"], report


def test_infra_lint_never_prints_the_secret() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    environment:\n      API_KEY: sk-test-abc123\n")
        code, report, done = lint(root, "docker-compose.yml")
        assert code == 1
        finding = next(item for item in report["findings"] if item["rule"] == "P0-SECRET-LITERAL")
        assert "API_KEY" in finding["message"] and finding["line"] == 5
        text = run("lint_infra.py", ["docker-compose.yml"], cwd=root)
        for output in (done.stdout + done.stderr, text.stdout + text.stderr):
            assert "sk-test-abc123" not in output, output
        assert "API_KEY" in text.stdout


def test_infra_lint_skips_vendor_folders_and_non_infra_yaml() -> None:
    """AC-017: only the root Dockerfile is reported."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "Dockerfile", "FROM node:latest\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"node\"]\n")
        write(root, "node_modules/x/Dockerfile", "FROM node:latest\n")
        write(root, ".github/workflows/ci.yml", "jobs:\n  test:\n    container:\n      image: node:latest\n")
        write(root, "config/app.yaml", "image: whatever:latest\nprivileged: true\n")
        code, report, _ = lint(root, ".")
        assert code == 1
        assert {item["file"] for item in report["findings"]} == {"Dockerfile"}, report


def test_infra_lint_text_format() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "Dockerfile", "FROM node:latest\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"node\"]\n")
        done = run("lint_infra.py", ["Dockerfile"], cwd=root)
        assert done.returncode == 1
        assert "Dockerfile:1: P0 P0-UNPINNED-IMAGE" in done.stdout, done.stdout
        assert "infra lint: 1 P0, 0 P1, 0 P2" in done.stdout, done.stdout


def test_infra_lint_suppression_with_and_without_reason() -> None:
    """AC-023."""
    compose = """services:
  ci:
    image: runner:3.1
    restart: always
    mem_limit: 256m
    logging:
      driver: json-file
    volumes:
      # infra-lint-disable P0-DOCKER-SOCKET -- agente de CI isolado
      - /var/run/docker.sock:/var/run/docker.sock
  other:
    image: runner:3.1
    restart: always
    mem_limit: 256m
    logging:
      driver: json-file
    volumes:
      # infra-lint-disable P0-DOCKER-SOCKET
      - /var/run/docker.sock:/var/run/docker.sock
"""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "docker-compose.yml", compose)
        code, report, _ = lint(root, "docker-compose.yml")
        assert code == 1, report
        found = [(item["rule"], item["line"]) for item in report["findings"]]
        assert ("P0-DOCKER-SOCKET", 10) not in found, found
        assert ("P0-DOCKER-SOCKET", 19) in found, found
        assert ("P1-SUPPRESSION-NO-REASON", 18) in found, found


def test_infra_lint_usage_errors() -> None:
    with tempfile.TemporaryDirectory() as raw:
        done = run("lint_infra.py", ["missing.yml"], cwd=Path(raw))
        assert done.returncode == 2 and "not found" in done.stderr


# --- hook -------------------------------------------------------------------------------------


def hook(payload: dict, project_dir: Path) -> dict:
    env = {key: value for key, value in os.environ.items() if key not in {"CLAUDE_PROJECT_DIR", "CURSOR_PROJECT_DIR"}}
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps(payload), text=True, capture_output=True, check=False, env=env, timeout=20)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout or "{}")


def test_infra_hook_reports_without_blocking() -> None:
    with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as other:
        root = Path(raw)
        dockerfile = write(root, "Dockerfile", "FROM python:latest\nUSER 1000\nHEALTHCHECK CMD true\nCMD [\"python\"]\n")
        compose = write(root, "docker-compose.yml", "services:\n  app:\n    image: app:1.0\n    environment:\n      API_KEY: sk-test-abc123\n")
        script = write(root, "tool.py", "FROM = 'python:latest'\n")
        notes = write(root, "notes.md", "FROM python:latest\n")
        outside = write(Path(other), "Dockerfile", "FROM python:latest\n")
        common = {"session_id": "s", "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "Edit", "tool_response": {"success": True}}
        reply = hook({**common, "tool_input": {"file_path": str(dockerfile)}}, root)
        context = reply["hookSpecificOutput"]
        assert context["hookEventName"] == "PostToolUse"
        assert "P0-UNPINNED-IMAGE" in context["additionalContext"] and "Dockerfile" in context["additionalContext"]
        secret = hook({**common, "tool_input": {"file_path": str(compose)}}, root)
        assert "API_KEY" in secret["hookSpecificOutput"]["additionalContext"]
        assert "sk-test-abc123" not in json.dumps(secret)
        for path in (script, notes, outside):
            assert hook({**common, "tool_input": {"file_path": str(path)}}, root) == {}, path
        # Cursor: no channel back to the agent; the summary goes to the timeline of an opted-in project.
        opt_in(root)
        for path in (dockerfile, compose):
            cursor = {"hook_event_name": "afterFileEdit", "workspace_roots": [str(root)], "file_path": str(path)}
            done = subprocess.run([PYTHON, str(SCRIPTS / "hook.py")], input=json.dumps(cursor), text=True, capture_output=True, check=False, timeout=20)
            assert done.returncode == 0 and json.loads(done.stdout) == {}, done.stdout
        timeline = (root / ".agent-system" / "timeline" / "events.jsonl").read_text(encoding="utf-8")
        assert timeline.count('"INFRA_LINT"') == 2, timeline
        assert "sk-test-abc123" not in timeline and "python:latest" not in timeline


def test_infra_hook_init_copies_the_scripts() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("init_project", SCRIPTS / "init_project.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert {"lint_infra.py", "validate_architecture.py"} <= set(module.COPY_SCRIPTS)


# --- Phase 2 review, FIND-016 to FIND-023: one positive case per P0 branch and near misses -----

OK_TAIL = "USER 1000\nHEALTHCHECK CMD [\"true\"]\nCMD [\"app\"]\n"
SVC = "    restart: always\n    mem_limit: 256m\n    logging:\n      driver: json-file\n"

P0_BRANCHES = [
    # (rule, file, text, expected line)
    ("P0-ROOT-USER", "Dockerfile", "FROM node:20.11\nUSER 0\nHEALTHCHECK CMD [\"true\"]\nCMD [\"node\"]\n", 2),
    ("P0-ROOT-USER", "Dockerfile", "FROM node:20.11\nUSER 0:0\nHEALTHCHECK CMD [\"true\"]\nCMD [\"node\"]\n", 2),
    ("P0-ROOT-USER", "Dockerfile", "FROM node:20.11\nUSER 0:1000\nHEALTHCHECK CMD [\"true\"]\nCMD [\"node\"]\n", 2),
    ("P0-ROOT-USER", "Dockerfile", "FROM node:20.11\nUSER root:staff\nHEALTHCHECK CMD [\"true\"]\nCMD [\"node\"]\n", 2),
    ("P0-ROOT-USER", "pod.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  securityContext:\n    runAsNonRoot: false\n", 5),
    ("P0-ROOT-USER", "pod.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  securityContext: {runAsUser: 0}\n", 4),
    ("P0-PRIVILEGED", "pod.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n    - name: x\n      image: nginx:1.27\n      securityContext:\n        privileged: true\n", 8),
    ("P0-SECRET-LITERAL", "Dockerfile", "ARG GITHUB_TOKEN=ghp_abc\nFROM node:20.11\n" + OK_TAIL, 1),
    ("P0-SECRET-LITERAL", "Dockerfile", "FROM node:20.11\nENV DB_PASSWORD hunter2\n" + OK_TAIL, 2),
    ("P0-SECRET-LITERAL", "deploy.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n  - name: x\n    image: nginx:1.27\n    env:\n    - {name: DB_PASSWORD, value: hunter2}\n", 8),
    ("P0-SECRET-LITERAL", "deploy.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n  - name: x\n    image: nginx:1.27\n    env:\n    - value: hunter2\n      name: DB_PASSWORD\n", 8),
    ("P0-SECRET-LITERAL", "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    environment:\n    - POSTGRES_PASSWORD=hunter2\n", 9),
    ("P0-SECRET-LITERAL", "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    environment: {SESSION_SECRET: abc}\n", 8),
    ("P0-DB-PORT-PUBLIC", "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    ports:\n    - \"5432:5432\"\n", 9),
    ("P0-DB-PORT-PUBLIC", "docker-compose.yml", "services:   # stack\n  db:\n    image: postgres:16.3\n" + SVC + "    ports:   # published\n      - \"5432:5432\"\n", 9),
    ("P0-DB-PORT-PUBLIC", "docker-compose.yml", "services:\n  cache:\n    image: redis:7.2\n" + SVC + "    ports:\n      - target: 6379\n        published: 6379\n", 9),
    ("P0-DB-PORT-PUBLIC", "svc.yaml", "apiVersion: v1\nkind: Service\nspec:\n  type: NodePort\n  ports:\n    - port: 3306\n      nodePort: 30306\n", 6),
    ("P0-DOCKER-SOCKET", "pod.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  volumes:\n    - name: docker\n      hostPath:\n        path: /var/run/docker.sock\n", 7),
]


def test_infra_lint_each_p0_branch() -> None:
    for rule, relative, text, line in P0_BRANCHES:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            code, report, done = lint(root, relative)
            found = [(item["rule"], item["line"]) for item in report.get("findings", [])]
            assert code == 1 and (rule, line) in found, (rule, relative, text, found, done.stderr)


def test_infra_lint_every_db_port_and_secret_word() -> None:
    for port in (5432, 3306, 1433, 27017, 6379, 11211, 9200, 5672, 9092):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, "docker-compose.yml", f"services:\n  s:\n    image: x:1.0\n{SVC}    ports:\n      - \"{port}:{port}\"\n")
            assert "P0-DB-PORT-PUBLIC" in rules(lint(root, "docker-compose.yml")[1]), port
    for word in ("PASSWORD", "PASSWD", "SECRET", "TOKEN", "API_KEY", "APIKEY", "PRIVATE_KEY", "ACCESS_KEY"):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, "docker-compose.yml", f"services:\n  s:\n    image: x:1.0\n{SVC}    environment:\n      APP_{word}: literal-value\n")
            code, report, done = lint(root, "docker-compose.yml")
            assert code == 1 and "P0-SECRET-LITERAL" in rules(report), word
            assert "literal-value" not in done.stdout


NEAR_MISSES = [
    # (rule that must NOT appear, file, text)
    ("P0-DB-PORT-PUBLIC", "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    ports:\n      - \"[::1]:5432:5432\"\n"),
    ("P0-DB-PORT-PUBLIC", "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    ports:\n      - target: 5432\n        host_ip: 127.0.0.1\n        published: 5432\n"),
    ("P0-DB-PORT-PUBLIC", "docker-compose.yml", "services:\n  web:\n    image: web:1.0\n" + SVC + "    ports:\n      - \"8080:8080\"\n"),
    ("P0-DB-PORT-PUBLIC", "svc.yaml", "apiVersion: v1\nkind: Service\nspec:\n  type: ClusterIP\n  ports:\n    - port: 5432\n"),
    ("P0-UNPINNED-IMAGE", "Dockerfile", "FROM scratch\nCOPY app /app\n" + OK_TAIL),
    ("P0-ROOT-USER", "Dockerfile", "FROM node:20.11 AS runtime\nUSER 1000\nHEALTHCHECK CMD [\"true\"]\nFROM runtime\nCMD [\"node\"]\n"),
    ("P1-NO-HEALTHCHECK", "Dockerfile", "FROM node:20.11 AS runtime\nUSER 1000\nHEALTHCHECK CMD [\"true\"]\nFROM runtime\nCMD [\"node\"]\n"),
    ("P0-SECRET-LITERAL", "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    environment:\n      POSTGRES_PASSWORD_FILE: /run/secrets/pg\n      JWT_TOKEN_TTL: 3600\n      SESSION_TOKEN_TTL: 15m\n      API_KEY: null\n      OTHER_SECRET: ~\n"),
]


def test_infra_lint_near_misses_stay_quiet() -> None:
    for rule, relative, text in NEAR_MISSES:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, relative, text)
            report = lint(root, relative)[1]
            assert rule not in rules(report), (rule, text, report)


def test_infra_lint_compact_lists_and_probes() -> None:
    """FIND-016: a compact containers list keeps the probe and resource checks."""
    manifest = (
        "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n"
        "      - name: web\n        image: web:1.0\n        readinessProbe:\n          httpGet: {path: /ready, port: 8080}\n"
        "        resources:\n          requests: {cpu: 100m}\n          limits: {memory: 128Mi}\n"
    )
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "deploy.yaml", manifest)
        found = [(item["rule"], item["line"]) for item in lint(root, "deploy.yaml")[1]["findings"]]
        assert found == [("P1-NO-PROBE", 7)], found


def test_infra_lint_healthcheck_belongs_to_the_built_service() -> None:
    """FIND-021: only the Compose service that builds this Dockerfile counts, and only the final stage."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "Dockerfile", "FROM node:20.11 AS build\nHEALTHCHECK CMD [\"true\"]\nFROM node:20.11-slim\nUSER 1000\nCMD [\"node\"]\n")
        write(root, "docker-compose.yml", "services:\n  db:\n    image: postgres:16.3\n" + SVC + "    healthcheck:\n      test: [\"CMD\", \"pg_isready\"]\n  app:\n    build: .\n" + SVC)
        assert "P1-NO-HEALTHCHECK" in rules(lint(root, "Dockerfile")[1])
        write(root, "docker-compose.yml", "services:\n  app:\n    build:\n      context: .\n      dockerfile: Dockerfile\n" + SVC + "    healthcheck:\n      test: [\"CMD\", \"true\"]\n")
        assert "P1-NO-HEALTHCHECK" not in rules(lint(root, "Dockerfile")[1])


def test_infra_lint_suppression_needs_the_double_dash() -> None:
    """FIND-022: a reason without -- is reported; a lowercase rule id with a reason is applied."""
    base = "services:\n  ci:\n    image: runner:3.1\n" + SVC + "    volumes:\n"
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "docker-compose.yml", base + "      # infra-lint-disable P0-DOCKER-SOCKET because CI\n      - /var/run/docker.sock:/var/run/docker.sock\n")
        found = rules(lint(root, "docker-compose.yml")[1])
        assert {"P0-DOCKER-SOCKET", "P1-SUPPRESSION-NO-REASON"} <= found, found
        write(root, "docker-compose.yml", base + "      # infra-lint-disable p0-docker-socket -- isolated runner\n      - /var/run/docker.sock:/var/run/docker.sock\n")
        code, report, _ = lint(root, "docker-compose.yml")
        assert code == 0 and not rules(report) & {"P0-DOCKER-SOCKET", "P1-SUPPRESSION-NO-REASON"}, report


def test_infra_lint_reads_large_files() -> None:
    """FIND-018: the CLI never skips a file for its size."""
    filler = "".join(f"# filler line {index:06d} " + "x" * 40 + "\n" for index in range(12000))
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        path = write(root, "bundle.yaml", "apiVersion: v1\nkind: Pod\nspec:\n  containers:\n  - name: x\n    image: nginx:latest\n" + filler)
        assert path.stat().st_size > 512 * 1024
        code, report, _ = lint(root, "bundle.yaml")
        assert code == 1 and "P0-UNPINNED-IMAGE" in rules(report), report


def test_infra_hook_lists_p0_first() -> None:
    """FIND-025: the P0 is shown even when many P1/P2 come first by line."""
    services = "".join(f"  s{index}:\n    image: app:1.0\n" for index in range(6))
    compose = "services:\n" + services + "  db:\n    image: postgres:16.3\n" + SVC + "    ports:\n      - \"5432:5432\"\n"
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        path = write(root, "docker-compose.yml", compose)
        payload = {"session_id": "s", "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(path)}, "tool_response": {"success": True}}
        context = hook(payload, root)["hookSpecificOutput"]["additionalContext"]
        # The hook flattens the summary to one line; the P0 must come before every P1 and P2.
        assert "P0-DB-PORT-PUBLIC" in context and context.index("P0-DB-PORT-PUBLIC") < context.index("P1-"), context


# --- Phase 2 review 2, FIND-026 to FIND-028 ---------------------------------------------------


def test_infra_lint_env_lists_with_mixed_indentation() -> None:
    """FIND-026: each env: list is read on its own, whatever its style."""
    manifest = (
        "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n"
        "      initContainers:\n      - name: init\n        image: busybox:1.36\n        env:\n"
        "        - name: DB_PASSWORD\n          value: hunter2\n"
        "      containers:\n        - name: app\n          image: app:1.0\n          env:\n"
        "            - name: API_TOKEN\n              value: sk-live-xyz\n"
    )
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "deploy.yaml", manifest)
        code, report, done = lint(root, "deploy.yaml")
        secrets = sorted(item["line"] for item in report["findings"] if item["rule"] == "P0-SECRET-LITERAL")
        assert code == 1 and secrets == [10, 16], report
        assert "hunter2" not in done.stdout and "sk-live-xyz" not in done.stdout


def test_infra_lint_compose_environment_flow_list() -> None:
    """FIND-027."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "docker-compose.yml", "services:\n  app:\n    image: app:1.0\n" + SVC + "    environment: [\"API_KEY=sk-flow\", \"LOG_LEVEL=info\"]\n")
        code, report, done = lint(root, "docker-compose.yml")
        assert code == 1 and ("P0-SECRET-LITERAL", 8) in [(item["rule"], item["line"]) for item in report["findings"]], report
        assert "sk-flow" not in done.stdout


def test_infra_lint_copy_url_and_empty_reason() -> None:
    """FIND-028: COPY of a URL is not ADD; a suppression with an empty reason after -- is reported."""
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        write(root, "Dockerfile", "FROM debian:12.5\nCOPY https://example.com/a.txt /a.txt\n" + OK_TAIL)
        assert "P1-ADD-REMOTE" not in rules(lint(root, "Dockerfile")[1])
        write(root, "docker-compose.yml", "services:\n  ci:\n    image: runner:3.1\n" + SVC + "    volumes:\n      # infra-lint-disable P0-DOCKER-SOCKET --   \n      - /var/run/docker.sock:/var/run/docker.sock\n")
        found = rules(lint(root, "docker-compose.yml")[1])
        assert {"P0-DOCKER-SOCKET", "P1-SUPPRESSION-NO-REASON"} <= found, found


def test_infra_lint_unreadable_file_exits_2() -> None:
    """FIND-028: a file that cannot be read is a usage problem, not a clean result."""
    import io
    import contextlib
    from unittest import mock

    sys.path.insert(0, str(SCRIPTS))
    import lint_infra

    with tempfile.TemporaryDirectory() as raw:
        path = write(Path(raw), "Dockerfile", "FROM node:20.11\n")
        real = Path.read_text

        def failing(self, *args, **kwargs):
            if self.name == "Dockerfile":
                raise PermissionError("denied")
            return real(self, *args, **kwargs)

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(Path, "read_text", failing), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = lint_infra.main([str(path)])
        assert code == 2 and "unreadable" in err.getvalue(), (code, err.getvalue())


def test_infra_hook_keeps_every_p0_fix_in_context() -> None:
    """FIND-028: eight P0s with their fixes fit in the hook context, and the P1/P2 tail is cut first."""
    services = "".join(f"  db{index}:\n    image: postgres:16.3\n    ports:\n      - \"{5432}:5432\"\n" for index in range(8))
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        path = write(root, "docker-compose.yml", "services:\n" + services)
        payload = {"session_id": "s", "cwd": str(root), "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": str(path)}, "tool_response": {"success": True}}
        context = hook(payload, root)["hookSpecificOutput"]["additionalContext"]
        assert context.count("P0-DB-PORT-PUBLIC") == 8 and context.count("bind it to 127.0.0.1") == 8, context
        assert "more; run lint_infra.py" in context, context
