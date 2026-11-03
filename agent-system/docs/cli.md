# Contratos de CLI

Todos os scripts usam só a biblioteca padrão do Python 3.10+, rodam em Windows, macOS e Linux, e não fazem rede, commit, push nem instalação. No projeto, rode as cópias em `.cursor/agent-system/scripts/` a partir da raiz. No plugin, os mesmos arquivos ficam em `agent-system/scripts/`.

## Contrato comum dos validadores

| Opção | Efeito |
| --- | --- |
| `--root PATH` | raiz do projeto (padrão: diretório atual) |
| `--feature SLUG` | nome de arquivo comum a spec, tasks, reviews e security |
| `--spec`, `--tasks`, `--tests`, `--review`, `--security` | caminho explícito, relativo à raiz; ganha de `--feature` |
| `--json` | saída estruturada (`ok`, `failures`, `warnings`, `results[]`) |
| `--strict` | avisos também reprovam |
| `--no-record` | não grava evento na timeline |
| `--help` | ajuda do argparse |

Exit codes: `0` sucesso, `1` validação ou gate reprovado, `2` erro de configuração, argumento, arquivo ausente, JSON inválido ou caminho fora da raiz.

Saída em texto: uma linha por resultado (`[PASS]`, `[WARN]`, `[FAIL]`, `[INFO]`) e a linha final `<check> passed.` ou `<check> failed.`.

Em projeto inicializado, cada validador grava o próprio evento (`SPEC_VALIDATION_COMPLETED`, `TASK_VALIDATION_COMPLETED`, `PROOF_EXECUTION_STARTED`/`COMPLETED`, `VERIFICATION_COMPLETED`) com `feature` e o resultado, e atualiza `state.json → verification.<slug>`. Falha ao gravar a timeline não muda o exit code.

## validate_spec.py

```powershell
python .cursor/agent-system/scripts/validate_spec.py --feature reset-password --require-approval
```

FAIL: front matter sem `status` ou com valor inválido, `complexity` ou `security_risk` inválidos, nenhum REQ ou AC, ID duplicado, AC sem REQ, AC com REQ inexistente, item sem texto, `--require-approval` sem `status: approved`.
WARN: REQ sem AC, sem seção de premissas ou restrições, spec aprovada com pergunta `- [ ]` aberta, REQ ou AC citado e não definido, ADR citado sem arquivo, `security_risk` ausente em M+, NONE com gatilhos.
INFO: quantos requisitos usam EARS.

## validate_tasks.py

```powershell
python .cursor/agent-system/scripts/validate_tasks.py --feature reset-password
```

FAIL: ID duplicado, tarefa sem título, sem REQ nem AC, com REQ/AC fora da spec, sem verificação, sem `Done when`, status ausente ou desconhecido, dependência inexistente ou circular, `blocked` sem causa, `done` sem prova PASS ou `Evidence`; TEST sem `Command` (se obrigatório), sem AC, com AC ou tarefa inexistente.
WARN: tarefa sem AC, sem `Gate`, `done` antes da dependência, AC sem tarefa ou sem TEST, spec não encontrada.

## check_proofs.py

```powershell
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password --task TASK-002
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password --only TEST-003 --timeout 300
python .cursor/agent-system/scripts/check_proofs.py --feature reset-password --dry-run
python .cursor/agent-system/scripts/check_proofs.py --fingerprint
```

Opções extras: `--only TEST-NNN` e `--task TASK-NNN` (repetíveis), `--timeout` (padrão 600 s; `Timeout` do TEST tem prioridade), `--allow EXE` (repetível; também `proof_allow` no layout), `--allow-shell`, `--allow-inline`, `--dry-run`, `--fingerprint`. `--allow-shell` e `--allow-inline` só com autorização do usuário.

Status por TEST: `PASS` (exit 0), `FAIL` (exit ≠ 0), `TIMEOUT` (árvore de processos encerrada), `ERROR` (executável ausente ou falha ao iniciar: ambiente), `REFUSED` (política). Exit: `1` se houver FAIL ou TIMEOUT, senão `2` se houver ERROR ou REFUSED, senão `0`.

