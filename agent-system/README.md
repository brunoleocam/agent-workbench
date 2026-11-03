# Sistema spec-driven de agentes

O sistema vive no plugin agent-workbench e só grava timeline e estado dentro de um projeto depois de `/init-agent-system`.

Princípio: não otimizar geração de código. Otimizar desenvolvimento rastreável, verificável e seguro.

Intent → Requirement → Specification → Decision → Task → Implementation → Evidence → Review → State.

## Camadas

| Camada | Onde | Responsabilidade |
| --- | --- | --- |
| Rules | `rules/` | Princípios e limites permanentes. `00`, `01`, `economia-de-tokens` e `mcp-triagem-obrigatoria` sempre; `02`–`08` por fase |
| Skills | `skills/` | Procedimentos (`/feature`, `/code-review`, `/security-review`...) |
| Agents | `agents/` | Papéis com contrato de entrada e saída ([`docs/contracts.md`](docs/contracts.md)) |
| Workflows | tabela adaptativa em `agents/orchestrator.md` | Sequência por classe, complexidade e risco |
| Scripts | `agent-system/scripts/` | Validação e operações determinísticas ([`docs/cli.md`](docs/cli.md)) |
| Hooks | `hooks/hooks.json` | Observabilidade fail-open: timeline e contexto da sessão |
| Evals | `agent-system/evals/` | Fixtures determinísticas dos gates |
| References | `skills/security-best-practices/references/` | Conhecimento por stack, carregado sob demanda |

Decisões: [ADR-0001](../docs/architecture/ADR/0001-formato-dos-artefatos-rastreaveis.md) (formato), [ADR-0002](../docs/architecture/ADR/0002-provas-fingerprint-e-politica-de-comandos.md) (provas e comandos), [ADR-0003](../docs/architecture/ADR/0003-papeis-de-verificacao-e-seguranca.md) (papéis).

## Fluxo adaptativo

```text
pedido → classe + complexidade + risco de segurança
       → spec (REQ/AC, EARS) → validate_spec --require-approval      M+
       → ADR                                                          só decisão de arquitetura
       → tarefas (TASK/TEST) → validate_tasks                         M+
       → implementer, uma tarefa por vez
       → security-reviewer                                            risco HIGH/CRITICAL
       → tester → check_proofs (exit code real + fingerprint)         M+
       → reviewer com Verification Audit                              M+
       → validate_verification (gate de conclusão)                    M+
       → checkpoint + estado
```

XS: faz direto. S: faz direto com o teste que prova a mudança. Nenhum gate é obrigatório em XS e S.

## Rastreabilidade

IDs `REQ`, `AC`, `ADR`, `TASK`, `TEST`, `PROOF`, `FIND` e `SEC`, cada um como título que começa com o ID, ligados por linhas `- Requirements:`, `- Acceptance:`, `- Verification:`. Um slug por feature, o mesmo arquivo em cada pasta do `layout.json`. Formato: [`docs/artifacts.md`](docs/artifacts.md).

EARS é recomendado para requisito comportamental; requisito técnico pode ser linguagem natural estruturada. Os scripts checam estrutura. Se a regra de negócio faz sentido continua sendo do planner, do reviewer e do usuário.

## Validação determinística

| Script | Pergunta que responde |
| --- | --- |
| `validate_spec.py` | A spec tem REQ e AC únicos, ligados, com premissas, perguntas e aprovação? |
| `validate_tasks.py` | Cada tarefa tem vínculo, verificação, conclusão, dependências válidas e evidência quando `done`? |
| `check_proofs.py` | Os TESTs passam de verdade? Grava stdout, stderr, exit code, horário e fingerprint |
| `validate_verification.py` | Pode declarar pronto? Critérios testados, provas do código atual, review, segurança, achados e tarefas |

Exit codes comuns: `0` ok, `1` gate reprovado, `2` configuração. `--json` e `--strict` em todos.

