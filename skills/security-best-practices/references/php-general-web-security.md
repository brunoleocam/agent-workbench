# PHP — segurança

Última revisão: 2026-11-03

Escopo: PHP 8.1+ em aplicação web sem framework, ou com framework sem referência dedicada (Slim, CodeIgniter, código legado). Para Laravel use `php-laravel-security.md`.

## Recomendações

- Banco: PDO ou mysqli com prepared statements. No PDO, `PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION` e `PDO::ATTR_EMULATE_PREPARES => false`. Nome de tabela, coluna ou direção de `ORDER BY` não aceita placeholder: use allowlist.
- Saída HTML: `htmlspecialchars($v, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')` no ponto de saída. Em atributo `href`, valide também o esquema (`https:`), porque escapar não bloqueia `javascript:`.
- Senha: `password_hash($senha, PASSWORD_DEFAULT)` e `password_verify()`. Chame `password_needs_rehash()` no login para migrar o algoritmo.
- Aleatoriedade: `random_bytes()` e `random_int()`. Nunca `rand()`, `mt_rand()` ou `uniqid()` para token.
- Comparação de segredo: `hash_equals()`. Comparações em geral com `===`.
- Sessão: `session.use_strict_mode=1`, `session.cookie_httponly=1`, `session.cookie_secure=1`, `session.cookie_samesite=Lax` (ou `Strict`). `session_regenerate_id(true)` após login e troca de privilégio.
- CSRF: token por sessão em todo formulário que muda estado, conferido com `hash_equals()`. SameSite ajuda, não substitui.
- Produção: `display_errors=Off`, `log_errors=On`, `expose_php=Off`. Erro detalhado só no log.
- Upload: tamanho máximo, tipo verificado pelo conteúdo (`finfo_file`), nome gerado pelo servidor, gravação fora do document root, `move_uploaded_file()`.
- Comando externo: evite. Se inevitável, `escapeshellarg()` por argumento, ou `proc_open()` com array de argumentos (PHP 7.4+), que não passa pelo shell.
- Desserialização: `json_decode()` para dado externo. `unserialize()` só em dado confiável, com `['allowed_classes' => false]`.
- `include`/`require` nunca com caminho vindo do usuário; mapeie por allowlist.
- Dependências: `composer audit` (Composer 2.4+) no CI.

## Vulnerabilidades comuns

- SQL injection por interpolação de variável na query.
- XSS por `echo` sem escape, inclusive em mensagem de erro e atributo.
- Object injection via `unserialize()` em cookie ou parâmetro, explorando magic methods (`__wakeup`, `__destruct`) de classes carregadas.
- Local/remote file inclusion por `include $_GET['page']`.
- Path traversal em download: `readfile('files/' . $_GET['f'])` com `../`.
- Session fixation por não regenerar o ID no login.
- Type juggling em comparação frouxa (`==`) de hash ou token.
- Upload de `.php` executável no document root.
- Command injection com `exec`, `system`, `shell_exec` ou crase.

## Implementação segura

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

## Implementação inadequada e risco

```php
$rows = $pdo->query("SELECT * FROM users WHERE email = '{$_GET['email']}'");
echo "Olá, " . $_GET['name'];
$prefs = unserialize($_COOKIE['prefs']);
```

Risco: a primeira linha permite ler ou alterar o banco (`' OR '1'='1`); a segunda executa script no navegador da vítima por link; a terceira entrega ao atacante a criação de objetos arbitrários, que pode chegar a execução de código conforme as classes disponíveis.

## Testes de segurança

- Para cada query com entrada externa, um teste com aspas, `--` e `' OR '1'='1` que prova ausência de efeito.
- Saída com `<script>` e `"><img src=x onerror=...>` aparece escapada.
- Download com `../` e caminho absoluto retorna 404.
- ID de sessão muda após login.
- POST sem token CSRF ou com token errado é rejeitado.
- Ferramentas opcionais, se já estiverem no projeto: `composer audit`, Psalm com `--taint-analysis`, Semgrep.

## Fontes

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
