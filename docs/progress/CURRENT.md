# Progresso atual: harness-evolution

Branch `feat/harness-evolution`, tudo sem commit. Nenhuma operação Git remota feita; aguardando aprovação do usuário para commit, push e PR.

## Implementado

- Núcleo determinístico: `artifacts.py`, `validate_spec.py`, `validate_tasks.py`, `check_proofs.py`, `validate_verification.py` (gate).
- Política de comandos de `check_proofs.py` (ADR-0002): sem shell, allowlist de executáveis, recusa de instalação/publicação por subcomando (melhor esforço), recusa de código inline por padrão (`--allow-inline` só com autorização), shell só com `Shell: yes` + `--allow-shell`, encerramento da árvore de processos no timeout.
- Fingerprint do workspace: escopo do subdiretório do projeto; a prova guarda o fingerprint de antes da execução; mudança durante a execução gera aviso e falha com `--strict`.
- Provas em `.cursor/agent-system/proofs/` são locais e ignoradas pelo `.gitignore`.
- Segurança: rule, skill, agente `security-reviewer`, redação de `Authorization`/Bearer/Basic nos hooks e no `timeline_view.py`.
- Lições (`lessons.py`, ADR-0003): só o usuário confirma; `confirm` recusa segredo aparente; `LESSONS.md` é mascarado ao renderizar.
- Evals determinísticos (`run_evals.py`, 8 fixtures com arquivos de teste reais).

## Adiado (Minimum Effective Engineering)

`metrics.py`, skill `/agent-evaluation`, cenários e rubricas manuais de evals. Arquivos guardados fora do repositório, no store do agente (`deferred/harness-evolution/`). Motivo: sem consumidor concreto. Ver seção "Deferred" em `docs/specs/harness-evolution.md`.

## Artefatos

- Spec: `docs/specs/harness-evolution.md`
- Tarefas: `docs/tasks/harness-evolution.md`
- ADRs: `docs/architecture/ADR/0001-*`, `0002-provas-fingerprint-e-politica-de-comandos.md`, `0003-*`
- Segurança: `docs/security/harness-evolution.md`
- Review: `docs/reviews/harness-evolution.md`

## Verificação

```text
python agent-system/scripts/test_system.py
python agent-system/scripts/run_evals.py
python agent-system/scripts/validate_spec.py --feature harness-evolution --require-approval --strict
python agent-system/scripts/validate_tasks.py --feature harness-evolution --strict
python agent-system/scripts/check_proofs.py --feature harness-evolution --strict
python agent-system/scripts/validate_verification.py --feature harness-evolution
```

Linux: copiar a árvore para `/tmp/aw-linux` no WSL (sem `.git`, `__pycache__`, `.cursor`) e rodar os dois primeiros comandos com `python3`.

## Resultados

- Windows: 29/29 testes, 8/8 evals.
- Linux (WSL2 Ubuntu, Python 3.14): 29/29 testes, 8/8 evals.
- macOS: não testado.

- Validadores strict (spec com `--require-approval`, tasks): exit 0. Provas: 14/14 PASS com `--strict`.
- Revisão de segurança final: SEC-001 a SEC-008 resolvidos (SEC-007 HIGH: metacaractere do `cmd.exe` em `.cmd`/`.bat` no Windows).
- Revisão independente final: PASS_WITH_WARNINGS. FIND-001 a 016 e 020 resolvidos; FIND-011, 017, 018 e 019 aceitos como limites de melhor esforço; nenhum aberto.
- Gate `validate_verification.py --feature harness-evolution`: exit 0.

## Pendências

- Limites de melhor esforço (FIND-011, 017, 018, 019) aceitos pelo usuário em 2026-11-03: `check_proofs.py` é guardrail, não sandbox nem fronteira de segurança contra código malicioso.
- PRs #3 e #4 mergeados em `main` (`c3e37e9`). Branch `fix/content-fingerprint`, sem commit: FIND-022 (fingerprint pelo conteúdo dos arquivos, sem HEAD, para a review commitada continuar válida). Aguardando revisão e aprovação do usuário para commit, push e PR.

## Frente: suporte ao Claude Code (0.4.0)

Branch `feat/claude-code-support`. O mesmo repositório funciona como plugin do Cursor e do Claude Code.

- `.claude-plugin/plugin.json` e `.claude-plugin/marketplace.json` (o repositório é o próprio marketplace). Versão 0.4.0 nos dois manifests.
- `hooks/claude-hooks.json` chama o mesmo `hook.py`, que traduz o payload do Claude Code para o formato do Cursor e devolve `hookSpecificOutput.additionalContext` no `SessionStart`. `hooks/hooks.json` (Cursor) é ignorado pelo Claude Code com aviso no `claude plugin validate`.
- Rules: `init_project.py --claude` grava as rules `00` a `08` condensadas (`agent-system/templates/CLAUDE.md`) num bloco gerenciado do `CLAUDE.md` do projeto e não mexe em `.cursor/hooks.json`.
- Subagents `implementer`, `tester` e `debugger`: `model: inherit` (valor aceito pelos dois editores).
- Estado do projeto continua em `.cursor/agent-system/` nos dois editores.

Verificação:

```text
python agent-system/scripts/test_system.py   # 32/32 (inclui test_claude_code.py)
python agent-system/scripts/run_evals.py     # 8/8
claude plugin validate .                     # passa; avisos esperados do hooks.json do Cursor e do ícone
```

Instalação testada com Claude Code 2.1.317 a partir do marketplace local: 34 skills, 7 agents e 7 hooks carregados; init executado a partir da cópia em cache.

Pendente: teste numa sessão real do Claude Code (substituição de `${CLAUDE_PLUGIN_ROOT}` nas skills, hooks disparando) e no macOS, onde `python` pode não existir no PATH.
