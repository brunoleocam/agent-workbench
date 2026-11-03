---
status: PASS
reviewer: security-review (built-in)
---
# Security review: evolução do harness

Escopo: mudanças não commitadas da branch `feat/harness-evolution`. Risco declarado na spec: MEDIUM (execução de comando, sistema de arquivos, segredo em log). A revisão não é obrigatória no gate para MEDIUM; está registrada como evidência. Os achados abaixo vêm da primeira revisão de segurança e do reviewer; o status de cada um foi atualizado depois da correção e precisa ser confirmado pela revisão final.

### SEC-001: código inline com `python -c` / `node -e` passava pela política de comandos
- Severity: MEDIUM
- Status: resolved
- File: agent-system/scripts/check_proofs.py
- Evidence: `policy_refusal` permitia interpretadores com `-c`/`-e`; um TEST em `docs/tasks/*.md` executava código arbitrário quando alguém rodava `check_proofs.py`.
- Recommendation: aplicado. `inline_code` recusa `python -c` (inclusive flags combinadas como `-Bc`), `node -e/--eval/-p`, `bun -e`, `deno eval`, `deno run <URL>`, `ruby -e` e `php -r`; `wrapped_command` aplica a mesma política ao comando de `uv run`, `poetry run`, `hatch run`, `pnpm exec`, `yarn exec/node` e `bundle exec`; trechos de comando shell também são checados, inclusive depois de `env`/`xargs`, e substituição de shell e heredoc são recusados. Depois da revisão independente (FIND-011 a FIND-013) também recusa `python -m` fora da lista de módulos de teste e dos módulos do projeto, `python3.x`/`pypy`, `ruby -we`, `rake -e`, `bash -ec`, `node --import data:`, `npm it`/`npm x`/`npx` e subcomando depois de flag com valor (`pnpm --filter x add`), sem recusar `uv run --package x pytest`. `--allow-inline` libera com autorização do usuário. Cobertura: `test_inline_code_refused_by_default`; fixtures convertidas para arquivos de teste.

### SEC-002: timeline renderizada sem nova redação
- Severity: LOW
- Status: resolved
- File: agent-system/scripts/timeline_view.py
- Evidence: `summary`, `result` e `files` iam para a saída e para `TIMELINE.md` como estavam na JSONL; evento antigo ou escrito por outra ferramenta podia conter segredo.
- Recommendation: aplicado `redact` e `safe_files` na renderização e linhas inválidas ignoradas; coberto por `test_new_semantic_events_update_state`.

### SEC-003: token em `Authorization: Bearer` gravado na timeline
- Severity: MEDIUM
- Status: resolved
- File: agent-system/scripts/lib.py
- Evidence: achado FIND-003 do reviewer; só a palavra `Bearer` era mascarada.
- Recommendation: padrões `AUTH_HEADER` e `AUTH_SCHEME`; coberto por `test_hook_marks_inferred_and_redacts`.

### SEC-004: `Shell: yes` desligava a recusa de instalação
- Severity: LOW
- Status: resolved
- File: agent-system/scripts/check_proofs.py
- Evidence: achado FIND-005 do reviewer.
- Recommendation: `shell_refusal` aplica a política (instalação e código inline) a cada trecho; coberto por `test_check_proofs_policy` e `test_inline_code_refused_by_default`.

### SEC-005: interpretador iniciado por gerenciador de pacotes escapava da recusa de código inline
- Severity: MEDIUM
- Status: resolved
- Evidence: revisão de segurança final reproduziu `yarn run node -e 1` e `pnpm node -e 1` passando sem `--allow-inline`.
- Recommendation: aplicado. `runner_target` aplica a política ao interpretador ou ferramenta que `npm`/`pnpm`/`yarn`/`bun` iniciariam (direto ou depois de `run`/`run-script`), sem recusar scripts do projeto (`yarn run test`, `npm run build`). Coberto por `test_inline_code_refused_by_default`.