A prova não exige commit. O fingerprint (conteúdo de cada arquivo do projeto, sem `.cursor/` nem Markdown das pastas de doc; não depende do HEAD) diz se o código mudou depois do teste, e continua igual depois de commitar o mesmo conteúdo. `check_proofs.py` roda sem shell, só executáveis permitidos, recusa subcomandos conhecidos de instalação e publicação (melhor esforço, por nome; não é sandbox), recusa código inline por melhor esforço (`python -c`, `node -e`, também atrás de `uv run` e similares) e encerra a árvore de processos no timeout. Um TEST aponta para o runner ou para um arquivo de teste do projeto. As provas ficam em `.cursor/agent-system/proofs/`, são locais e não devem ser versionadas.

## Segurança

- Rule `08-security-engineering`: limites curtos (negar por padrão, validação, segredos, upload, integrações, erros e logs).
- Skill `security-best-practices`: secure coding com dez referências por stack (PHP, Laravel, Express, React, Next.js, Python, FastAPI, Django, ASP.NET Core, Spring). O init grava em `layout.json` quais referências valem para o projeto.
- Skill `/security-review` e agente `security-reviewer`: relatório `SEC-NNN` com severidade CRITICAL a INFORMATIONAL, confiança e classificação (confirmado, provável, suspeita, hardening, risco aceito). Relatório primeiro; correção só com autorização.
- Risco de segurança é dimensão separada da complexidade (rule `01`). HIGH e CRITICAL tornam a revisão de segurança obrigatória no gate.

## Lições aprendidas

`lessons.py` grava em `.cursor/agent-system/lessons.json` (fonte de verdade) e gera `LESSONS.md`. Agentes propõem (`candidate`); só o usuário confirma ou rejeita. O `sessionStart` injeta até cinco títulos confirmados; o resto é carregado por categoria (`list --status confirmed --category X`). Texto que parece segredo e duplicatas são recusados.

## Evals

`run_evals.py` roda as fixtures de `evals/fixtures/`: projetos mínimos que provam o comportamento dos gates (feature completa passa, prova obsoleta reprova, risco HIGH exige revisão...). Comportamento do modelo não é avaliado automaticamente.

Adiado nesta versão, por não ter consumidor concreto: métricas agregadas da timeline e avaliação manual de agentes por cenários e rubricas.

## O que é automático

- Rules, skills e subagents entram pelo plugin.
- Hooks do plugin rodam em todo workspace, mas não escrevem nada se o projeto não tiver `.cursor/agent-system/state.json`.
- Em projeto inicializado, os hooks gravam em `.cursor/timeline/events.jsonl`: sessão, subagent, edição de arquivo (sem conteúdo), falha de ferramenta, teste reconhecido no shell (marcado `inferred: true`) e o tamanho da resposta do agente.
- `sessionStart` injeta a task ativa, o próximo passo, a linha do roadmap e as lições confirmadas.
- Os validadores gravam seus próprios eventos e atualizam `state.json → verification.<slug>`.

## O que depende de pessoa

- Instalar num projeto: `/init-agent-system`.
- Aprovar spec, arquitetura, mudança de comportamento de negócio, segurança, permissão, infraestrutura nova e remoção de comportamento.
- Aceitar risco residual (com justificativa no relatório).
- Confirmar ou rejeitar lições.
- Commit e push: só quando pedido.
- Criar um agente novo: `/create-agent <nome>`.
- Eventos semânticos (spec, ADR, task, review, checkpoint): o agente chama `record_event.py`. O hook não inventa essa intenção.

## Abrir um projeto

`workspaceOpen` não instala o sistema e não altera projeto existente.

`/init-agent-system` copia os scripts e um `hooks.json` para o projeto, preservando hooks que já existiam (backup em `hooks.json.bak-agent-system`). Script local sem a marca `agent-system-managed` e diferente do plugin é preservado. `state.json` existente só ganha chaves novas. `overrides` e `proof_allow` do `layout.json` sobrevivem a um novo init. Rules e subagents não são copiados, porque o plugin já os carrega. Cloud Agents não carregam o plugin local: para eles, `--for-cloud` copia as rules `00` a `08` e os subagents.