Política (ADR-0002): executa sem shell, a partir da raiz ou de `Cwd`. Só executáveis da lista (python, python3, py, pytest, uv, poetry, tox, nox, hatch, node, npm, pnpm, yarn, bun, deno, vitest, jest, tsc, dotnet, go, cargo, mvn, mvnw, gradle, gradlew, java, php, composer, phpunit, pest, ruby, bundle, rake, rspec, make, ctest). `npx`, `dlx`, `npm exec`, `npm x` e `bun x` ficam fora porque baixam pacote. A recusa de instalação é de melhor esforço, por nome de subcomando: recusa quando o subcomando instala, publica ou remove (`npm install`, `python -m pip install`, `uv pip install`, `make install`, `cargo publish`, `dotnet add`...), `yarn` e `bundle` sem subcomando, e operadores de shell sem `Shell: yes`. No Windows, um `.cmd`/`.bat` (como `npm.cmd`) roda pelo `cmd.exe`, então argumentos com `& | < > ^ %` são recusados nesse caso. Recusa código inline (melhor esforço, por análise de argumentos; uma flag desconhecida cujo valor parece arquivo, como `node --env-file .env -e`, ainda esconde o código): `python -c` (inclusive `-Bc`), `python -m` fora da lista de módulos de teste (pytest, unittest, coverage, tox, mypy, ruff...) e dos módulos do próprio projeto, `node -e/--eval/-p`, `node --import data:/http:`, `bun -e`, `deno eval`, `deno run <URL>`, `ruby -e` (inclusive `-we`), `rake -e`, `php -r`, `make --eval`, `bash/sh -c` (inclusive `-ec`), `pwsh -Command` e `cmd /c`, `perl -e`, `deno run npm:/jsr:`, também quando iniciados por `npm`/`pnpm`/`yarn`/`bun` (`yarn run node -e`, `pnpm node -e`) ou chamados por `uv run`, `poetry run`, `hatch run`, `pnpm exec`, `yarn exec/node` ou `bundle exec` (o comando interno passa pela mesma política). Um TEST aprovado chama o runner do projeto (`pytest`, `npm test`, `dotnet test`, `python -m pytest`...) ou um arquivo de teste versionado (`python tests/check_x.py`). `--allow-inline` libera código inline numa execução, com autorização do usuário. Com `Shell: yes` e `--allow-shell`, as recusas de instalação e de código inline valem para cada trecho do comando (também depois de `env`, `xargs` e similares), e substituição de shell (`$(...)`, crase, `<(...)`), heredoc e pipe para interpretador sem script (`curl x | sh`) são recusados sem `--allow-inline`. A política separa teste de comando arbitrário, mas não é sandbox: um arquivo de teste executa o que contiver.

A prova guarda o fingerprint de antes da execução. Se o workspace mudar enquanto os testes rodam (edição paralela ou arquivo gerado fora do `.gitignore`), o script avisa e o gate passa a tratar as provas como obsoletas; com `--strict`, sai com 1.

Saída: `.cursor/agent-system/proofs/<slug>.json` (fonte de verdade) e `<slug>.md`. Cada prova guarda TEST, REQ, AC, tarefa, comando (redigido), exit code, status, motivo, horários, duração, as últimas 20 000 letras de stdout e stderr com segredos mascarados, e o fingerprint. Rodar só alguns TESTs mantém as provas dos outros. As provas são evidência local, presa ao fingerprint: não versione a pasta (o plugin a ignora no `.gitignore`; faça o mesmo no projeto). Num projeto que é subpasta de um repositório git, o fingerprint considera só os arquivos da subpasta.

Fingerprint: HEAD mais o hash do conteúdo de cada arquivo modificado ou não rastreado (git status), sem `.cursor/`, caches e Markdown das pastas de doc do harness. Sem git, hash dos arquivos do projeto (até 5 000 arquivos). Não exige commit.

## validate_verification.py

```powershell
python .cursor/agent-system/scripts/validate_verification.py --feature reset-password
```

Inclui as falhas estruturais de `validate_spec` e `validate_tasks`. FAIL: AC obrigatório sem TEST, TEST obrigatório sem prova, prova diferente de PASS, prova de outro fingerprint, comando do TEST alterado depois da prova, tarefa que não está `done` nem `cancelled`, review ausente em M+ ou com status FAIL, revisão de segurança ausente com risco HIGH/CRITICAL ou com status FAIL, achado bloqueante aberto, risco aceito sem justificativa.
WARN: review com fingerprint de outro estado, achado `major`/`MEDIUM` aberto, AC coberto só por TEST opcional.

## lessons.py

```powershell
python .cursor/agent-system/scripts/lessons.py add --category testing --title "..." --description "..." [--context "..."] [--evidence TEST-004]
python .cursor/agent-system/scripts/lessons.py list [--status confirmed] [--category testing] [--json] [--verbose]
python .cursor/agent-system/scripts/lessons.py confirm --id LESSON-001
python .cursor/agent-system/scripts/lessons.py reject --id LESSON-002 --reason "..."
python .cursor/agent-system/scripts/lessons.py render
```

Categorias: architecture, requirements, implementation, testing, security, performance, debugging, workflow, tooling. Exit `1` para duplicata (título normalizado) ou texto com segredo; `2` para projeto não inicializado, argumento inválido, ID inexistente ou JSON inválido. `lessons.json` é a fonte de verdade; `LESSONS.md` é regenerado a cada mudança.

## run_evals.py (só no plugin)

```powershell
python agent-system/scripts/run_evals.py [--json]
```

Roda as fixtures de `agent-system/evals/fixtures/` e compara exit code e trechos de saída com `expect.json`. Exit `0` se todas batem, `1` se alguma diverge, `2` se uma fixture é inválida.

## Outros

`record_event.py --event <EVENTO> --summary "..." [--feature SLUG] [--result ...]`, `status_cmd.py`, `timeline_view.py --write-md` e `init_project.py --root . [--for-cloud]` mantêm o contrato anterior.
