"""Shared helper for the hidden acceptance tests: starts the project's server as a
black box (2 workers, one SQLite file) and gives tests an httpx client.

Environment: APP_DIR (project root), optional ADMIN_USER / ADMIN_PASSWORD.
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, app_dir: str, extra_env: dict | None = None, db_path: str | None = None):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db = db_path or str(Path(self.tmp.name) / "bench.db")
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        env = dict(os.environ)
        env.update({"DB_PATH": self.db})
        for k, v in (extra_env or {}).items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
        self.log = open(Path(self.tmp.name) / "server.log", "w")
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(self.port), "--workers", "2"],
            cwd=app_dir, env=env, stdout=self.log, stderr=subprocess.STDOUT,
        )

    def wait_ready(self, timeout: float = 30.0) -> None:
        end = time.time() + timeout
        while time.time() < end:
            if self.proc.poll() is not None:
                raise RuntimeError("server exited: " + self.tail())
            try:
                if httpx.get(self.url + "/health", timeout=2).status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.3)
        raise RuntimeError("server did not become ready: " + self.tail())

    def tail(self) -> str:
        self.log.flush()
        try:
            return Path(self.log.name).read_text()[-1500:]
        except OSError:
            return ""

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()
        self.tmp.cleanup()