## Agentes

O chat principal é o orchestrator, por causa da rule `00`. O Cursor não substitui o agente principal por um subagent. Por isso a rule manda não invocar outro `orchestrator`.

- `planner` — requisitos (EARS), spec, ADR, tasks. Sem código.
- `implementer` — uma task já especificada.
- `tester` — testes, evals e provas com exit code real.
- `reviewer` — review independente com Verification Audit. Não corrige sozinho. Absorve o papel de verifier (ADR-0003).
- `security-reviewer` — achados de segurança com referências da stack. Não corrige.
- `debugger` — reproduz e acha a causa antes do patch.

O registro `agent-system/agents.json` lista só agentes deste sistema. Agentes built-in do Cursor não entram nele (o built-in `security-review` é outro agente).

## Comandos

Skills com `disable-model-invocation: true` são comandos explícitos: `/init-agent-system`, `/create-agent <nome>`, `/agent-status`, `/timeline`, `/help`, `/security-review`. As demais (`/feature`, `/code-review`, `/lessons`...) também podem ser invocadas pelo nome. Guia completo: `/help`.

## Estado

`.cursor/agent-system/state.json` guarda fase, task ativa, agente ativo, tasks bloqueadas, CRs abertas, review, próximo passo e o resultado de cada gate por feature (`verification`). Sobrevive ao fim da conversa.

## Roadmap

`docs/progress/ROADMAP.md` é o mapa do plano: fases, tarefas com status (`[x]`, `[~]`, `[ ]`, `[!]`) e a linha "Você está aqui". `/roadmap` mostra, cria, atualiza ou gera a visão em Canvas.

## Timeline

`.cursor/timeline/events.jsonl` é append-only e é a fonte de verdade. `/timeline` gera `TIMELINE.md`. Edições repetidas do mesmo arquivo em 20 segundos viram um único `FILE_EDIT`. Senhas, tokens (inclusive `--token valor`, prefixos conhecidos e credencial em URL) e conteúdo de arquivo não são gravados. Caminho de `.env` ou chave privada vira `[redacted-path]`.

## Projeto já em andamento

`/init-agent-system` não move PRD, PDR, ADR nem spec. Ele grava os caminhos encontrados em `layout.json`. Spec antiga sem IDs não é migrada nem validada; o formato rastreável entra com o próximo trabalho M ou maior.

## Testes

```powershell
python agent-system/scripts/test_system.py            # suíte completa
python agent-system/scripts/test_system.py proofs     # filtra por nome de módulo ou função
python agent-system/scripts/run_evals.py              # só as evals determinísticas
```

## Limitações

- Não existe formato oficial `agents.json` no Cursor. O arquivo é registro deste sistema.
- `afterShellExecution` não traz exit code. O resultado de teste do hook é inferido do texto e marcado `inferred`; só `check_proofs.py` produz resultado determinístico.
- A política do `check_proofs.py` separa runner e arquivo de teste de comando arbitrário, mas não é sandbox: um arquivo de teste executa o que contiver. `--allow-inline` e `--allow-shell` só com autorização do usuário.
- O encerramento da árvore de processos no timeout foi testado no Windows e no Linux (WSL2); macOS não foi testado.
- Os validadores checam estrutura, não semântica. Um teste que não prova nada passa no gate (fixture `weak-test-passes-gate`); quem pega é a Verification Audit.
- A detecção de superfície de ataque é por nome de arquivo e manifesto: indício, não análise.
- `sessionStart` não consegue impedir a sessão. O hook de `stop` não envia follow-up; o loop de correção é decisão do orchestrator.
- Hooks do plugin local não rodam em Cloud Agents até o projeto ter os hooks copiados. Skills e referências não são copiadas para o Cloud.
- Não há avaliação automática de comportamento de modelo.
