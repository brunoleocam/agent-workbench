# Spring — security

Last reviewed: 2026-11-03

Scope: Spring Boot 3.x with Spring Security 6.x, Java 17+, Spring MVC, Spring Data JPA, and Thymeleaf when there is server-side rendering.

## Recommendations

- Configure through a `SecurityFilterChain` bean (`WebSecurityConfigurerAdapter` was removed in Spring Security 6). In `authorizeHttpRequests`, end with `.anyRequest().authenticated()` or `.denyAll()`, so a new route is not born open.
- Method authorization: `@EnableMethodSecurity` and `@PreAuthorize`/`@PostAuthorize` on sensitive operations. Check ownership in the service or in the query (`findByIdAndOwnerId`), not only by role.
- CSRF comes on. Turn it off only on a stateless API authenticated by a header (bearer); with a cookie session, keep it.
- Passwords: `PasswordEncoderFactories.createDelegatingPasswordEncoder()` (bcrypt by default, with an algorithm prefix) or `BCryptPasswordEncoder`/`Argon2PasswordEncoder`. Never `NoOpPasswordEncoder` outside tests.
- Binding: receive DTOs (records) with Bean Validation (`@Valid`, `@NotBlank`, `@Size`). Do not use a JPA entity as a `@RequestBody`.
- JPA: named parameters in JPQL and native queries (`:email`), the Criteria API, or derived queries. Never concatenate input into the query string. A `Sort` coming from the user with an allowlist of properties.
- Thymeleaf: `th:text` escapes; `th:utext` only with sanitized HTML.
- SpEL: never evaluate an expression built with external input.
- Jackson: do not enable `activateDefaultTyping`/global polymorphic typing for external data; for polymorphism, use `@JsonTypeInfo` with declared subtypes.
- XML: configure the parser against XXE (disable DTDs/external entities in `DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`).
- Actuator: by default only `health` is exposed over HTTP. Expand `management.endpoints.web.exposure.include` only with authentication; `env`, `heapdump`, `configprops`, and `loggers` leak secrets or allow changing behavior.
- Errors: keep `server.error.include-stacktrace=never` and `include-message` off in production.
- Session: the default `sessionFixation` (migrates the session at login) must not be turned off; `Secure` and `HttpOnly` cookie.
- CORS: explicit configuration in the `SecurityFilterChain` with listed origins.
- Secrets in environment variables or a vault, not in a committed `application.yml`.
- Dependencies: OWASP Dependency-Check or the repository's scanner in CI; keep the Spring Boot BOM updated.

## Common vulnerabilities

- A `permitAll()` that is too broad because of a generic matcher (`/api/**`).
- IDOR: `repository.findById(id)` without checking the owner.
- SQL injection in `@Query(nativeQuery = true)` built by concatenation or in `entityManager.createQuery("... " + name)`.
- Mass assignment through `@RequestBody User`.
- Actuator `env` or `heapdump` exposed without authentication.
- XSS by `th:utext`.
- Insecure deserialization with Jackson's default typing.
- CSRF turned off in an app with form login.

## Secure implementation

```java
@Bean
SecurityFilterChain api(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/public/**").permitAll()
            .anyRequest().authenticated())
        .formLogin(Customizer.withDefaults());
    return http.build();
}

public record RenameDto(@NotBlank @Size(max = 100) String name) {}

@PutMapping("/projects/{id}")
public ProjectView rename(@PathVariable Long id, @Valid @RequestBody RenameDto dto,
                          @AuthenticationPrincipal UserDetails user) {
    Project p = projects.findByIdAndOwnerUsername(id, user.getUsername())
        .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND));
    p.setName(dto.name());
    return ProjectView.from(projects.save(p));
}
```

## Inadequate implementation and risk

```java
@PutMapping("/projects/{id}")
public Project update(@PathVariable Long id, @RequestBody Project project) {
    project.setId(id);
    return projects.save(project);
}

em.createNativeQuery("SELECT * FROM project WHERE name = '" + name + "'");
```

Risk: any user overwrites any project, including the owner and internal fields; the concatenated native query allows SQL injection.

## Security tests

- `spring-security-test` with MockMvc: anonymous → 401/redirect; another user's `@WithMockUser` → 404 or 403.
- A POST with a session without `.with(csrf())` → 403 when CSRF is active.
- A body with a field not expected by the DTO does not change the entity.
- `GET /actuator/env` without credentials → 401 or 404.
- Optional tools: SpotBugs with Find Security Bugs, OWASP Dependency-Check, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/Java_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://docs.spring.io/spring-security/reference/
- https://docs.spring.io/spring-boot/
