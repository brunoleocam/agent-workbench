# Python web — segurança

Última revisão: 2026-11-03

Escopo: Python 3.10+ em aplicação web sem referência dedicada (Flask, Starlette puro, scripts que atendem HTTP, workers). FastAPI e Django têm referências próprias; esta cobre a base da linguagem e da biblioteca padrão.

## Recomendações

- SQL: parâmetros do driver DB-API (`cursor.execute(sql, params)`), com o placeholder do driver (`%s` no psycopg, `?` no sqlite3). No SQLAlchemy, `text()` com `bindparams`/dicionário. Nunca f-string ou `%` para montar SQL.
- Templates: Jinja2 com `autoescape` ligado para HTML (o Flask liga por padrão em `.html`). `Markup()` e `|safe` só em conteúdo sanitizado.
- Comandos: `subprocess.run([...], shell=False, check=True)` com lista de argumentos. `shell=True` com entrada externa é injeção.
- Desserialização: `json` para dado externo. `pickle`, `marshal` e `shelve` só com dado confiável. YAML com `yaml.safe_load`.
- XML externo: `defusedxml` em vez dos parsers da biblioteca padrão.
- Aleatoriedade: `secrets.token_urlsafe()` e `secrets.choice()`. O módulo `random` não é para segurança.
- Comparação de token: `hmac.compare_digest()`.
- Senha: argon2 (`argon2-cffi`) ou bcrypt; nunca hash simples (`hashlib.sha256`) sem KDF.
- Arquivos: resolva com `pathlib` e confirme que fica dentro da base (`resolved.is_relative_to(base)`). Em `tarfile`, use `filter='data'` (Python 3.12+ e releases de segurança com backport); em `zipfile`, valide cada nome antes de extrair.
- HTTP de saída: `timeout` sempre (requests não tem padrão). URL do usuário só após allowlist de host e bloqueio de IPs internos, contra SSRF.
- `eval`, `exec` e `compile` nunca sobre entrada externa. `ast.literal_eval` só para literais simples.
- Flask: `SECRET_KEY` do ambiente; `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE`; CSRF via extensão (ex.: Flask-WTF) em formulários; `debug=False` em produção (o debugger do Werkzeug executa código).
- Logs sem senha, token ou documento completo.
- Dependências: `pip-audit` no CI e versões fixadas.

## Vulnerabilidades comuns

- SQL injection com f-string em `execute`.
- Command injection em `os.system` ou `subprocess(..., shell=True)` com nome de arquivo do usuário.
- Execução de código via `pickle.loads` em cookie, fila ou cache.
- `yaml.load` sem `Loader` seguro.
- XXE ou "billion laughs" com `xml.etree` sobre XML externo.
- Path traversal em `send_file(os.path.join(base, nome))`.
- Zip slip ao extrair arquivo enviado.
- Debugger do Werkzeug exposto em produção.
- SSRF em importação por URL.

## Implementação segura

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

## Implementação inadequada e risco

```python
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")
os.system(f"convert {filename} thumb.png")
data = pickle.loads(base64.b64decode(request.cookies["state"]))
```

Risco: injeção de SQL; nome de arquivo `x.png; rm -rf ~` executa comando no servidor; cookie forjado com pickle executa código arbitrário no processo.

## Testes de segurança

- pytest com payloads de SQL e de shell (`;`, `$( )`, crase) provando que nada além do esperado acontece.
- `safe_path('../../etc/passwd')` levanta erro.
- Arquivo zip com entrada `../x` é recusado.
- Requisição de saída para `127.0.0.1`, `169.254.169.254` e hosts fora da allowlist é bloqueada.
- Ferramentas opcionais: Bandit, `pip-audit`, Semgrep.

## Fontes

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