### SEC-006: resíduos de baixa severidade da revisão final
- Severity: LOW
- Status: resolved
- Evidence: `curl x | sh` e `perl -e` passavam no modo shell; `deno run npm:` não era recusado; `lessons.py confirm` não checava `evidence`, e `list` mostrava texto cru; `curl -u user:senha` não era mascarado.
- Recommendation: aplicado. Pipe para interpretador sem script (ou shell com `-s`) é recusado sem `--allow-inline`; `perl -e/-E` entra na lista de interpretadores; `deno run npm:/jsr:` é recusado; `confirm` checa todos os campos de texto e `list` mascara a saída; `redact_secrets` mascara a senha de `-u/--user user:senha`. Coberto por `test_inline_code_refused_by_default`, `test_lessons_edited_by_hand_stay_redacted` e `test_hook_marks_inferred_and_redacts`.

### SEC-007: argumento com metacaractere do cmd.exe virava comando no Windows
- Severity: HIGH
- Status: resolved
- Evidence: revisão independente final (FIND-016) reproduziu `npm -v&echo.>marker` criando o arquivo sem `Shell: yes`, e `npm -v "x|findstr" 9999` gravando o exit code do `findstr`. Causa: no Windows, `npm` resolve para `npm.cmd`, e todo `.cmd`/`.bat` roda pelo `cmd.exe`. Controle negativo: o mesmo `.cmd` chamado direto pelo `subprocess` cria o marcador.
- Recommendation: aplicado. `batch_refusal` recusa `& | < > ^ %` e quebra de linha nos argumentos quando o executável resolvido é `.cmd`/`.bat` no Windows; quem precisar desses caracteres usa `Shell: yes` com `--allow-shell`. Coberto por `test_inline_code_refused_by_default` (unitário e ponta a ponta com um `.cmd` falso).

### SEC-008: flag com valor desconhecida escondia código inline
- Severity: LOW
- Status: resolved
- Evidence: FIND-017 da revisão final: `node --unhandled-rejections strict -e`, `python --check-hash-based-pycs always -c`, `python -m coverage run -m pip install`, `python -m django shell -c` e `tox exec -- python -c` passavam.
- Recommendation: aplicado. Só um argumento que parece arquivo (com `.` ou separador de caminho) encerra a varredura de flags; `coverage run` e `tox exec` passam pela mesma política; `django shell/dbshell/runscript` é recusado.

## Limites aceitos

- A política não é sandbox: um arquivo de teste do projeto executa o que contiver. Ele fica no diff e passa pela revisão; é a fronteira escolhida em ADR-0002.
- `proof_allow` no `layout.json` e `--allow` ampliam a lista de executáveis. Mesmo liberados, `bash/sh/zsh -c`, `pwsh/powershell -Command/-EncodedCommand` e `cmd /c` continuam recusados como código inline; um script de shell versionado (`bash scripts/test.sh`) roda.
- A recusa de instalação é por nome de subcomando (melhor esforço). Exemplos que ainda passam: `uv sync`, `dotnet restore`, `go mod download`, `go run pkg@latest`, `yarn workspace web add`, e subcomando escondido atrás de flag sem valor seguida de flag com valor desconhecida (`npm --silent --prefix sub install`).
- A recusa de código inline também é melhor esforço: uma flag desconhecida cujo valor parece arquivo esconde o código seguinte (`node --env-file .env -e`, `node --title a.b -e`, `bun --cwd ./sub -e`, `php --define a.b=1 -r`, `python -m coverage run --rcfile .coveragerc -m pip`), assim como comandos de framework que abrem shell (`python manage.py shell -c`, `npm explore pkg -- node -e`). O TEST fica no diff e passa pela revisão.
- Com `Shell: yes` + `--allow-shell` (duplo opt-in), subshell `( ... )`, `| bash /dev/stdin`, `powershell <comando>` sem flag, abreviações como `powershell -enc`/`pwsh -comm` e `pythonw -c` não são detectados.
- A redação de `-u user:senha` não cobre valor colado (`-uuser:senha`), usuário vazio (`-u :token`) nem segredo sem dois-pontos. Um script de projeto (`npm run x`, `make target`) pode instalar por dentro; a defesa é a revisão do diff.
- Linhas antigas da timeline gravadas antes da redação de `Authorization` só são mascaradas na leitura (`timeline_view.py`); o JSONL em disco não é reescrito.
- Lições editadas à mão em `lessons.json` são mascaradas ao renderizar `LESSONS.md`, e `confirm` recusa lição com segredo aparente.
