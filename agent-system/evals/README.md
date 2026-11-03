# Evals do harness

Fixtures determinísticas dos gates, sem API externa nem serviço pago. Comportamento do modelo (classificação, qualidade de spec, review) não é avaliado aqui.

`python agent-system/scripts/run_evals.py` copia cada fixture para uma pasta temporária, troca `__PYTHON__` pelo interpretador atual, executa os passos e compara exit code, `contains` e `not_contains`. Passo `write` altera um arquivo (por exemplo, para tornar uma prova obsoleta). Passo `stamp` grava no front matter de um relatório o fingerprint atual (`check_proofs.py --fingerprint`), como o revisor faz. `base` herda o projeto de outra fixture. Os TESTs das fixtures rodam arquivos de teste em `checks/`, como um projeto real; nada usa `python -c`.

| Fixture | O que prova |
| --- | --- |
| `complete-feature` | feature M completa passa em todos os gates |
| `ambiguous-spec` | pergunta aberta e REQ sem AC viram aviso; `--strict` reprova |
| `dependency-cycle` | ciclo, dependência inexistente e bloqueio sem causa reprovam o plano |
| `proof-fails` | falha da aplicação (FAIL) e do ambiente (ERROR) são separadas |
| `stale-proof` | código mudou depois da prova; doc do harness não invalida |
| `security-blocking` | risco HIGH exige revisão; achado HIGH aberto e risco aceito sem justificativa bloqueiam |
| `criterion-without-test` | AC sem TEST reprova o gate |
| `weak-test-passes-gate` | limite conhecido: teste sem asserção passa no gate; só a Verification Audit pega |

`test_system.py` também roda `run_evals.py`.
