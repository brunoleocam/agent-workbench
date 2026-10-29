# Sistema spec-driven de agentes

O sistema vive no plugin agent-workbench e só grava timeline e estado dentro de um projeto depois de `/init-agent-system`.

Princípio: não otimizar geração de código. Otimizar desenvolvimento rastreável e verificável.

Intent → Requirement → Specification → Decision → Task → Implementation → Evidence → Review → State.

## O que é automático

- Rules, skills e subagents entram pelo plugin. `00-core-engineering`, `01-request-classification`, `economia-de-tokens` e `mcp-triagem-obrigatoria` valem em toda conversa.
- Hooks do plugin (`hooks/hooks.json`) rodam em todo workspace, mas não escrevem nada se o projeto não tiver `.cursor/agent-system/state.json`.
- Em projeto inicializado, os hooks gravam eventos objetivos em `.cursor/timeline/events.jsonl`: sessão, subagent, edição de arquivo (sem conteúdo), falha de ferramenta, teste reconhecido no shell e o tamanho da resposta do agente.
- `sessionStart` injeta no contexto a task ativa e o próximo passo, só se o projeto estiver inicializado. Se existir `docs/progress/ROADMAP.md`, acrescenta a linha "Você está aqui" e a contagem de tarefas por status.

## O que depende de pessoa

- Instalar num projeto: `/init-agent-system`.
- Aprovar arquitetura, mudança de comportamento de negócio, segurança, infraestrutura nova e remoção de comportamento.
- Commit e push: só quando pedido.
- Criar um agente novo: `/create-agent <nome>`.
- Eventos semânticos (spec, ADR, task, review, checkpoint): o agente chama `record_event.py`. O hook não inventa essa intenção.

## Abrir um projeto

`workspaceOpen` é o evento oficial ao abrir o workspace. Ele não instala o sistema e não altera projeto existente. Instalação automática foi rejeitada porque sobrescreveria config alheia.

`/init-agent-system` copia os scripts e um `hooks.json` para o projeto, preservando hooks que já existiam (backup em `hooks.json.bak-agent-system` se ainda não houver backup). Rules e subagents não são copiados, porque o plugin já os carrega. Cloud Agents não carregam o plugin local: para eles, rode o init com `--for-cloud`, que copia as rules `00` a `07` e os subagents.

## Agentes

O chat principal é o orchestrator, por causa da rule `00`. O Cursor não substitui o agente principal por um subagent. Por isso a rule manda não invocar outro `orchestrator`.

Delegação:

- `planner` — requisitos, spec, ADR, tasks. Sem código.
- `implementer` — uma task já especificada.
- `tester` — testes e evals, com evidência.
- `reviewer` — review independente. Não corrige sozinho.
- `debugger` — reproduz e acha a causa antes do patch.

O registro `agent-system/agents.json` do plugin lista só agentes deste sistema. Agentes built-in do Cursor não entram nele.

## Comandos

São skills com `disable-model-invocation: true`, o mecanismo atual de comando explícito no Cursor. O diretório legado `.cursor/commands` não é usado.

- `/init-agent-system`
- `/create-agent <nome>`
- `/agent-status`
- `/timeline`
- `/help`

## Estado

`.cursor/agent-system/state.json` guarda fase, task ativa, agente ativo, tasks bloqueadas, CRs abertas, review e o próximo passo. Sobrevive ao fim da conversa.

## Roadmap

`docs/progress/ROADMAP.md` é o mapa do plano: fases, tarefas com status (`[x]`, `[~]`, `[ ]`, `[!]`) e a linha "Você está aqui". O `planner` cria e o orchestrator atualiza a linha da tarefa a cada mudança de status (regra `06`). `/roadmap` mostra, cria, atualiza ou gera a visão em Canvas. `/agent-status` mostra o resumo.

## Timeline

`.cursor/timeline/events.jsonl` é append-only e é a fonte de verdade. `/timeline` gera `.cursor/timeline/TIMELINE.md` como vista. Edições repetidas do mesmo arquivo em 20 segundos viram um único `FILE_EDIT`. Senhas, tokens e conteúdo de arquivo não são gravados. Caminho de `.env` ou chave privada vira `[redacted-path]`.

## Change request

Mudança no meio da implementação é classificada. Mudança de requisito, spec ou arquitetura vira CR e atualiza os artefatos antes de continuar. Dependência fica explícita: `TASK-021` depende de `TASK-022`.

## Projeto já em andamento

`/init-agent-system` não move PRD, PDR, ADR nem spec. Ele grava os caminhos encontrados em `.cursor/agent-system/layout.json`. O trabalho seguinte escreve nesses caminhos. O init não resume o código.

1. Abra o repositório.
2. Rode `/init-agent-system`.
3. Peça o trabalho em linguagem normal, por exemplo "quero o checkout reservar estoque antes do pagamento".
4. O orchestrator classifica. Se não for XS, o planner escreve a spec e as tasks. O implementer faz uma task. O tester traz evidência. O reviewer devolve PASS, PASS_WITH_WARNINGS ou FAIL. O checkpoint diz o próximo passo.

## Limitações

- Não existe formato oficial `agents.json` no Cursor. O arquivo é registro deste sistema. O formato oficial do subagent é Markdown com `name` e `description` em `.cursor/agents`, `~/.cursor/agents` ou `agents/` de um plugin.
- `afterShellExecution` não traz exit code. Falha de teste é inferida do texto da saída e pode ficar inconclusiva.
- `sessionStart` não consegue impedir a sessão.
- Hooks do plugin local não rodam em Cloud Agents até o projeto ter os hooks copiados.
- O hook de `stop` não envia follow-up. O loop de correção é decisão do orchestrator, não um loop automático.
