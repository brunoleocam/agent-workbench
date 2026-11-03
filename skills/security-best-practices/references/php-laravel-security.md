# Laravel — segurança

Última revisão: 2026-11-03

Escopo: Laravel 10+ e 11 em PHP 8.1+ (Laravel 11 exige PHP 8.2+), com Eloquent, Blade e o stack padrão de middleware. Regras de PHP puro estão em `php-general-web-security.md`.

## Recomendações

- Autorização: Policies ou Gates em toda ação sobre recurso de um dono. `Gate::authorize('update', $post)` ou `$this->authorize(...)` quando o controller usa `AuthorizesRequests` (o controller base do Laravel 11 não inclui o trait por padrão). Middleware `auth` só autentica, não autoriza.
- Escopo por dono: prefira `$request->user()->orders()->findOrFail($id)` a `Order::findOrFail($id)`.
- Mass assignment: declare `$fillable` (ou `$guarded` restrito) em todo model. Use `$request->validated()` ou `$request->safe()->only([...])`, nunca `$request->all()` em `create`/`update`. Não desligue a proteção com `Model::unguard()` fora de seeders.
- Validação: Form Requests com regras explícitas. Em `exists`/`unique`, restrinja colunas e escopo.
- SQL: Query Builder e Eloquent parametrizam. Em `whereRaw`, `selectRaw`, `orderByRaw` e `DB::raw`, passe bindings (`whereRaw('price > ?', [$min])`). Coluna de ordenação vinda do usuário só por allowlist.
- Blade: `{{ }}` escapa. `{!! !!}` só com HTML sanitizado no servidor. Dado para JavaScript via `@json` / `Js::from`.
- CSRF: `@csrf` em formulários. No Laravel 11, exceções ficam em `bootstrap/app.php` (`$middleware->validateCsrfTokens(except: [...])`); no 10, em `VerifyCsrfToken::$except`. Exceção só para webhook com assinatura verificada.
- Configuração: `APP_DEBUG=false` e `APP_ENV=production` em produção. `APP_KEY` secreto, fora do repositório; trocá-lo invalida dados criptografados e sessões.
- Senha: `Hash::make()` e `Hash::check()` (bcrypt ou argon2 conforme `config/hashing.php`). Reset de senha pelo broker nativo.
- Rate limit: `throttle` em login, reset de senha, OTP e endpoints caros (`RateLimiter::for`).
- Upload: regras `file`, `mimes`/`mimetypes`, `max`. `$file->store('dir')` gera nome aleatório; não use `getClientOriginalName()` como caminho. Disco privado para arquivo sensível; entrega por rota autorizada ou `temporaryUrl`.
- Links sensíveis: `URL::signedRoute()` / `temporarySignedRoute()` com middleware `signed`.
- Redirect: `redirect()->intended()` ou rotas nomeadas; não redirecione para URL arbitrária do request.
- Dependências: `composer audit` no CI.

## Vulnerabilidades comuns

- IDOR por route model binding sem policy (`/invoices/{invoice}`).
- Mass assignment de `is_admin`, `role` ou `user_id` via `$request->all()`.
- XSS por `{!! $comentario !!}`.
- SQL injection em `whereRaw("name = '$name'")` ou `orderBy($request->sort)`.
- `APP_DEBUG=true` em produção expondo stack trace, variáveis de ambiente e queries.
- `.env` acessível pela web quando o document root não aponta para `public/`.
- Webhook excluído do CSRF sem verificar assinatura.

## Implementação segura

```php
public function update(UpdatePostRequest $request, Post $post)
{
    Gate::authorize('update', $post);
    $post->update($request->validated());

    return redirect()->route('posts.show', $post);
}

$posts = Post::query()
    ->whereRaw('LOWER(title) LIKE ?', ['%' . mb_strtolower($term) . '%'])
    ->orderBy(in_array($sort, ['title', 'created_at'], true) ? $sort : 'created_at')
    ->paginate();
```

## Implementação inadequada e risco

```php
public function update(Request $request, $id)
{
    $post = Post::find($id);
    $post->update($request->all());
}
```

Risco: qualquer usuário autenticado altera post de outro (IDOR), e campos não previstos no formulário, como `user_id` ou `published`, são gravados se o model não os proteger.

## Testes de segurança

- Feature test: usuário B tenta ler, editar e apagar recurso de A e recebe 403 ou 404.
- Payload com campo extra (`is_admin=1`) não altera o atributo.
- Rota de login retorna 429 após o limite.
- POST sem token CSRF retorna 419.
- Upload com extensão permitida e conteúdo diferente é rejeitado.
- Ferramentas opcionais: `composer audit`, Psalm com `--taint-analysis`, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/Laravel_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://laravel.com/docs/authorization
- https://laravel.com/docs/csrf
- https://laravel.com/docs/eloquent
- https://laravel.com/docs/validation
