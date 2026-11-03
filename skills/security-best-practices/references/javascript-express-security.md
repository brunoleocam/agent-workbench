# Express — segurança

Última revisão: 2026-11-03

Escopo: Express 4 e 5 em Node.js LTS (20+), JavaScript ou TypeScript, servindo API JSON ou páginas renderizadas no servidor. Front React fica em `javascript-typescript-react-security.md`.

## Recomendações

- Use versão mantida de Express e Node. No Express 5, promessa rejeitada em handler vai para o error handler; no 4, envolva handlers async ou trate o erro, senão o processo pode ficar com requisição pendurada.
- Headers: `helmet()` dá um conjunto razoável (CSP, `X-Content-Type-Options`, HSTS etc.). Revise a CSP para a aplicação real. `app.disable('x-powered-by')` se não usar helmet.
- Corpo: `express.json({ limit: '100kb' })` ou o limite que o caso exige. Valide o corpo com schema (zod, joi, ajv) e rejeite campos não previstos.
- Autorização em cada rota que acessa recurso de um dono, no handler ou em middleware que confere o dono, não só "está logado".
- Sessão com `express-session`: `secret` forte vindo do ambiente, store persistente (o MemoryStore padrão não é para produção), cookie `httpOnly`, `secure`, `sameSite`. `req.session.regenerate()` após login.
- CSRF: Express não tem proteção nativa e o `csurf` está deprecado. Com cookie de sessão, use token sincronizado de biblioteca mantida ou verifique `Origin` em métodos que mudam estado, além de `sameSite`.
- `app.set('trust proxy', ...)` com o número de proxies ou as faixas reais, nunca `true` sem necessidade; afeta `req.ip`, rate limit e `req.secure`.
- Rate limit (`express-rate-limit`) em login, reset e endpoints caros.
- CORS (`cors`): lista explícita de origens. Nunca refletir qualquer `Origin` com `credentials: true`.
- MongoDB: rejeite objetos onde se espera string (`{ "$ne": null }` no login). Valide tipo antes da query.
- Arquivos: `res.sendFile(nome, { root: dir })` com nome validado; nunca concatene caminho do usuário.
- Prototype pollution: não faça merge profundo de JSON externo em objetos; use schema ou `Object.create(null)` para mapas.
- Regex sobre entrada externa sem backtracking catastrófico (ReDoS).
- Erros: handler final que loga detalhes e devolve mensagem genérica; `NODE_ENV=production`.
- Dependências: `npm audit` (ou equivalente do gerenciador) no CI; lockfile commitado.

## Vulnerabilidades comuns

- NoSQL injection por operador Mongo no corpo ou na query string.
- IDOR em `GET /api/orders/:id` sem filtro por dono.
- Mass assignment: `User.update(req.body)` gravando `role`.
- Path traversal em `res.sendFile(path.join(dir, req.params.file))` sem conferência.
- SSRF ao buscar URL informada pelo usuário (webhook, preview, import).
- Command injection com `child_process.exec` e string montada.
- Stack trace exposto em resposta de erro.
- JWT aceito sem fixar algoritmo, ou sem verificar expiração.

## Implementação segura

```js
const express = require('express');
const helmet = require('helmet');
const { z } = require('zod');

const app = express();
app.use(helmet());
app.use(express.json({ limit: '100kb' }));

const LoginBody = z.object({ email: z.string().email(), password: z.string().min(1) }).strict();

app.post('/login', loginLimiter, async (req, res, next) => {
  const parsed = LoginBody.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: 'invalid_body' });
  const user = await users.findOne({ email: parsed.data.email });
  // verificar senha com bcrypt/argon2, depois req.session.regenerate(...)
});

app.get('/api/orders/:id', requireAuth, async (req, res) => {
  const order = await orders.findOne({ _id: req.params.id, ownerId: req.user.id });
  if (!order) return res.sendStatus(404);
  res.json(order);
});
```

## Implementação inadequada e risco

```js
app.post('/login', async (req, res) => {
  const user = await users.findOne({ email: req.body.email, password: req.body.password });
  res.json(user);
});
app.get('/files/:name', (req, res) => res.sendFile(__dirname + '/uploads/' + req.params.name));
```

Risco: `{"email":"a@b.c","password":{"$ne":null}}` autentica sem senha (e a senha está em texto puro no banco); a resposta devolve o documento inteiro do usuário; a rota de arquivos lê fora de `uploads/` com nome codificado contendo `..`.

## Testes de segurança

- Supertest: corpo com operador `$ne`/`$gt` é rejeitado com 400.
- Usuário B acessando recurso de A recebe 404 ou 403.
- Campo extra (`role`) no corpo é rejeitado ou ignorado.
- Nome de arquivo com `..%2f` não sai do diretório.
- Erro forçado não devolve stack trace.
- Headers de segurança presentes na resposta.
- Ferramentas opcionais: `npm audit`, `eslint-plugin-security`, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://expressjs.com/en/advanced/best-practice-security.html
- https://nodejs.org/en/learn/getting-started/security-best-practices
