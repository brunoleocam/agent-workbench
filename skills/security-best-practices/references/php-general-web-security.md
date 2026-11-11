# PHP — security

Last reviewed: 2026-11-03

Scope: PHP 8.1+ in a web application without a framework, or with a framework that has no dedicated reference (Slim, CodeIgniter, legacy code). For Laravel use `php-laravel-security.md`.

## Recommendations

- Database: PDO or mysqli with prepared statements. In PDO, `PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION` and `PDO::ATTR_EMULATE_PREPARES => false`. A table name, column, or `ORDER BY` direction does not accept a placeholder: use an allowlist.
- HTML output: `htmlspecialchars($v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` at the point of output. In an `href` attribute, also validate the scheme (`https:`), because escaping does not block `javascript:`.
- Password: `password_hash($password, PASSWORD_DEFAULT)` and `password_verify()`. Call `password_needs_rehash()` at login to migrate the algorithm.
- Randomness: `random_bytes()` and `random_int()`. Never `rand()`, `mt_rand()`, or `uniqid()` for a token.
- Secret comparison: `hash_equals()`. Other comparisons with `===`.
- Session: `session.use_strict_mode=1`, `session.cookie_httponly=1`, `session.cookie_secure=1`, `session.cookie_samesite=Lax` (or `Strict`). `session_regenerate_id(true)` after login and on privilege change.
- CSRF: a per-session token on every state-changing form, checked with `hash_equals()`. SameSite helps, it does not replace it.
- Production: `display_errors=Off`, `log_errors=On`, `expose_php=Off`. Detailed errors only in the log.
- Upload: maximum size, type verified by content (`finfo_file`), server-generated name, stored outside the document root, `move_uploaded_file()`.
- External command: avoid. If unavoidable, `escapeshellarg()` per argument, or `proc_open()` with an argument array (PHP 7.4+), which does not go through the shell.
- Deserialization: `json_decode()` for external data. `unserialize()` only on trusted data, with `['allowed_classes' => false]`.
- `include`/`require` never with a user-supplied path; map through an allowlist.
- Dependencies: `composer audit` (Composer 2.4+) in CI.

## Common vulnerabilities

- SQL injection by interpolating a variable into the query.
- XSS by `echo` without escaping, including in error messages and attributes.
- Object injection via `unserialize()` on a cookie or parameter, exploiting magic methods (`__wakeup`, `__destruct`) of loaded classes.
- Local/remote file inclusion by `include $_GET['page']`.
- Path traversal in downloads: `readfile('files/' . $_GET['f'])` with `../`.
- Session fixation by not regenerating the ID at login.
- Type juggling in a loose (`==`) comparison of a hash or token.
- Upload of an executable `.php` in the document root.
- Command injection with `exec`, `system`, `shell_exec`, or backticks.

## Secure implementation

```php
$pdo = new PDO($dsn, $user, $pass, [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_EMULATE_PREPARES => false,
]);
$stmt = $pdo->prepare('SELECT id, name FROM users WHERE email = :email');
$stmt->execute(['email' => $email]);
$row = $stmt->fetch();

echo htmlspecialchars($row['name'] ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');

$base = realpath(__DIR__ . '/../storage/files');
$path = realpath($base . '/' . basename($_GET['f'] ?? ''));
if ($path === false || !str_starts_with($path, $base . DIRECTORY_SEPARATOR)) {
    http_response_code(404);
    exit;
}
```

## Inadequate implementation and risk

```php
$rows = $pdo->query("SELECT * FROM users WHERE email = '{$_GET['email']}'");
echo "Hello, " . $_GET['name'];
$prefs = unserialize($_COOKIE['prefs']);
```

Risk: the first line allows reading or changing the database (`' OR '1'='1`); the second runs script in the victim's browser through a link; the third lets the attacker create arbitrary objects, which can lead to code execution depending on the available classes.

## Security tests

- For each query with external input, a test with quotes, `--`, and `' OR '1'='1` that proves no effect.
- Output with `<script>` and `"><img src=x onerror=...>` appears escaped.
- A download with `../` and an absolute path returns 404.
- The session ID changes after login.
- A POST without a CSRF token or with a wrong one is rejected.
- Optional tools, if already in the project: `composer audit`, Psalm with `--taint-analysis`, Semgrep.

## Sources

- https://cheatsheetseries.owasp.org/cheatsheets/PHP_Configuration_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/Top10/
- https://www.php.net/manual/en/security.php
- https://www.php.net/manual/en/pdo.prepared-statements.php
- https://www.php.net/manual/en/function.password-hash.php
