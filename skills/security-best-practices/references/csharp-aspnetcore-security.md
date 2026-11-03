# ASP.NET Core — segurança

Última revisão: 2026-11-03

Escopo: ASP.NET Core 8 (LTS) e posteriores, C#, com MVC, Razor Pages ou Minimal APIs, e Entity Framework Core 8.

## Recomendações

- Autorização por padrão: defina `FallbackPolicy` que exige usuário autenticado e libere o público com `[AllowAnonymous]` ou `.AllowAnonymous()`. Assim um endpoint novo nasce protegido.
- Autorização por recurso: `IAuthorizationService.AuthorizeAsync(User, recurso, policy)` ou consulta filtrada pelo dono. `[Authorize]` sozinho só exige login.
- Overposting: receba DTOs/view models com apenas os campos editáveis, nunca a entidade EF direto no binding.
- EF Core: LINQ parametriza. `FromSql`/`FromSqlInterpolated` e `ExecuteSql` convertem a interpolação em parâmetros. `FromSqlRaw`/`ExecuteSqlRaw` só com parâmetros explícitos, nunca com string concatenada.
- Razor escapa por padrão. `Html.Raw` e `MarkupString` (Blazor) só com HTML sanitizado.
- Antiforgery: Razor Pages valida por padrão; em MVC use `AutoValidateAntiforgeryTokenAttribute` global ou `[ValidateAntiForgeryToken]`. Em .NET 8, Minimal APIs que fazem binding de formulário usam `app.UseAntiforgery()`. API só com bearer token no header não precisa de antiforgery; com cookie, precisa.
- Cookies de autenticação: `HttpOnly`, `SecurePolicy = Always`, `SameSite` adequado.
- JWT bearer: valide emissor, audiência, tempo de vida e chave (`TokenValidationParameters`); não desligue validações para "fazer funcionar".
- HTTPS: `UseHttpsRedirection()` e `UseHsts()` fora de desenvolvimento.
- Erros: `UseDeveloperExceptionPage` só em Development; produção com `UseExceptionHandler` e ProblemDetails sem stack trace.
- Segredos: user-secrets em desenvolvimento; variáveis de ambiente ou cofre (ex.: Azure Key Vault) em produção. Nada em `appsettings.json` commitado.
- Dados protegidos e tokens próprios: Data Protection API, com chaves persistidas e protegidas em ambiente com várias instâncias.
- Rate limiting: middleware nativo (`AddRateLimiter`/`UseRateLimiter`, .NET 7+) em login e endpoints caros.
- CORS: política nomeada com origens explícitas; não use `AllowAnyOrigin` com `AllowCredentials` (o framework recusa essa combinação).
- Serialização: não use `BinaryFormatter` (obsoleto). Em `System.Text.Json`/Newtonsoft, não habilite tipagem polimórfica a partir do payload (`TypeNameHandling` diferente de `None`).
- Uploads: `[RequestSizeLimit]`, nome gerado no servidor, armazenamento fora de `wwwroot`, validação de conteúdo.
- Dependências: `dotnet list package --vulnerable` no CI.

## Vulnerabilidades comuns

- Controller sem `[Authorize]` num app sem fallback policy.
- IDOR: `_db.Orders.FindAsync(id)` sem checar `UserId`.
- Overposting de `IsAdmin` ao bindar a entidade.
- SQL injection com `FromSqlRaw($"... {nome}")`.
- XSS por `@Html.Raw(Model.Bio)`.
- `TypeNameHandling.All` no Newtonsoft com JSON externo.
- Página de exceção de desenvolvimento ativa em produção.

## Implementação segura

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

## Implementação inadequada e risco

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

Risco: o cliente envia a entidade inteira e pode trocar `UserId`, `IsAdmin` ou o perfil de outra pessoa; a concatenação no SQL permite injeção.

## Testes de segurança

- `WebApplicationFactory` (testes de integração): endpoint sem token → 401; usuário B no recurso de A → 404 ou 403.
- Corpo com `IsAdmin=true` não altera o campo.
- POST de formulário sem antiforgery token → 400.
- Resposta de erro em ambiente Production sem stack trace.
- Ferramentas opcionais: analisadores .NET (regras de segurança CA2100, CA3001 e afins), `dotnet list package --vulnerable`, Semgrep.

## Fontes

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
