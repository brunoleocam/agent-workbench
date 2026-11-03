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

- Windows: 27/27 testes, 8/8 evals.
- Linux (WSL2 Ubuntu, Python 3.14): 27/27 testes, 8/8 evals.
- macOS: não testado.

- Validadores strict (spec com `--require-approval`, tasks): exit 0. Provas: 14/14 PASS com `--strict`.
- Revisão de segurança final: SEC-001 a SEC-008 resolvidos (SEC-007 HIGH: metacaractere do `cmd.exe` em `.cmd`/`.bat` no Windows).
- Revisão independente final: PASS_WITH_WARNINGS. FIND-001 a 016 e 020 resolvidos; FIND-011, 017, 018 e 019 aceitos como limites de melhor esforço; nenhum aberto.
- Gate `validate_verification.py --feature harness-evolution`: exit 0.

## Pendências

- Limites de melhor esforço (FIND-011, 017, 018, 019) aceitos pelo usuário em 2026-11-03: `check_proofs.py` é guardrail, não sandbox nem fronteira de segurança contra código malicioso.
- Commit, push e PR autorizados. Merge só depois da revisão e aprovação do usuário no PR.
