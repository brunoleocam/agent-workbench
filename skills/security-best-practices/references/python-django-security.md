# Django — security

Last reviewed: 2026-11-03

Scope: Django 4.2 LTS and 5.x, Python 3.10+, with the ORM, templates, and default middleware. Django REST Framework covered in the essentials. General Python rules are in `python-general-web-security.md`.

## Recommendations

- Production: `DEBUG = False`, `SECRET_KEY` from the environment, explicit `ALLOWED_HOSTS`. Run `python manage.py check --deploy` and address the warnings.
- HTTPS: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (start low and increase). Behind a TLS proxy, `SECURE_PROXY_SSL_HEADER` only if the proxy overwrites the header.
- Middleware: keep `SecurityMiddleware`, `CsrfViewMiddleware`, `XFrameOptionsMiddleware`.
- CSRF: `{% csrf_token %}` in POST forms. `@csrf_exempt` only for an endpoint with other authentication (a webhook signature). In Django 4.0+, trusted HTTPS origins in `CSRF_TRUSTED_ORIGINS` need the scheme.
- Templates: autoescape on. `|safe`, `mark_safe`, and `{% autoescape off %}` only on sanitized HTML. Data for JS via `json_script`.
- The ORM parameterizes. In `raw()`, `RawSQL`, and `cursor.execute`, pass `params`. Avoid `extra()`. A field name from the user in `order_by` only through an allowlist.
- Per-object authorization: `get_object_or_404(Invoice, pk=pk, owner=request.user)` or a filtered queryset. `@login_required` and `LoginRequiredMixin` do not check ownership. Django 5.1 has `LoginRequiredMiddleware` to require login by default.
- Forms: `ModelForm` with explicit `fields`, never `"__all__"` on a form exposed to ordinary users.
- DRF: a restrictive `DEFAULT_PERMISSION_CLASSES` (the default is `AllowAny`), `get_queryset()` filtered by the user, serializers with explicit `fields` and `read_only_fields` for privileged fields, throttling on authentication.
- Passwords: default hashers (PBKDF2, or Argon2 by installing `argon2-cffi`) and `AUTH_PASSWORD_VALIDATORS` active.
- Redirect: validate `next` with `url_has_allowed_host_and_scheme()`.
- Uploads: appropriate `FILE_UPLOAD_MAX_MEMORY_SIZE` and `DATA_UPLOAD_MAX_MEMORY_SIZE`, type validation, `MEDIA_ROOT` served without execution and, for private files, through an authorized view.
- Admin: a non-obvious URL is not a control; require staff users with strong passwords and, if possible, MFA and network restriction.
- Dependencies: `pip-audit` in CI; update within the LTS series.

## Common vulnerabilities

- `DEBUG = True` in production exposing settings and tracebacks.
- IDOR: `Invoice.objects.get(pk=pk)` in a view with `@login_required`.
- XSS by `{{ bio|safe }}`.
- SQL injection in `raw(f"... {q}")` or `extra(where=[...])` built with a string.
- A DRF ViewSet without permissions, inheriting `AllowAny`.
- A serializer `fields = "__all__"` accepting `is_staff`.
- Open redirect through `?next=` without validation.

## Secure implementation

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

## Inadequate implementation and risk

```python
@login_required
def invoice_detail(request, pk):
    invoice = Invoice.objects.get(pk=pk)
    return render(request, "invoices/detail.html", {"invoice": invoice})

rows = Invoice.objects.raw(f"SELECT * FROM billing_invoice WHERE number = '{number}'")
```

Risk: any logged-in user reads another user's invoice by changing the `pk`; the raw query allows SQL injection with the supplied number.

## Security tests

- `TestCase` with two users: B gets 404 when accessing A's object in views and DRF endpoints.
- `Client(enforce_csrf_checks=True)`: a POST without a token returns 403.
- A template rendered with `<script>` shows the escaped text.
- `next=https://evil.example` falls back to the default.
- `manage.py check --deploy` with no unjustified warnings.
- Optional tools: Bandit, `pip-audit`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/Django_Security_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Django_REST_Framework_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://docs.djangoproject.com/en/stable/topics/security/
- https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
- https://docs.djangoproject.com/en/stable/ref/csrf/
- https://www.django-rest-framework.org/api-guide/permissions/
