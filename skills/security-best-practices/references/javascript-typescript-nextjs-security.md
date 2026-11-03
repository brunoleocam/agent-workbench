# Next.js — segurança

Última revisão: 2026-11-03

Escopo: Next.js 14+ com App Router (Server Components, Server Actions, Route Handlers, Middleware), JavaScript ou TypeScript. As regras de JSX e DOM de `javascript-typescript-react-security.md` também valem aqui; esta referência cobre o que é específico do servidor do Next.

## Recomendações

- Server Action é um endpoint POST público. Dentro de cada action: autentique, autorize sobre o recurso e valide os argumentos com schema. Esconder o botão não protege a action.
- Route Handler (`app/**/route.ts`) também é endpoint público; mesma regra.
- Middleware não deve ser a única barreira de autorização. Repita a checagem perto do dado (action, handler, camada de acesso a dados). Mantenha o Next atualizado: houve bypass de middleware por header interno (CVE-2025-29927, corrigido em 14.2.25 e 15.2.3).
- Centralize o acesso a dados numa camada só de servidor que já filtra por usuário e devolve DTOs com os campos necessários. Marque esses módulos com `import 'server-only'` para o build falhar se forem importados por Client Component.
- Props passadas de Server para Client Component são serializadas e chegam ao navegador. Não passe o objeto inteiro do banco (hash de senha, tokens, campos internos).
- Variáveis `NEXT_PUBLIC_*` vão para o bundle do cliente. Segredo nunca leva esse prefixo.
- CSRF: Server Actions só aceitam POST e o Next compara `Origin` com o host; atrás de proxy reverso com outro domínio, configure `serverActions.allowedOrigins` em vez de desligar a checagem. Route Handlers que mudam estado com cookie de sessão precisam da sua própria verificação (Origin ou token).
- `redirect()` com destino vindo do usuário: só caminhos relativos internos ou allowlist.
- Imagens remotas: `images.remotePatterns` restrito aos hosts reais; padrão amplo transforma o otimizador num proxy.
- Headers: CSP (com nonce via middleware se usar scripts inline), HSTS e demais em `next.config` `headers()` ou no middleware.
- Cookies de sessão via `cookies()` com `httpOnly`, `secure`, `sameSite`.
- Cache: dado por usuário não pode cair em cache compartilhado. Rotas que leem `cookies()`/`headers()` são dinâmicas; ao usar `fetch` com cache ou `unstable_cache`, não inclua dado de um usuário em entrada servida a outro.
- Erros: mensagem genérica ao cliente; detalhe só no log do servidor.

## Vulnerabilidades comuns

- Server Action sem checagem de permissão (`deletePost(id)` chamável por qualquer um).
- IDOR em Route Handler `GET /api/invoices/[id]`.
- Vazamento de campos sensíveis em props de Client Component.
- Segredo exposto por prefixo `NEXT_PUBLIC_`.
- Autorização feita só no middleware, com matcher que não cobre todas as rotas.
- Open redirect via `?callbackUrl=`.
- SSRF em action que busca URL informada pelo usuário.
- XSS por `dangerouslySetInnerHTML` com conteúdo do CMS.

## Implementação segura

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

## Implementação inadequada e risco

```ts
'use server';
export async function deletePost(postId: string) {
  await db.post.delete({ where: { id: postId } });
}
```

Risco: qualquer visitante, mesmo sem login, pode invocar a action com o ID de qualquer post e apagá-lo, porque a action é um endpoint POST acessível fora da UI.

## Testes de segurança

- Teste unitário de cada action e handler: sem sessão → recusa; sessão de outro usuário → recusa; argumento malformado → erro de validação.
- Inspecionar o payload RSC/HTML da página e confirmar que campos sensíveis não aparecem.
- Buscar `NEXT_PUBLIC_` no código e conferir que nenhum é segredo.
- `callbackUrl=https://evil.example` não redireciona para fora.
- Conferir a versão do Next contra avisos de segurança publicados.
- Ferramentas opcionais: ESLint com `eslint-config-next`, `npm audit`, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://nextjs.org/blog/security-nextjs-server-components-actions
- https://nextjs.org/docs
- https://github.com/vercel/next.js/security/advisories
