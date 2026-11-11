# FastAPI — security

Last reviewed: 2026-11-03

Scope: FastAPI 0.100+ with Pydantic v2, Python 3.10+, ASGI (Uvicorn or similar), database via SQLAlchemy 2.x or similar. General Python rules (subprocess, pickle, files) are in `python-general-web-security.md`.

## Recommendations

- Input: Pydantic models with types and limits (`Field(max_length=...)`, `conint`, `EmailStr`). For a body that must not accept extra fields, `model_config = ConfigDict(extra="forbid")`.
- Output: declare `response_model` (or a return annotation with an output model) to filter fields. Never return the ORM object with a password hash or internal fields.
- Authentication as a dependency (`Depends(get_current_user)`). `OAuth2PasswordBearer` only extracts the token from the header; validation (signature, expiry, issuer, audience) is yours.
- JWT: pin the list of algorithms when decoding (PyJWT: `jwt.decode(token, key, algorithms=["HS256"])`), require `exp`, use a strong key from the environment.
- Authorization per resource: the dependency delivers the user; the query filters by owner (`where(Order.owner_id == user.id)`). Use reusable dependencies for roles.
- Mass assignment: do not do `Model(**payload.model_dump())` with the broad input model. Have separate create/update models without privileged fields.
- SQL: ORM or `text()` with named parameters. Never an f-string in the query.
- CORS (`CORSMiddleware`): explicit `allow_origins`. Do not combine a wildcard with `allow_credentials=True`.
- `TrustedHostMiddleware` with the real hosts when the application generates URLs from `Host`.
- Documentation: in a public production deployment, turn off or protect `/docs`, `/redoc`, and `/openapi.json` (`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`) if the API is not public.
- Upload (`UploadFile`): FastAPI does not limit size by default. Limit at the proxy or read in chunks with a ceiling; validate type by content; generate the name on the server.
- Rate limiting is not built in: apply it at the proxy/gateway or with a library, mainly on login and reset.
- Errors: a handler that does not return a stack trace; `debug=False` in production.
- Dependencies: `pip-audit` in CI.

## Common vulnerabilities

- An endpoint that uses `Depends(get_current_user)` but fetches the resource only by ID (IDOR).
- A missing `response_model` returning `hashed_password`.
- A JWT decoded without verifying the signature or with the algorithm taken from the token.
- A `UserUpdate` that accepts `is_admin` from the client.
- Open CORS with credentials.
- An upload without a limit consuming memory or disk.
- A public `/docs` exposing internal endpoints.

## Secure implementation

```python
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

app = FastAPI()

class NoteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)

class NoteOut(BaseModel):
    id: int
    title: str

@app.patch("/notes/{note_id}", response_model=NoteOut)
async def update_note(note_id: int, body: NoteUpdate,
                      user=Depends(get_current_user), db=Depends(get_db)):
    note = db.scalar(select(Note).where(Note.id == note_id, Note.owner_id == user.id))
    if note is None:
        raise HTTPException(status_code=404)
    note.title = body.title
    db.commit()
    return note
```

## Inadequate implementation and risk

```python
@app.patch("/notes/{note_id}")
async def update_note(note_id: int, body: dict, db=Depends(get_db)):
    note = db.get(Note, note_id)
    for k, v in body.items():
        setattr(note, k, v)
    db.commit()
    return note
```

Risk: with no authentication or owner filter, any client changes any note and any column (including `owner_id`), and the response returns the whole object.

## Security tests

- `TestClient`/`httpx`: no token → 401; another user's token → 404 or 403; an expired token or one with a swapped signature → 401; a token with a different `alg` → 401.
- A body with an extra field → 422.
- The response does not contain fields outside the `response_model`.
- An upload above the limit is refused.
- Optional tools: Bandit, `pip-audit`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/API-Security/
- https://owasp.org/Top10/
- https://fastapi.tiangolo.com/tutorial/security/
- https://fastapi.tiangolo.com/tutorial/cors/
