---
name: security-best-practices
description: Applies stack-specific secure coding guidance while implementing or maintaining code, loading only the reference for the detected language and framework. Use when writing or changing code that touches input, auth, data access, files, secrets, or external calls (segurança, secure coding, boas práticas de segurança, vulnerabilidade, hardening).
---

# Secure coding during implementation

Use it during implementation and maintenance. It does not replace `/code-review` (requirement → code) or `/security-review` (audit with a report). This skill guides the code while it is being written.

## Procedure

1. Identify the language and framework.
   - If `.cursor/agent-system/layout.json` exists, read the `frameworks` and `security_references` fields.
   - Otherwise, read only the manifests: `composer.json`, `package.json`, `pyproject.toml` or `requirements*.txt`, `*.csproj`, `pom.xml` or `build.gradle*`.
2. Load only the reference for the stack in use, from the table below. Two at most when the change crosses layers (e.g. Express API and React front end). Never load all of them.
3. Apply the recommendations to the code being changed. Do not rewrite code outside the task's scope.
4. When you notice a relevant vulnerability, flag it with file and line, even out of scope. Fixing out of scope becomes `/change-request` or `/bug-fix`.
5. Distinguish:
   - effective vulnerability: there is controllable input and a path to impact;
   - hardening: a recommended defense is missing, with no demonstrated exploitation path.

   Do not present hardening as a vulnerability.

## References by stack

| Stack | Reference |
|---|---|
| PHP without a framework or an unlisted framework | [references/php-general-web-security.md](references/php-general-web-security.md) |
| Laravel | [references/php-laravel-security.md](references/php-laravel-security.md) |
| Node.js with Express | [references/javascript-express-security.md](references/javascript-express-security.md) |
| React (SPA, Vite, CRA) | [references/javascript-typescript-react-security.md](references/javascript-typescript-react-security.md) |
| Next.js | [references/javascript-typescript-nextjs-security.md](references/javascript-typescript-nextjs-security.md) |
| Python web without a listed framework (Flask etc.) | [references/python-general-web-security.md](references/python-general-web-security.md) |
| FastAPI | [references/python-fastapi-security.md](references/python-fastapi-security.md) |
| Django | [references/python-django-security.md](references/python-django-security.md) |
| ASP.NET Core | [references/csharp-aspnetcore-security.md](references/csharp-aspnetcore-security.md) |
| Spring Boot / Spring Security | [references/java-spring-security.md](references/java-spring-security.md) |

Next.js already covers React; do not load both. A stack outside the table: use the OWASP Cheat Sheet Series pages cited in the closest reference and say there is no dedicated reference.

## Project lessons

This project's confirmed security lessons:

```bash
python .cursor/agent-system/scripts/lessons.py list --status confirmed --category security
```

Run only if the project has `.cursor/agent-system/`. A confirmed lesson outranks generic advice when the two conflict; cite which one you applied.

## Output

At the end of the step, report in a few lines: reference loaded, recommendations applied, alerts (vulnerability or hardening, with file and line). With no alert, say so.
