# Express — security

Last reviewed: 2026-11-03

Scope: Express 4 and 5 on Node.js LTS (20+), JavaScript or TypeScript, serving a JSON API or server-rendered pages. The React front end is in `javascript-typescript-react-security.md`.

## Recommendations

- Use a maintained version of Express and Node. In Express 5, a rejected promise in a handler goes to the error handler; in 4, wrap async handlers or handle the error, otherwise the process may be left with a hanging request.
- Headers: `helmet()` gives a reasonable set (CSP, `X-Content-Type-Options`, HSTS, etc.). Review the CSP for the real application. `app.disable('x-powered-by')` if you do not use helmet.
- Body: `express.json({ limit: '100kb' })` or the limit the case requires. Validate the body with a schema (zod, joi, ajv) and reject unexpected fields.
- Authorization on every route that accesses a resource that has an owner, in the handler or in middleware that checks the owner, not just "is logged in".
- Session with `express-session`: a strong `secret` from the environment, a persistent store (the default MemoryStore is not for production), `httpOnly`, `secure`, `sameSite` cookie. `req.session.regenerate()` after login.
- CSRF: Express has no native protection and `csurf` is deprecated. With a session cookie, use a synchronized token from a maintained library or verify `Origin` on state-changing methods, in addition to `sameSite`.
- `app.set('trust proxy', ...)` with the number of proxies or the real ranges, never `true` without need; it affects `req.ip`, rate limiting, and `req.secure`.
- Rate limit (`express-rate-limit`) on login, reset, and expensive endpoints.
- CORS (`cors`): an explicit list of origins. Never reflect any `Origin` with `credentials: true`.
- MongoDB: reject objects where a string is expected (`{ "$ne": null }` at login). Validate the type before the query.
- Files: `res.sendFile(name, { root: dir })` with a validated name; never concatenate a user path.
- Prototype pollution: do not deep-merge external JSON into objects; use a schema or `Object.create(null)` for maps.
- Regex over external input without catastrophic backtracking (ReDoS).
- Errors: a final handler that logs details and returns a generic message; `NODE_ENV=production`.
- Dependencies: `npm audit` (or the package manager's equivalent) in CI; lockfile committed.

## Common vulnerabilities

- NoSQL injection through a Mongo operator in the body or query string.
- IDOR in `GET /api/orders/:id` without an owner filter.
- Mass assignment: `User.update(req.body)` writing `role`.
- Path traversal in `res.sendFile(path.join(dir, req.params.file))` without a check.
- SSRF when fetching a user-supplied URL (webhook, preview, import).
- Command injection with `child_process.exec` and a built string.
- Stack trace exposed in an error response.
- A JWT accepted without pinning the algorithm, or without verifying expiry.

## Secure implementation

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
  // verify the password with bcrypt/argon2, then req.session.regenerate(...)
});

app.get('/api/orders/:id', requireAuth, async (req, res) => {
  const order = await orders.findOne({ _id: req.params.id, ownerId: req.user.id });
  if (!order) return res.sendStatus(404);
  res.json(order);
});
```

## Inadequate implementation and risk

```js
app.post('/login', async (req, res) => {
  const user = await users.findOne({ email: req.body.email, password: req.body.password });
  res.json(user);
});
app.get('/files/:name', (req, res) => res.sendFile(__dirname + '/uploads/' + req.params.name));
```

Risk: `{"email":"a@b.c","password":{"$ne":null}}` authenticates without a password (and the password is plain text in the database); the response returns the user's whole document; the files route reads outside `uploads/` with an encoded name containing `..`.

## Security tests

- Supertest: a body with a `$ne`/`$gt` operator is rejected with 400.
- User B accessing A's resource gets 404 or 403.
- An extra field (`role`) in the body is rejected or ignored.
- A file name with `..%2f` does not leave the directory.
- A forced error does not return a stack trace.
- Security headers are present in the response.
- Optional tools: `npm audit`, `eslint-plugin-security`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/Nodejs_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/NPM_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://expressjs.com/en/advanced/best-practice-security.html
- https://nodejs.org/en/learn/getting-started/security-best-practices
