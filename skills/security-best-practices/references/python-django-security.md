# Django — segurança

Última revisão: 2026-11-03

Escopo: Django 4.2 LTS e 5.x, Python 3.10+, com ORM, templates e middleware padrão. Django REST Framework coberto no essencial. Regras gerais de Python estão em `python-general-web-security.md`.

## Recomendações

- Produção: `DEBUG = False`, `SECRET_KEY` do ambiente, `ALLOWED_HOSTS` explícito. Rode `python manage.py check --deploy` e trate os avisos.
- HTTPS: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (comece baixo e aumente). Atrás de proxy TLS, `SECURE_PROXY_SSL_HEADER` só se o proxy sobrescrever o header.
- Middleware: mantenha `SecurityMiddleware`, `CsrfViewMiddleware`, `XFrameOptionsMiddleware`.
- CSRF: `{% csrf_token %}` em formulários POST. `@csrf_exempt` só para endpoint com outra autenticação (assinatura de webhook). Em Django 4.0+, origens HTTPS confiáveis em `CSRF_TRUSTED_ORIGINS` precisam do esquema.
- Templates: autoescape ligado. `|safe`, `mark_safe` e `{% autoescape off %}` só em HTML sanitizado. Dado para JS via `json_script`.
- ORM parametriza. Em `raw()`, `RawSQL` e `cursor.execute`, passe `params`. Evite `extra()`. Nome de campo vindo do usuário em `order_by` só por allowlist.
- Autorização por objeto: `get_object_or_404(Invoice, pk=pk, owner=request.user)` ou queryset filtrado. `@login_required` e `LoginRequiredMixin` não checam dono. Django 5.1 tem `LoginRequiredMiddleware` para exigir login por padrão.
- Forms: `ModelForm` com `fields` explícito, nunca `"__all__"` em form exposto a usuário comum.
- DRF: `DEFAULT_PERMISSION_CLASSES` restritivo (o padrão é `AllowAny`), `get_queryset()` filtrado pelo usuário, serializers com `fields` explícitos e `read_only_fields` para campos privilegiados, throttling em autenticação.
- Senhas: hashers padrão (PBKDF2, ou Argon2 instalando `argon2-cffi`) e `AUTH_PASSWORD_VALIDATORS` ativos.
- Redirect: valide `next` com `url_has_allowed_host_and_scheme()`.
- Uploads: `FILE_UPLOAD_MAX_MEMORY_SIZE` e `DATA_UPLOAD_MAX_MEMORY_SIZE` adequados, validação de tipo, `MEDIA_ROOT` servido sem execução e, para arquivo privado, por view autorizada.
- Admin: URL não óbvia não é controle; exija usuários staff com senha forte e, se possível, MFA e restrição de rede.
- Dependências: `pip-audit` no CI; atualize dentro da série LTS.

## Vulnerabilidades comuns

- `DEBUG = True` em produção expondo settings e traceback.
- IDOR: `Invoice.objects.get(pk=pk)` em view com `@login_required`.
- XSS por `{{ bio|safe }}`.
- SQL injection em `raw(f"... {q}")` ou `extra(where=[...])` montado com string.
- ViewSet DRF sem permissão, herdando `AllowAny`.
- Serializer `fields = "__all__"` aceitando `is_staff`.
- Open redirect por `?next=` sem validação.

## Implementação segura

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk, owner=request.user)
    return render(request, "invoices/detail.html", {"invoice": invoice})

def after_login(request):
    nxt = request.GET.get("next", "")
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        nxt = "/"
    return redirect(nxt)

rows = Invoice.objects.raw("SELECT * FROM billing_invoice WHERE number = %s", [number])
```

## Implementação inadequada e risco

```python
@login_required
def invoice_detail(request, pk):
    invoice = Invoice.objects.get(pk=pk)
    return render(request, "invoices/detail.html", {"invoice": invoice})

rows = Invoice.objects.raw(f"SELECT * FROM billing_invoice WHERE number = '{number}'")
```

Risco: qualquer usuário logado lê a fatura de outro trocando o `pk`; a query crua permite injeção de SQL com o número informado.

## Testes de segurança

- `TestCase` com dois usuários: B recebe 404 ao acessar objeto de A em views e endpoints DRF.
- `Client(enforce_csrf_checks=True)`: POST sem token retorna 403.
- Template renderizado com `<script>` mostra o texto escapado.
- `next=https://evil.example` cai no fallback.
- `manage.py check --deploy` sem avisos não justificados.
- Ferramentas opcionais: Bandit, `pip-audit`, Semgrep.

## Fontes

- https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Django_REST_Framework_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://docs.djangoproject.com/en/stable/topics/security/
- https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- https://docs.djangoproject.com/en/stable/ref/csrf/
- https://www.django-rest-framework.org/api-guide/permissions/
