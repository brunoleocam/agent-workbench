# Next.js — security

Last reviewed: 2026-11-03

Scope: Next.js 14+ with the App Router (Server Components, Server Actions, Route Handlers, Middleware), JavaScript or TypeScript. The JSX and DOM rules in `javascript-typescript-react-security.md` also apply here; this reference covers what is specific to the Next server.

## Recommendations

- A Server Action is a public POST endpoint. Inside each action: authenticate, authorize over the resource, and validate the arguments with a schema. Hiding the button does not protect the action.
- A Route Handler (`app/**/route.ts`) is also a public endpoint; same rule.
- Middleware must not be the only authorization barrier. Repeat the check close to the data (action, handler, data access layer). Keep Next updated: there was a middleware bypass through an internal header (CVE-2025-29927, fixed in 14.2.25 and 15.2.3).
- Centralize data access in a server-only layer that already filters by user and returns DTOs with the needed fields. Mark those modules with `import 'server-only'` so the build fails if a Client Component imports them.
- Props passed from a Server to a Client Component are serialized and reach the browser. Do not pass the whole database object (password hash, tokens, internal fields).
- `NEXT_PUBLIC_*` variables go into the client bundle. A secret never carries that prefix.
- CSRF: Server Actions only accept POST and Next compares `Origin` with the host; behind a reverse proxy with another domain, configure `serverActions.allowedOrigins` instead of turning the check off. Route Handlers that change state with a session cookie need their own verification (Origin or token).
- `redirect()` with a user-supplied destination: only internal relative paths or an allowlist.
- Remote images: `images.remotePatterns` restricted to the real hosts; a broad pattern turns the optimizer into a proxy.
- Headers: CSP (with a nonce via middleware if you use inline scripts), HSTS, and others in `next.config` `headers()` or in middleware.
- Session cookies through `cookies()` with `httpOnly`, `secure`, `sameSite`.
- Cache: per-user data cannot land in a shared cache. Routes that read `cookies()`/`headers()` are dynamic; when using `fetch` with cache or `unstable_cache`, do not include one user's data in an entry served to another.
- Errors: a generic message to the client; detail only in the server log.

## Common vulnerabilities

- A Server Action without a permission check (`deletePost(id)` callable by anyone).
- IDOR in the Route Handler `GET /api/invoices/[id]`.
- Leaking sensitive fields in Client Component props.
- A secret exposed by the `NEXT_PUBLIC_` prefix.
- Authorization done only in middleware, with a matcher that does not cover every route.
- Open redirect via `?callbackUrl=`.
- SSRF in an action that fetches a user-supplied URL.
- XSS by `dangerouslySetInnerHTML` with CMS content.

## Secure implementation

```ts
'use server';
import 'server-only';
import { z } from 'zod';
import { getSession } from '@/lib/auth';
import { db } from '@/lib/db';

const Input = z.object({ postId: z.string().uuid() });

export async function deletePost(raw: unknown) {
  const session = await getSession();
  if (!session) throw new Error('unauthorized');
  const { postId } = Input.parse(raw);

  const result = await db.post.deleteMany({ where: { id: postId, authorId: session.userId } });
  if (result.count === 0) throw new Error('not_found');
}
```

## Inadequate implementation and risk

```ts
'use server';
export async function deletePost(postId: string) {
  await db.post.delete({ where: { id: postId } });
}
```

Risk: any visitor, even without logging in, can invoke the action with any post's ID and delete it, because the action is a POST endpoint reachable outside the UI.

## Security tests

- A unit test for each action and handler: no session → refused; another user's session → refused; a malformed argument → validation error.
- Inspect the page's RSC/HTML payload and confirm that sensitive fields do not appear.
- Search for `NEXT_PUBLIC_` in the code and check that none is a secret.
- `callbackUrl=https://evil.example` does not redirect outside.
- Check the Next version against published security advisories.
- Optional tools: ESLint with `eslint-config-next`, `npm audit`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://nextjs.org/blog/security-nextjs-server-components-actions
- https://nextjs.org/docs
- https://github.com/vercel/next.js/security/advisories
