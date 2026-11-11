# Python web — security

Last reviewed: 2026-11-03

Scope: Python 3.10+ in a web application without a dedicated reference (Flask, bare Starlette, scripts that serve HTTP, workers). FastAPI and Django have their own references; this one covers the language and standard library base.

## Recommendations

- SQL: DB-API driver parameters (`cursor.execute(sql, params)`), with the driver's placeholder (`%s` in psycopg, `?` in sqlite3). In SQLAlchemy, `text()` with `bindparams`/a dictionary. Never an f-string or `%` to build SQL.
- Templates: Jinja2 with `autoescape` on for HTML (Flask turns it on by default for `.html`). `Markup()` and `|safe` only on sanitized content.
- Commands: `subprocess.run([...], shell=False, check=True)` with an argument list. `shell=True` with external input is injection.
- Deserialization: `json` for external data. `pickle`, `marshal`, and `shelve` only with trusted data. YAML with `yaml.safe_load`.
- External XML: `defusedxml` instead of the standard library parsers.
- Randomness: `secrets.token_urlsafe()` and `secrets.choice()`. The `random` module is not for security.
- Token comparison: `hmac.compare_digest()`.
- Password: argon2 (`argon2-cffi`) or bcrypt; never a plain hash (`hashlib.sha256`) without a KDF.
- Files: resolve with `pathlib` and confirm it stays inside the base (`resolved.is_relative_to(base)`). With `tarfile`, use `filter='data'` (Python 3.12+ and security releases with a backport); with `zipfile`, validate each name before extracting.
- Outbound HTTP: always a `timeout` (requests has no default). A user URL only after a host allowlist and blocking of internal IPs, against SSRF.
- `eval`, `exec`, and `compile` never over external input. `ast.literal_eval` only for simple literals.
- Flask: `SECRET_KEY` from the environment; `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`; CSRF via an extension (e.g. Flask-WTF) on forms; `debug=False` in production (the Werkzeug debugger executes code).
- Logs without passwords, tokens, or whole documents.
- Dependencies: `pip-audit` in CI and pinned versions.

## Common vulnerabilities

- SQL injection with an f-string in `execute`.
- Command injection in `os.system` or `subprocess(..., shell=True)` with a user file name.
- Code execution via `pickle.loads` on a cookie, queue, or cache.
- `yaml.load` without a safe `Loader`.
- XXE or "billion laughs" with `xml.etree` over external XML.
- Path traversal in `send_file(os.path.join(base, name))`.
- Zip slip when extracting an uploaded archive.
- The Werkzeug debugger exposed in production.
- SSRF in an import by URL.

## Secure implementation

```python
import secrets
import subprocess
from pathlib import Path

BASE = Path("/srv/app/files").resolve()

def find_user(conn, email: str):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name FROM users WHERE email = %s", (email,))
        return cur.fetchone()

def safe_path(name: str) -> Path:
    target = (BASE / name).resolve()
    if not target.is_relative_to(BASE):
        raise ValueError("invalid path")
    return target

def thumbnail(src: Path, dst: Path) -> None:
    subprocess.run(["convert", str(src), "-resize", "200x200", str(dst)], check=True, timeout=30)

reset_token = secrets.token_urlsafe(32)
```

## Inadequate implementation and risk

```python
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
os.system(f"convert {filename} thumb.png")
data = pickle.loads(base64.b64decode(request.cookies["state"]))
```

Risk: SQL injection; a file name `x.png; rm -rf ~` runs a command on the server; a forged cookie with pickle executes arbitrary code in the process.

## Security tests

- pytest with SQL and shell payloads (`;`, `$( )`, backticks) proving that nothing beyond what is expected happens.
- `safe_path('../../etc/passwd')` raises an error.
- A zip file with a `../x` entry is refused.
- An outbound request to `127.0.0.1`, `169.254.169.254`, and hosts outside the allowlist is blocked.
- Optional tools: Bandit, `pip-audit`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://docs.python.org/3/library/secrets.html
- https://docs.python.org/3/library/subprocess.html
- https://docs.python.org/3/library/pickle.html
- https://flask.palletsprojects.com/en/stable/web-security/
