# Spring — segurança

Última revisão: 2026-11-03

Escopo: Spring Boot 3.x com Spring Security 6.x, Java 17+, Spring MVC, Spring Data JPA e Thymeleaf quando houver renderização no servidor.

## Recomendações

- Configuração por bean `SecurityFilterChain` (o `WebSecurityConfigurerAdapter` foi removido no Spring Security 6). Em `authorizeHttpRequests`, termine com `.anyRequest().authenticated()` ou `.denyAll()`, para rota nova não nascer aberta.
- Autorização por método: `@EnableMethodSecurity` e `@PreAuthorize`/`@PostAuthorize` nas operações sensíveis. Checagem de dono no serviço ou na query (`findByIdAndOwnerId`), não só por papel.
- CSRF vem ligado. Desligue apenas em API stateless autenticada por header (bearer); com sessão por cookie, mantenha.
- Senhas: `PasswordEncoderFactories.createDelegatingPasswordEncoder()` (bcrypt por padrão, com prefixo de algoritmo) ou `BCryptPasswordEncoder`/`Argon2PasswordEncoder`. Nunca `NoOpPasswordEncoder` fora de teste.
- Binding: receba DTOs (records) com Bean Validation (`@Valid`, `@NotBlank`, `@Size`). Não use entidade JPA como `@RequestBody`.
- JPA: parâmetros nomeados em JPQL e native query (`:email`), Criteria API ou derived queries. Nunca concatenar entrada na string da query. `Sort` vindo do usuário com allowlist de propriedades.
- Thymeleaf: `th:text` escapa; `th:utext` só com HTML sanitizado.
- SpEL: nunca avalie expressão construída com entrada externa.
- Jackson: não ative `activateDefaultTyping`/tipagem polimórfica global para dado externo; em polimorfismo, use `@JsonTypeInfo` com subtipos declarados.
- XML: configure o parser contra XXE (desabilite DTD/entidades externas no `DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`).
- Actuator: por padrão só `health` é exposto via HTTP. Expanda `management.endpoints.web.exposure.include` só com autenticação; `env`, `heapdump`, `configprops` e `loggers` vazam segredos ou permitem alterar comportamento.
- Erros: mantenha `server.error.include-stacktrace=never` e `include-message` desligado em produção.
- Sessão: `sessionFixation` padrão (migra a sessão no login) não deve ser desligado; cookie `Secure` e `HttpOnly`.
- CORS: configuração explícita no `SecurityFilterChain` com origens listadas.
- Segredos em variáveis de ambiente ou cofre, não em `application.yml` commitado.
- Dependências: OWASP Dependency-Check ou o scanner do repositório no CI; mantenha o BOM do Spring Boot atualizado.

## Vulnerabilidades comuns

- `permitAll()` amplo demais por matcher genérico (`/api/**`).
- IDOR: `repository.findById(id)` sem checar o dono.
- SQL injection em `@Query(nativeQuery = true)` montada com concatenação ou em `entityManager.createQuery("... " + nome)`.
- Mass assignment por `@RequestBody User`.
- Actuator `env` ou `heapdump` exposto sem autenticação.
- XSS por `th:utext`.
- Desserialização insegura com tipagem padrão do Jackson.
- CSRF desligado em app com login por formulário.

## Implementação segura

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

## Implementação inadequada e risco

```java
@PutMapping("/projects/{id}")
public Project update(@PathVariable Long id, @RequestBody Project project) {
    project.setId(id);
    return projects.save(project);
}

em.createNativeQuery("SELECT * FROM project WHERE name = '" + name + "'");
```

Risco: qualquer usuário sobrescreve qualquer projeto, inclusive o dono e campos internos; a query nativa concatenada permite injeção de SQL.

## Testes de segurança

- `spring-security-test` com MockMvc: anônimo → 401/redirect; `@WithMockUser` de outro usuário → 404 ou 403.
- POST com sessão sem `.with(csrf())` → 403 quando CSRF está ativo.
- Corpo com campo não previsto no DTO não altera a entidade.
- `GET /actuator/env` sem credencial → 401 ou 404.
- Ferramentas opcionais: SpotBugs com Find Security Bugs, OWASP Dependency-Check, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/Java_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Mass_Assignment_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Query_Parameterization_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://docs.spring.io/spring-security/reference/
- https://docs.spring.io/spring-boot/
