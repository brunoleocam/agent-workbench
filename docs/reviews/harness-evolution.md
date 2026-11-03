---
status: PASS_WITH_WARNINGS
reviewer: reviewer
fingerprint: b9a8f9305dd1f636b8618b6d6436fb2a6be66aa16ddcddf52bc4d39885efce90
---
# Review: evolução do harness

Escopo: mudanças não commitadas da branch `feat/harness-evolution` (29 arquivos modificados e 16 entradas não rastreadas), conferidas contra `docs/specs/harness-evolution.md`, ADR-0001..0003, `docs/tasks/harness-evolution.md`, `docs/security/harness-evolution.md` e `agent-system/docs/{artifacts,cli,contracts}.md`. Segunda rodada da revisão final, depois das correções de FIND-011 e FIND-016 a FIND-020.

Como verifiquei (Windows, Python 3.13):
- `python agent-system/scripts/test_system.py`: `27 passed, 0 failed`. `run_evals.py`: `8/8 deterministic evals passed`.
- `validate_spec.py --feature harness-evolution --require-approval --strict` e `validate_tasks.py --feature harness-evolution --strict`: exit 0. `validate_verification.py --feature harness-evolution`: exit 0, `14 required checks proven on the current workspace`.
- `check_proofs.py --fingerprint --dry-run`: digest `975820cf…`, 83 arquivos alterados, igual ao fingerprint das 14 provas (todas PASS).
- FIND-016 ponta a ponta: projeto temporário em `%TEMP%` com quatro TESTs `npm`, rodado com `check_proofs.py --root <tmp> --tasks docs/tasks/probe.md`. A pasta foi apagada depois.
- Script descartável em `%TEMP%` chamando `policy_refusal` e `batch_refusal` com 24 comandos que deveriam ser recusados e 27 que deveriam passar. Para as formas que escapam, executei `node` para confirmar que o código roda. Scripts e pastas temporárias foram apagados.
- Não rodei `check_proofs.py` sem `--dry-run` sobre o repositório nem `record_event.py`, para não alterar provas nem arquivos fora desta review.
- Terceira rodada (FIND-017 documentado como limite, sem mudança de código): `check_proofs.py` e `test_proofs.py` não mudaram desde a rodada anterior (modificados às 10:47, antes dela). Só mudaram REQ-005 na spec, `agent-system/docs/cli.md`, `agent-system/README.md` e `docs/security/harness-evolution.md`. Os dois READMEs entram no fingerprint, o que explica o digest novo `49451b3e…`. As 14 provas regeneradas estão PASS com esse fingerprint, e o TEST-015 (suíte completa) faz parte delas.
- Atualização sobre o commit `1c1ee94` (PR #3), feita pelo implementador e ainda sem nova revisão independente: correção de FIND-021 em `validate_verification.py`. O workspace atual é o HEAD `1c1ee94` mais 9 arquivos alterados, digest `565b74e4…`. Antes de atualizar esta review, o gate corrigido reprovou com `Review was recorded for another workspace state (fingerprint 49451b3ea44a, current 565b74e4f01b)`; o código anterior não teria apontado isso. Resultados: suíte 28/28 no Windows e no Linux (WSL2), evals 8/8, validadores strict com exit 0, 14 provas PASS regeneradas com esse digest.
- Depois, só documentação e o teste de READMEs: `README.md` passou a ser a versão em inglês, com link para `README.pt-BR.md` (novo), e `test_readmes_cite_only_existing_commands_and_scripts` passou a checar também o README em português. Digest novo `45c3adc9…`; 14 provas PASS regeneradas, incluindo o TEST-015 (suíte completa). Sem mudança de código do harness.
- Atualização sobre o `main` em `c3e37e9` (PR #4 mergeado), feita pelo implementador e ainda sem nova revisão independente: correção de FIND-022 (fingerprint pelo conteúdo, sem HEAD). Digest `b9a8f930…` (modo git, 123 arquivos, 4 alterados); cálculo em 0,76 s. Suíte 29/29 no Windows e no Linux (WSL2), evals 8/8, validadores strict com exit 0, 14 provas PASS.

## Verification Audit

TEST-001 (parser, AC-001): confere `Block.line` (`test_validators.py:23`, linhas 6 e 13), além de bloco dentro de fence, alias pt-BR e linha sem alias. Um parser que gravasse a linha errada falha. Forte.

TEST-002 (validate_spec e layout, AC-002/AC-008): exit code e `[FAIL]` para ID duplicado e REQ inexistente, `[WARN]` promovido por `--strict`, `security_risk` inválido, `overrides`, `--feature ../reset` e caminho fora da raiz com 2, JSON inválido com 2. Cobre o AC. REQ-002 também cita "AC sem REQ" e "ADR citado sem arquivo", que o AC não exige e nenhum teste cobre (resíduo aceitável; não está no AC).

TEST-003 (validate_tasks, AC-003): dependência inexistente, ciclo, bloqueio sem causa, `done` sem prova PASS, sem verificação e sem `Done when`, sempre nomeando a tarefa. `test_validate_tasks_duplicate_and_done_without_evidence` (`test_validators.py:114-125`) cobre tarefa duplicada e `done` sem `Evidence`, e o caso corrigido confirma que os códigos somem. As asserções checam o código (`duplicate-id`, `task-done-no-evidence`) no JSON, não a tarefa nomeada; suficiente.

TEST-004 (check_proofs, AC-004/AC-005): PASS, FAIL com exit real, TIMEOUT, ERROR, REFUSED sem execução (`started_at is None`), morte do neto no timeout e remoção da prova de TEST removido (`test_proofs.py:50`). `test_inline_code_refused_by_default` lista as formas inline recusadas (inclusive as de FIND-011, FIND-013 e parte de FIND-017) e os comandos normais permitidos (`test_proofs.py:130-141`). `batch_refusal` tem asserções unitárias com `windows=True` (`:143-147`, rodam em qualquer sistema) e um caso ponta a ponta no Windows com `tools/runner.cmd` falso (`:178-188`): o TEST com `-v&echo.>marker.txt` vira REFUSED, o marcador não aparece e o TEST sem metacaractere passa. O caso ponta a ponta é pulado fora do Windows, o que é correto, porque o problema só existe lá. Mutação que ainda passa com tudo verde: valor de flag desconhecida que contém ponto ou caminho esconde o `-e`/`-c` seguinte (FIND-017, aceito e documentado como limite).

TEST-005 (fingerprint, AC-006): código muda e doc do harness não muda, em modo arquivos e git, projeto em subpasta de repositório e prova com o fingerprint de antes da execução. Ponto fraco mantido: `test_fingerprint_in_repository_subdirectory` (`test_proofs.py:230`) retorna sem asserção quando não há `git` no PATH.

TEST-006 (gate, AC-007): prova ausente, prova obsoleta, review ausente, review com `status: FAIL` (`test_proofs.py:278`), comando alterado depois da prova (`:283`), blocker aberto, risco aceito sem justificativa, HIGH sem revisão de segurança, SEC aberto, tarefa não concluída e `VERIFICATION_COMPLETED`/`state.verification`. `test_small_change_needs_no_review` cobre S. Forte.

TEST-007 (wiring, AC-009/010/012/019/020): estrutural, checa presença de arquivos e strings. Aceitável para critério estrutural.

TEST-008 (init, AC-011/AC-018): frameworks, superfícies, `overrides` e `proof_allow` preservados, estado migrado e `--for-cloud`. Forte.

TEST-009 (lições, AC-013): duplicata e segredo saem 1, `confirm`, `render` e `sessionStart` só com confirmadas. O comando agora inclui `test_lessons_edited_by_hand_stay_redacted` (SEC-005), e a prova registra `2 passed, 0 failed`.

TEST-011 (evals, AC-015): oito fixtures, todas com `Command` apontando para arquivos em `checks/`, sem código inline.

TEST-012 (hook, AC-017): `inferred: true` e redação de token, `Authorization: Bearer/Basic` e `-u user:senha`. Falharia se o segredo vazasse.

TEST-013 (eventos, AC-016): eventos novos e `verification` sem perder `version`, `active_agent` e `phase`.

TEST-014 e TEST-015 (AC-020): TEST-014 confere que cada comando e script citado nos READMEs existe; `manifest["version"] == "0.2.0"` está em `test_improvement.py:217` e roda no TEST-015. Fraco por desenho para afirmações em prosa.

Provas (item 9): 14 provas em `.cursor/agent-system/proofs/harness-evolution.json`, todas PASS, fingerprint `49451b3ea44a…` igual ao workspace atual, sem prova de TEST-010. `validate_verification.py` não reporta prova obsoleta nem comando alterado.

Filtro dos TESTs: `test_system.py:254-255` falha quando nenhum teste casa, e todos os nomes usados pelos TESTs existem.

Minimum Effective Engineering: `metrics.py`, `/agent-evaluation`, cenários e rubricas foram adiados (spec, seção Deferred) e não deixaram código, teste, skill nem fixture órfãos. Não achei componente sem consumidor. O ponto de complexidade é a política de comandos: é uma lista de negação com mais de 300 linhas de heurística (`check_proofs.py`, de `ALLOWED_EXECUTABLES` até `shell_refusal`), e cada rodada de revisão acha formas novas. A decisão desta entrega foi parar de enumerar: REQ-005 e a seção "Limites aceitos" declaram melhor esforço tanto para instalação quanto para código inline, e os resíduos ficam documentados.

### FIND-001: fingerprint ignora mudanças quando a raiz do projeto é subdiretório do repositório git
- Severity: blocker
- Status: resolved
- File: agent-system/scripts/artifacts.py
- Evidence: `test_fingerprint_in_repository_subdirectory` passa: edição em `app/src` muda o digest, doc do harness e pasta irmã não mudam.

### FIND-002: descoberta de layout aponta specs e tarefas para pastas de código
- Severity: major
- Status: resolved
- File: agent-system/scripts/init_project.py
- Evidence: `test_layout_ignores_code_folders_named_spec_or_tasks` passa no TEST-002. Resíduo documentado no código: `spec/README.md` sem `docs/specs` vira `specs_dir`; `overrides` resolve.

### FIND-003: token em `Authorization: Bearer <token>` vaza na timeline
- Severity: major
- Status: resolved
- File: agent-system/scripts/lib.py:24
- Evidence: `redact("curl -H 'Authorization: Bearer abcdefgh1234' x")` devolve `curl -H '[redacted]' x`; coberto no TEST-012.

### FIND-004: prova recebe o fingerprint posterior mesmo quando o workspace mudou durante a execução
- Severity: major
- Status: resolved
- File: agent-system/scripts/check_proofs.py:604
- Evidence: `proof["fingerprint"] = before["digest"]`; `test_proofs_keep_fingerprint_from_before_the_run` passa.

### FIND-005: com `Shell: yes` a política de instalação não é aplicada
- Severity: minor
- Status: resolved
- File: agent-system/scripts/check_proofs.py:339
- Evidence: `shell_refusal` aplica a política a cada trecho; `npm install left-pad && npm test` com `--allow-shell` vira REFUSED (`test_proofs.py:101-103`).

### FIND-006: lacunas e falsos positivos na política de comandos
- Severity: minor
- Status: resolved
- File: agent-system/scripts/check_proofs.py:192
- Evidence: `test_policy_subcommands` passa com `npm exec`, `bun x`, `python -mpip install`, `make install`, `setup.py install` recusados e `go test ./... -run get`, `cargo test -- i` permitidos.

### FIND-007: métricas contam testes inferidos de timeline antiga como "registrados por agentes"
- Severity: minor
- Status: resolved
- File: docs/specs/harness-evolution.md:170
- Evidence: `metrics.py` foi adiado (seção Deferred) e não existe no repositório.

### FIND-008: `--strict` é aceito e ignorado por `check_proofs.py`
- Severity: minor
- Status: resolved
- File: agent-system/scripts/check_proofs.py
- Evidence: `test_proofs.py:202`: com o workspace alterado durante a execução, `--strict` sai 1 com `[FAIL] Workspace changed`.

### FIND-009: testes não cobrem partes dos critérios que dizem cobrir
- Severity: minor
- Status: resolved
- File: agent-system/tests/test_validators.py:23
- Evidence: `Block.line` verificado (`test_validators.py:23`); tarefa duplicada e `done` sem `Evidence` (`test_validators.py:114-125`, códigos `duplicate-id` e `task-done-no-evidence`); review `status: FAIL` (`test_proofs.py:278`, `Review status is FAIL.`) e comando alterado depois da prova (`test_proofs.py:283`, `command changed after its proof`). Todos passam na suíte.

### FIND-010: lista de executáveis em `cli.md` não bate com o código
- Severity: info
- Status: resolved
- File: agent-system/docs/cli.md:56
- Evidence: os 36 executáveis de `cli.md:56` são os de `ALLOWED_EXECUTABLES` (`check_proofs.py:43-48`).

### FIND-011: recusa de instalação deixa passar formas menos comuns
- Severity: minor
- Status: accepted
- File: agent-system/scripts/check_proofs.py:174
- Evidence: `npm in x`, `npm un x` e `npm r x` agora são recusados (`MUTATING`, linha 51; asserções em `test_proofs.py:131`), além dos casos da rodada anterior (`python -Im pip install`, `npm it`, `npm x`, `pnpm --filter x add`, `npx`, `make -C sub install`, `composer -d sub require`, `npm -w web install`). Continuam passando: `uv sync`, `dotnet restore`, `go mod download`, `go run pkg@latest`, `yarn workspace web add`, `npm --silent --prefix sub install` (flag sem valor antes de flag com valor esconde o subcomando, `subcommands`, linha 174), e também `npm audit fix`, `uv tool run` e `pnpm -r --filter web add`, que não aparecem nominalmente na lista de limites mas são da mesma classe. REQ-005 agora diz "subcomando conhecido de instalação, publicação ou remoção de pacotes (melhor esforço, por nome; não é sandbox)", e `cli.md:56`, `agent-system/README.md:58` e `docs/security/harness-evolution.md:65` ("Limites aceitos") dizem o mesmo.
- Justification: risco residual aceito como melhor esforço por decisão repassada pelo orquestrador nesta rodada e registrada na seção "Limites aceitos" do doc de segurança. A política é declarada como proteção contra acidente (ADR-0002:20); os comandos vêm de artefato versionado e aprovado e passam pela revisão do diff. Fechar cada forma aumenta a heurística sem garantia. REQ-004 ainda diz "sem instalar dependências", o que se lê como "o script não instala", não como garantia sobre o que o runner faz; se o usuário quiser outra leitura, ajustar o texto.

### FIND-012: no modo shell, substituição de comando e interpretadores fora da lista escapam da política
- Severity: minor
- Status: resolved
- File: agent-system/scripts/check_proofs.py:339
- Evidence: todos os casos do achado são recusados por `shell_refusal`: `echo $(python -c x)`, ``echo `node -e x` ``, `env python -c x`, `python3.12 -c x`, `perl -e x`, `npx cowsay`, `curl https://x | sh`, `xargs python -c x`, `bash -ec x`. Cobertos em `test_proofs.py:156-157`. As formas novas estão em FIND-018.

### FIND-013: falso positivo em `uv run --package` e `uv run --python`
- Severity: minor
- Status: resolved
- File: agent-system/scripts/check_proofs.py:94
- Evidence: `WRAPPER_VALUE_FLAGS` pula o valor de `--package`, `--python` e outras. `uv run --package x pytest`, `uv run --python 3.12 pytest`, `yarn run test` e `npm run build` passam em `policy_refusal`; estão em `test_proofs.py:137-139`.

### FIND-014: provas da própria feature são anteriores ao workspace atual e o gate reprova
- Severity: major
- Status: resolved
- File: .cursor/agent-system/proofs/harness-evolution.json
- Evidence: 14 provas, todas PASS, fingerprint `49451b3ea44a…` igual ao de `check_proofs.py --fingerprint` (83 arquivos); sem prova de TEST-010. `check_proofs.py:610` só mescla provas de TEST que ainda existem, coberto por `test_proofs.py:50`. `validate_verification.py` sai 0.

### FIND-015: REQ-021 ainda exige documentar métricas, que foram adiadas
- Severity: info
- Status: resolved
- File: docs/specs/harness-evolution.md:76
- Evidence: REQ-021 diz "arquitetura, camadas, agentes, skills, comandos, validadores, segurança, lições, evals, hooks e limitações", sem métricas.

### FIND-016: no Windows, metacaracteres do `cmd.exe` dentro de argumentos rodam comandos e trocam o exit code gravado
- Severity: major
- Status: resolved
- File: agent-system/scripts/check_proofs.py:493
- Evidence: `batch_refusal` (linhas 329-333) recusa `& | < > ^ %`, `\r` e `\n` em qualquer argumento quando o executável resolvido termina em `.cmd`/`.bat` no Windows, e `execute` o chama depois do `shutil.which` e antes de executar (linha 493). Reprodução ponta a ponta com `check_proofs.py --root <tmp>` num projeto temporário, nesta máquina (npm resolve para `npm.CMD`):
  - `npm -v&echo.>aw_marker.txt`: `[REFUSED] ... argument has a cmd.exe metacharacter`, `exit=None`; o marcador não foi criado.
  - `npm -v "x|findstr" 9999` e `npm -v %PATH%`: REFUSED.
  - `npm -v`: `[PASS] exit=0`.
  - Também conferi, chamando a função: `^` e quebra de linha são recusados num `.CMD`/`.bat`, `node.exe` com `&` não é afetado, e fora do Windows não há recusa. `!` só expande com delayed expansion, que vem desligada no `cmd /c`.
  - Testes: `test_proofs.py:143-147` (unitário, inclui `-t "login|logout"`) e `:178-188` (ponta a ponta com `tools/runner.cmd`). Não existe mutação simples que passe: remover a chamada em `execute` derruba o caso ponta a ponta no Windows.

### FIND-017: valores de flag com ponto ou caminho ainda escondem código inline
- Severity: minor
- Status: accepted
- File: agent-system/scripts/check_proofs.py:140
- Evidence: os casos do relatório anterior passaram a ser recusados: `node --unhandled-rejections strict -e`, `python --check-hash-based-pycs always -c`, `node --title t -e`, `ruby -E UTF-8 -e`, `bun --cwd sub -e`, `python -m coverage run -m pip install x`, `python -m django shell -c x`, `tox exec -e py -- python -c x`. Os comandos normais continuam permitidos (27 de 27 na sonda, inclusive `python manage.py test`, `python -m coverage run -m pytest`, `tox exec -e py -- pytest`, `node --env-file .env scripts/test.js`). Ainda passam:
  - `node --env-file .env -e x`, que estava no relatório anterior. `looks_like_file` (linhas 140-142) trata qualquer token com `.` ou separador como script, então o valor `.env` encerra a varredura. Executei `node --env-file .env -e "console.log(...)"` e o código rodou.
  - Pelo mesmo motivo: `node --title a.b -e x` (executado, rodou), `node --redirect-warnings out.log -e x`, `bun --cwd ./sub -e x`, `php --define a.b=1 -r x` e `python -m coverage run --rcfile .coveragerc -m pip install x`. Este último roda `pip install` dentro do `coverage`.
  - `python manage.py shell -c x` (Django pelo script do projeto) e `npm explore pkg -- node -e x`.
  - Afeta REQ-005 e AC-005. Minor porque são formas improváveis por acidente e a política é declarada como proteção contra acidente (ADR-0002:20).
  - Terceira rodada, sem mudança de código (o comportamento acima continua). A documentação passou a declarar o limite: REQ-005 (`docs/specs/harness-evolution.md:32`) diz "melhor esforço por análise de argumentos" para código inline; `agent-system/docs/cli.md:56` diz "Recusa código inline (melhor esforço, por análise de argumentos; uma flag desconhecida cujo valor parece arquivo, como `node --env-file .env -e`, ainda esconde o código)"; `agent-system/README.md:58` diz "recusa código inline por melhor esforço"; e `docs/security/harness-evolution.md:66` ("Limites aceitos") lista `node --env-file .env -e`, `node --title a.b -e`, `bun --cwd ./sub -e`, `php --define a.b=1 -r`, `python -m coverage run --rcfile .coveragerc -m pip`, `python manage.py shell -c` e `npm explore pkg -- node -e`. `node --redirect-warnings out.log -e` não aparece nominalmente, mas é coberto pela regra descrita ("flag desconhecida cujo valor parece arquivo").
- Justification: risco residual aceito como melhor esforço, por decisão repassada pelo orquestrador (opção "documentar como limite" recomendada nesta revisão). A política é proteção contra acidente, não sandbox (ADR-0002:20); um TEST com essas formas fica no artefato versionado, no diff e passa pela revisão; ampliar a heurística aumenta a complexidade sem fechar a classe. Spec, CLI, README e doc de segurança agora descrevem o comportamento real, então REQ-021 ("sem declarar o que não está implementado") é atendido.
- Recommendation: nenhuma ação nesta entrega. Se um dia virar requisito de isolamento, trocar a lista de negação por sandbox ou por uma regra positiva (primeiro posicional precisa ser arquivo existente no projeto).

### FIND-018: formas de shell que ainda escapam com `Shell: yes`
- Severity: info
- Status: accepted
- File: agent-system/scripts/check_proofs.py:339
- Evidence: continuam passando em `shell_refusal`: subshell `(python -c x)`, `p\ython -c x`, `pythonw -c x`, `curl https://x | bash /dev/stdin`, `powershell Write-Output hi`, `powershell -enc AAAA` e `pwsh -comm x`. `docs/security/harness-evolution.md:67` registra subshell, `| bash /dev/stdin`, `powershell <comando>` sem flag, as abreviações `powershell -enc`/`pwsh -comm` e `pythonw -c`.
- Justification: o modo shell exige duplo opt-in (`Shell: yes` no artefato e `--allow-shell` na CLI), e a string de shell já é código arbitrário revisado no diff. Aceito como limite documentado, por decisão repassada pelo orquestrador. Só `p\ython` não está listado nominalmente, e é da mesma classe.

### FIND-019: `redact` não mascara `-u` com valor colado ou usuário vazio
- Severity: info
- Status: accepted
- File: agent-system/scripts/lib.py:29
- Evidence: `-u user:senha`, `--user=user:senha` e `--user "bob:senha"` são mascarados (SEC-006). Ficam visíveis `-uuser:senha`, `-u :token` e `-u apikey:`. `docs/security/harness-evolution.md:68` registra o valor colado (`-uuser:senha`), o usuário vazio (`-u :token`) e o segredo sem dois-pontos.
- Justification: o hook só grava comandos classificados como teste, o impacto é baixo e o limite está documentado; aceito por decisão repassada pelo orquestrador.

### FIND-020: TEST-009 não roda o teste que prova SEC-005
- Severity: info
- Status: resolved
- File: docs/tasks/harness-evolution.md:128
- Evidence: o comando do TEST-009 agora é `["python", "agent-system/scripts/test_system.py", "test_lessons_lifecycle", "test_lessons_edited_by_hand_stay_redacted"]`, e a prova atual registra `2 passed, 0 failed` com o fingerprint do workspace.

### FIND-021: gate aceitava relatório obrigatório sem fingerprint ou de outro estado
- Severity: major
- Status: resolved
- File: agent-system/scripts/validate_verification.py:57
- Evidence: `check_report_doc()` comparava por prefixo (`current.startswith(recorded)`), só avisava quando o fingerprint diferia e ignorava fingerprint ausente. Agora, para review e revisão de segurança obrigatórias, fingerprint ausente ou diferente reprova, com comparação exata; relatório não obrigatório só avisa. `test_report_fingerprint_must_match_exactly` cobre ausente, diferente (incluindo prefixo de 12 caracteres e digest com sufixo extra), igual, revisão de segurança obrigatória e review opcional. Controle negativo: com o `validate_verification.py` do commit `1c1ee94`, o teste falha, porque a review sem fingerprint passa no gate. O eval `stale-proof` agora exige que a review seja registrada de novo depois da mudança de código.
- Requirement: REQ-007 / AC-007 (TEST-006).

### FIND-022: review commitada nunca batia com o fingerprint do próprio commit
- Severity: major
- Status: resolved
- File: agent-system/scripts/artifacts.py (`workspace_fingerprint`)
- Evidence: o fingerprint incluía o HEAD; commitar a review mudava o HEAD, e o gate exato (FIND-021) reprovava no estado commitado (`fingerprint 45c3adc984ed, current 04449f90ccb3` no PR #4). Agora o digest é o blob id do git de cada arquivo do projeto (índice para arquivo sem mudança, `git hash-object` para modificado ou não rastreado, com a normalização de fim de linha do `git add`), sem o HEAD. `test_fingerprint_survives_commit` cobre: repositório sem commit em modo git, digest igual antes e depois do commit com `.gitattributes` `eol=crlf`, review carimbada antes do commit aceita pelo gate depois dele, mudança de conteúdo invalida e restaurar o conteúdo volta ao mesmo digest, arquivo apagado invalida. Controle negativo: num repositório com um commit, mudar um arquivo e commitar mantém o digest com o código novo (`True`) e muda com o anterior (`False`).
- Requirement: REQ-006 / AC-006 (TEST-005).
