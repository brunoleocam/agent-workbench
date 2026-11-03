# ADR-0002: Provas, fingerprint e política de comandos

Status: aceito
Data: 2026-11-03

## Contexto

`afterShellExecution` não traz exit code, então o resultado de teste do hook é inferido. O usuário revisa o diff antes de autorizar git, logo a prova não pode exigir commit. `check_proofs.py` executa comandos escritos em artefato, o que é superfície de risco.

## Decisão

- `check_proofs.py` é a única fonte de resultado determinístico. Grava `.cursor/agent-system/proofs/<slug>.json` (fonte de verdade) e `<slug>.md` (vista).
- Cada prova guarda o fingerprint do workspace de antes da execução: o conteúdo de cada arquivo do projeto, como blob id do git (índice para arquivo sem mudança, `git hash-object` para arquivo modificado ou não rastreado, com a mesma normalização de fim de linha do `git add`), limitado à pasta do projeto quando ela é subpasta do repositório. O HEAD não entra na conta: commitar o mesmo conteúdo mantém o fingerprint, então uma review registrada antes do commit continua válida depois dele. Exclui `.cursor/`, caches e os diretórios de doc do harness, para que escrever review ou checkpoint não invalide a prova. Sem git: hash dos arquivos do projeto, com limite. Se o workspace muda durante a execução, as provas ficam obsoletas para o gate (código testado não é garantidamente o atual); `--strict` sai com 1.
- Execução sem shell, com `shlex` ou lista JSON. Executável resolvido com `shutil.which`. Lista de executáveis permitidos e recusa de subcomandos que instalam, publicam ou removem pacotes, inclusive em cada trecho de um comando shell. Extensão só com `--allow <exe>`. Shell só com `Shell: yes` no TEST e `--allow-shell` na CLI. Código inline (`python -c`, `node -e`, `ruby -e`, `php -r`, `deno eval`, `deno run <URL>`, `bash -c`, `python -m` fora dos módulos de teste e do projeto, substituição de shell e heredoc) é recusado por padrão, também quando um wrapper (`uv run`, `poetry run`, `bundle exec`, `yarn node`...) o inicia: o comando interno passa pela mesma política. Um TEST aprovado chama o runner do projeto ou um arquivo de teste versionado, que fica visível no diff e na revisão; código inline no artefato de tarefas é comando arbitrário. `--allow-inline` libera numa execução, só com autorização do usuário. Provas em `.cursor/agent-system/proofs/` são evidência local e não são versionadas.
- Status: PASS, FAIL (exit ≠ 0), TIMEOUT, ERROR (ambiente, executável ausente), REFUSED (política). TIMEOUT, ERROR e REFUSED não são tratados como falha da aplicação no relatório.

## Alternativas

- Exigir commit e usar o SHA: contraria a revisão humana antes do git.
- Sandbox real: fora de escopo e não portável. A lista é proteção contra acidente, não isolamento; os comandos vêm de artefato versionado e aprovado.

## Consequências

- Teste que escreve arquivo rastreado muda o fingerprint; o script avisa quando o fingerprint antes e depois difere.
- Comando de runner fora da lista exige `--allow` explícito.
