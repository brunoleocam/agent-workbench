# Laravel — security

Last reviewed: 2026-11-03

Scope: Laravel 10+ and 11 on PHP 8.1+ (Laravel 11 requires PHP 8.2+), with Eloquent, Blade, and the default middleware stack. Plain PHP rules are in `php-general-web-security.md`.

## Recommendations

- Authorization: Policies or Gates on every action over a resource that has an owner. `Gate::authorize('update', $post)` or `$this->authorize(...)` when the controller uses `AuthorizesRequests` (Laravel 11's base controller does not include the trait by default). The `auth` middleware only authenticates, it does not authorize.
- Owner scoping: prefer `$request->user()->orders()->findOrFail($id)` over `Order::findOrFail($id)`.
- Mass assignment: declare `$fillable` (or a restrictive `$guarded`) on every model. Use `$request->validated()` or `$request->safe()->only([...])`, never `$request->all()` in `create`/`update`. Do not turn off the protection with `Model::unguard()` outside seeders.
- Validation: Form Requests with explicit rules. In `exists`/`unique`, restrict columns and scope.
- SQL: the Query Builder and Eloquent parameterize. In `whereRaw`, `selectRaw`, `orderByRaw`, and `DB::raw`, pass bindings (`whereRaw('price > ?', [$min])`). A sort column coming from the user only through an allowlist.
- Blade: `{{ }}` escapes. `{!! !!}` only with HTML sanitized on the server. Data for JavaScript via `@json` / `Js::from`.
- CSRF: `@csrf` in forms. In Laravel 11, exceptions go in `bootstrap/app.php` (`$middleware->validateCsrfTokens(except: [...])`); in 10, in `VerifyCsrfToken::$except`. An exception only for a webhook with a verified signature.
- Configuration: `APP_DEBUG=false` and `APP_ENV=production` in production. `APP_KEY` secret and outside the repository; changing it invalidates encrypted data and sessions.
- Password: `Hash::make()` and `Hash::check()` (bcrypt or argon2 per `config/hashing.php`). Password reset through the native broker.
- Rate limit: `throttle` on login, password reset, OTP, and expensive endpoints (`RateLimiter::for`).
- Upload: the `file`, `mimes`/`mimetypes`, and `max` rules. `$file->store('dir')` generates a random name; do not use `getClientOriginalName()` as a path. A private disk for sensitive files; delivery through an authorized route or `temporaryUrl`.
- Sensitive links: `URL::signedRoute()` / `temporarySignedRoute()` with the `signed` middleware.
- Redirect: `redirect()->intended()` or named routes; do not redirect to an arbitrary URL from the request.
- Dependencies: `composer audit` in CI.

## Common vulnerabilities

- IDOR through route model binding without a policy (`/invoices/{invoice}`).
- Mass assignment of `is_admin`, `role`, or `user_id` via `$request->all()`.
- XSS by `{!! $comment !!}`.
- SQL injection in `whereRaw("name = '$name'")` or `orderBy($request->sort)`.
- `APP_DEBUG=true` in production exposing stack traces, environment variables, and queries.
- `.env` reachable from the web when the document root does not point to `public/`.
- A webhook excluded from CSRF without verifying the signature.

## Secure implementation

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

## Inadequate implementation and risk

```php
public function update(Request $request, $id)
{
    $post = Post::find($id);
    $post->update($request->all());
}
```

Risk: any authenticated user changes another user's post (IDOR), and fields not expected in the form, such as `user_id` or `published`, are written if the model does not protect them.

## Security tests

- Feature test: user B tries to read, edit, and delete A's resource and gets 403 or 404.
- A payload with an extra field (`is_admin=1`) does not change the attribute.
- The login route returns 429 after the limit.
- A POST without a CSRF token returns 419.
- An upload with an allowed extension and different content is rejected.
- Optional tools: `composer audit`, Psalm with `--taint-analysis`, Semgrep.

## Sources

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
