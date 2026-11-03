---
name: security-best-practices
description: Applies stack-specific secure coding guidance while implementing or maintaining code, loading only the reference for the detected language and framework. Use when writing or changing code that touches input, auth, data access, files, secrets, or external calls (segurança, secure coding, boas práticas de segurança, vulnerabilidade, hardening).
---

# Secure coding na implementação

Use durante a implementação e a manutenção. Não substitui `/code-review` (requisito → código) nem `/security-review` (auditoria com relatório). Esta skill orienta o código enquanto ele é escrito.

## Procedimento

1. Identifique linguagem e framework.
   - Se existir `.cursor/agent-system/layout.json`, leia os campos `frameworks` e `security_references`.
   - Senão, leia só os manifests: `composer.json`, `package.json`, `pyproject.toml` ou `requirements*.txt`, `*.csproj`, `pom.xml` ou `build.gradle*`.
2. Carregue só a referência da stack em uso, pela tabela abaixo. Duas no máximo quando a mudança cruza camadas (ex.: API Express e front React). Nunca carregue todas.
3. Aplique as recomendações ao trecho que está mudando. Não reescreva código fora do escopo da tarefa.
4. Ao notar vulnerabilidade relevante, avise com arquivo e linha, mesmo fora do escopo. Corrigir fora do escopo vira `/change-request` ou `/bug-fix`.
5. Diferencie:
   - vulnerabilidade efetiva: há entrada controlável e caminho até o impacto;
   - hardening: falta uma defesa recomendada, sem caminho de exploração demonstrado.

   Não apresente hardening como vulnerabilidade.

## Referências por stack

| Stack | Referência |
|---|---|
| PHP sem framework ou framework não listado | [references/php-general-web-security.md](references/php-general-web-security.md) |
| Laravel | [references/php-laravel-security.md](references/php-laravel-security.md) |
| Node.js com Express | [references/javascript-express-security.md](references/javascript-express-security.md) |
| React (SPA, Vite, CRA) | [references/javascript-typescript-react-security.md](references/javascript-typescript-react-security.md) |
| Next.js | [references/javascript-typescript-nextjs-security.md](references/javascript-typescript-nextjs-security.md) |
| Python web sem framework listado (Flask etc.) | [references/python-general-web-security.md](references/python-general-web-security.md) |
| FastAPI | [references/python-fastapi-security.md](references/python-fastapi-security.md) |
| Django | [references/python-django-security.md](references/python-django-security.md) |
| ASP.NET Core | [references/csharp-aspnetcore-security.md](references/csharp-aspnetcore-security.md) |
| Spring Boot / Spring Security | [references/java-spring-security.md](references/java-spring-security.md) |

Next.js já cobre React; não carregue as duas. Stack fora da tabela: use as páginas do OWASP Cheat Sheet Series citadas na referência mais próxima e diga que não há referência dedicada.

## Lições do projeto

Lições confirmadas de segurança deste projeto:

```bash
python .cursor/agent-system/scripts/lessons.py list --status confirmed --category security
```

Rode só se o projeto tiver `.cursor/agent-system/`. Lição confirmada vale mais que recomendação genérica quando as duas conflitam; cite qual aplicou.

## Saída

Ao fim do passo, informe em poucas linhas: referência carregada, recomendações aplicadas, alertas (vulnerabilidade ou hardening, com arquivo e linha). Sem alerta, diga isso.
