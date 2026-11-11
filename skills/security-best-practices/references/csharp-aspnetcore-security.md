# ASP.NET Core — security

Last reviewed: 2026-11-03

Scope: ASP.NET Core 8 (LTS) and later, C#, with MVC, Razor Pages, or Minimal APIs, and Entity Framework Core 8.

## Recommendations

- Authorization by default: define a `FallbackPolicy` that requires an authenticated user and open up the public parts with `[AllowAnonymous]` or `.AllowAnonymous()`. That way a new endpoint is born protected.
- Per-resource authorization: `IAuthorizationService.AuthorizeAsync(User, resource, policy)` or a query filtered by owner. `[Authorize]` alone only requires login.
- Overposting: receive DTOs/view models with only the editable fields, never the EF entity directly in binding.
- EF Core: LINQ parameterizes. `FromSql`/`FromSqlInterpolated` and `ExecuteSql` turn interpolation into parameters. `FromSqlRaw`/`ExecuteSqlRaw` only with explicit parameters, never with a concatenated string.
- Razor escapes by default. `Html.Raw` and `MarkupString` (Blazor) only with sanitized HTML.
- Antiforgery: Razor Pages validates by default; in MVC use a global `AutoValidateAntiforgeryTokenAttribute` or `[ValidateAntiForgeryToken]`. In .NET 8, Minimal APIs that bind form data use `app.UseAntiforgery()`. An API with only a bearer token in the header does not need antiforgery; with a cookie, it does.
- Authentication cookies: `HttpOnly`, `SecurePolicy = Always`, appropriate `SameSite`.
- JWT bearer: validate issuer, audience, lifetime, and key (`TokenValidationParameters`); do not turn off validations to "make it work".
- HTTPS: `UseHttpsRedirection()` and `UseHsts()` outside development.
- Errors: `UseDeveloperExceptionPage` only in Development; production with `UseExceptionHandler` and ProblemDetails without a stack trace.
- Secrets: user-secrets in development; environment variables or a vault (e.g. Azure Key Vault) in production. Nothing in a committed `appsettings.json`.
- Protected data and your own tokens: the Data Protection API, with keys persisted and protected in a multi-instance environment.
- Rate limiting: the native middleware (`AddRateLimiter`/`UseRateLimiter`, .NET 7+) on login and expensive endpoints.
- CORS: a named policy with explicit origins; do not use `AllowAnyOrigin` with `AllowCredentials` (the framework refuses that combination).
- Serialization: do not use `BinaryFormatter` (obsolete). In `System.Text.Json`/Newtonsoft, do not enable polymorphic typing from the payload (`TypeNameHandling` other than `None`).
- Uploads: `[RequestSizeLimit]`, a server-generated name, storage outside `wwwroot`, content validation.
- Dependencies: `dotnet list package --vulnerable` in CI.

## Common vulnerabilities

- A controller without `[Authorize]` in an app with no fallback policy.
- IDOR: `_db.Orders.FindAsync(id)` without checking `UserId`.
- Overposting of `IsAdmin` when binding the entity.
- SQL injection with `FromSqlRaw($"... {name}")`.
- XSS by `@Html.Raw(Model.Bio)`.
- `TypeNameHandling.All` in Newtonsoft with external JSON.
- The development exception page active in production.

## Secure implementation

```csharp
builder.Services.AddAuthorization(o =>
    o.FallbackPolicy = new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build());

public record UpdateProfileDto(string DisplayName);

[HttpPut("profile/{id:int}")]
public async Task<IActionResult> Update(int id, UpdateProfileDto dto)
{
    var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
    var profile = await _db.Profiles.SingleOrDefaultAsync(p => p.Id == id && p.UserId == userId);
    if (profile is null) return NotFound();

    profile.DisplayName = dto.DisplayName;
    await _db.SaveChangesAsync();
    return NoContent();
}

var users = await _db.Users.FromSql($"SELECT * FROM Users WHERE Email = {email}").ToListAsync();
```

## Inadequate implementation and risk

```csharp
[HttpPut("profile")]
public async Task<IActionResult> Update(Profile profile)
{
    _db.Update(profile);
    await _db.SaveChangesAsync();
    return Ok(profile);
}

var users = _db.Users.FromSqlRaw("SELECT * FROM Users WHERE Email = '" + email + "'");
```

Risk: the client sends the whole entity and can change `UserId`, `IsAdmin`, or someone else's profile; the SQL concatenation allows injection.

## Security tests

- `WebApplicationFactory` (integration tests): an endpoint without a token → 401; user B on A's resource → 404 or 403.
- A body with `IsAdmin=true` does not change the field.
- A form POST without an antiforgery token → 400.
- An error response in the Production environment without a stack trace.
- Optional tools: .NET analyzers (security rules CA2100, CA3001, and the like), `dotnet list package --vulnerable`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/DotNet_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://learn.microsoft.com/en-us/aspnet/core/security/
- https://learn.microsoft.com/en-us/aspnet/core/security/anti-request-forgery
- https://learn.microsoft.com/en-us/aspnet/core/security/authorization/introduction
- https://learn.microsoft.com/en-us/ef/core/querying/sql-queries
