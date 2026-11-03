# FastAPI — segurança

Última revisão: 2026-11-03

Escopo: FastAPI 0.100+ com Pydantic v2, Python 3.10+, ASGI (Uvicorn ou similar), banco via SQLAlchemy 2.x ou similar. Regras gerais de Python (subprocess, pickle, arquivos) estão em `python-general-web-security.md`.

## Recomendações

- Entrada: modelos Pydantic com tipos e limites (`Field(max_length=...)`, `conint`, `EmailStr`). Para corpo que não deve aceitar campos extras, `model_config = ConfigDict(extra="forbid")`.
- Saída: declare `response_model` (ou anotação de retorno com modelo de saída) para filtrar campos. Nunca devolva o objeto ORM com hash de senha ou campos internos.
- Autenticação como dependência (`Depends(get_current_user)`). `OAuth2PasswordBearer` só extrai o token do header; a validação (assinatura, expiração, emissor, audiência) é sua.
- JWT: fixe a lista de algoritmos ao decodificar (PyJWT: `jwt.decode(token, key, algorithms=["HS256"])`), exija `exp`, use chave forte do ambiente.
- Autorização por recurso: a dependência entrega o usuário; a consulta filtra por dono (`where(Order.owner_id == user.id)`). Use dependências reutilizáveis para papéis.
- Mass assignment: não faça `Model(**payload.model_dump())` com o modelo de entrada amplo. Tenha modelos separados de criação/atualização sem campos privilegiados.
- SQL: ORM ou `text()` com parâmetros nomeados. Nunca f-string na query.
- CORS (`CORSMiddleware`): `allow_origins` explícito. Não combine curinga com `allow_credentials=True`.
- `TrustedHostMiddleware` com os hosts reais quando a aplicação gera URLs a partir do `Host`.
- Documentação: em produção pública, desligue ou proteja `/docs`, `/redoc` e `/openapi.json` (`FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`) se a API não for pública.
- Upload (`UploadFile`): FastAPI não limita tamanho por padrão. Limite no proxy ou leia em blocos com teto; valide tipo pelo conteúdo; gere o nome no servidor.
- Rate limit não vem embutido: aplique no proxy/gateway ou com biblioteca, principalmente em login e reset.
- Erros: handler que não devolve stack trace; `debug=False` em produção.
- Dependências: `pip-audit` no CI.

## Vulnerabilidades comuns

- Endpoint que usa `Depends(get_current_user)` mas busca o recurso só pelo ID (IDOR).
- `response_model` ausente devolvendo `hashed_password`.
- JWT decodificado sem verificar assinatura ou com algoritmo vindo do token.
- `UserUpdate` com `is_admin` aceito do cliente.
- CORS aberto com credenciais.
- Upload sem limite consumindo memória ou disco.
- `/docs` público expondo endpoints internos.

## Implementação segura

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

## Implementação inadequada e risco

```python
@app.patch("/notes/{note_id}")
async def update_note(note_id: int, body: dict, db=Depends(get_db)):
    note = db.get(Note, note_id)
    for k, v in body.items():
        setattr(note, k, v)
    db.commit()
    return note
```

Risco: sem autenticação nem filtro por dono, qualquer cliente altera qualquer nota e qualquer coluna (inclusive `owner_id`), e a resposta devolve o objeto inteiro.

## Testes de segurança

- `TestClient`/`httpx`: sem token → 401; token de outro usuário → 404 ou 403; token expirado ou com assinatura trocada → 401; token com `alg` diferente → 401.
- Corpo com campo extra → 422.
- Resposta não contém campos fora do `response_model`.
- Upload acima do limite é recusado.
- Ferramentas opcionais: Bandit, `pip-audit`, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/API-Security/
- https://owasp.org/Top10/
- https://fastapi.tiangolo.com/tutorial/security/
- https://fastapi.tiangolo.com/tutorial/cors/
