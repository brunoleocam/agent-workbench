---
status: approved
complexity: XL
security_risk: LOW
security_triggers: file_system
approved_by: brunoleocam
---

# Spec: pipeline de arquitetura e DevOps (skills, agentes e lint de infraestrutura)

Problema: quando o Workbench constrói um sistema, as decisões de arquitetura aparecem espalhadas pelas tarefas e ninguém as registra. O agente escolhe banco, cache, fila, forma de deploy e modelo de permissões no momento em que precisa, sem levantar carga, consistência e orçamento, e sem dizer o que muda quando o projeto crescer. O resultado costuma cair em um de dois extremos: um protótipo que não tem caminho de escala, ou Kubernetes, microsserviços e fila em um projeto com cem usuários. Os arquivos de infraestrutura (Dockerfile, Compose, manifests) saem com os erros de sempre: imagem `latest`, container rodando como root, segredo no arquivo, banco exposto na internet, sem healthcheck. O usuário quer aprender arquitetura enquanto decide, e não sabe responder perguntas abstratas ("qual o seu requisito de consistência?").

Resultado: um pipeline com quatro etapas encadeadas, no mesmo formato do pipeline de design. Primeiro, uma entrevista curta, com respostas recomendadas, que levanta os atributos de qualidade e uma estimativa de capacidade. Depois, 2 ou 3 arquiteturas candidatas com trade-offs, para o usuário escolher. A escolhida vira um contrato (`ARCHITECTURE.md` + ADRs) que inclui **estágios de escala com gatilhos medíveis**: o projeto começa no menor desenho que atende a carga de hoje, e o contrato diz qual métrica, em qual valor, justifica o próximo passo. Por fim, uma revisão independente e um lint determinístico de Dockerfile, Compose e Kubernetes. Três agentes novos dividem o trabalho: um decide a arquitetura, um implementa a infraestrutura e um revisa.

Postura padrão (decisão do usuário): escala por estágios, sem overengineering. O alvo de infraestrutura (VPS, PaaS, cloud gerenciada, Kubernetes) não tem padrão: a entrevista sempre pergunta.

Fontes: a lista de temas cobertos pelas referências usa como checklist os temas tratados no canal do YouTube Renato Augusto Tech (CQRS, Event Sourcing, Dual Write, Load Balancing, Sharding, escolha de banco, Server-Sent Events, escala de zero a um milhão de usuários, estudos de caso de System Design). Nenhum conteúdo dos vídeos é transcrito ou copiado; o texto das referências é escrito para o Workbench.

Frente 2, fora deste spec: Clean Code, SOLID e Design Patterns no nível do código (regra, lente do `reviewer` e da skill `refactoring`). Entra num spec próprio depois deste.

Fases de entrega (cada fase fecha com a suíte verde e pode ser revisada sozinha):

1. Contrato e skills: REQ-001 a REQ-020.
2. Lint de infraestrutura e hook: REQ-021 a REQ-030.
3. Agentes, roteamento e integração com o fluxo existente: REQ-031 a REQ-038.

## Requirements

### REQ-001: Entrevista com respostas recomendadas
WHEN o usuário invoca `architecture-discovery` e não existe `architecture/brief.md` com `status: approved`, THE SYSTEM SHALL fazer no máximo 6 perguntas, cada uma com uma resposta recomendada já preenchida, opções em linguagem leiga (sem jargão sem explicação) e no máximo 6 opções por pergunta.

### REQ-002: Perguntar só o que falta
WHEN a resposta de uma pergunta da entrevista já pode ser obtida do pedido, do README, do código, dos arquivos de infraestrutura ou de um brief anterior, THE SYSTEM SHALL usar essa informação, marcá-la como `observado` ou `inferido` no brief e não fazer a pergunta, com a exceção do REQ-003.

### REQ-003: Alvo de infraestrutura sempre perguntado
THE SYSTEM SHALL sempre perguntar o alvo de infraestrutura (por exemplo VPS, PaaS, cloud gerenciada, Kubernetes ou "ainda não sei"). IF o repositório já mostra um alvo (por exemplo `fly.toml`, provider do Terraform, manifests Kubernetes, `docker-compose.yml` de produção), THEN a resposta recomendada SHALL ser esse alvo, citando o arquivo que o mostra.

### REQ-004: Conteúdo do brief
WHEN a entrevista termina, THE SYSTEM SHALL gravar `architecture/brief.md` com front matter `status` e as seções: propósito do sistema; usuários e carga (hoje e em 12 meses, com pico); padrão de acesso (proporção leitura/escrita, tamanho típico dos dados); consistência e tolerância a dado desatualizado; latência e disponibilidade esperadas; dados sensíveis e obrigações legais (por exemplo LGPD); equipe e experiência operacional; orçamento mensal de infraestrutura; alvo de infraestrutura; restrições. Cada informação SHALL estar marcada como `fornecido`, `observado` ou `inferido`.

### REQ-005: Estimativa de capacidade
THE SYSTEM SHALL incluir no brief uma estimativa de capacidade com as contas à mostra: requisições por segundo média e de pico, armazenamento por ano e banda de saída, partindo dos números do brief. Cada número SHALL indicar de quais premissas veio, e um número que depende de premissa `inferida` SHALL ser marcado como estimativa.

### REQ-006: Sistema existente
WHEN o projeto já tem código ou infraestrutura, THE SYSTEM SHALL descrever no brief a arquitetura atual observada (componentes, bancos, filas, forma de deploy), citando os arquivos de onde cada item veio, antes de propor qualquer mudança.

### REQ-007: Opções estruturalmente diferentes
WHEN `architecture-options` roda com um brief aprovado, THE SYSTEM SHALL gravar `architecture/options.md` com 2 ou 3 arquiteturas candidatas, em que cada par difere em pelo menos um destes eixos: número de unidades de deploy, topologia de dados (quantos armazenamentos e de que tipo) e estilo de comunicação (síncrono, assíncrono por fila ou eventos). Em sistema existente, uma das opções SHALL ser manter a arquitetura atual com ajustes.

### REQ-008: Trade-offs de cada opção
THE SYSTEM SHALL descrever cada opção com um diagrama Mermaid dos componentes e uma tabela com: custo mensal em faixa para a carga do brief, complexidade operacional (baixa, média ou alta, com o motivo), pontos únicos de falha, o que acontece quando a carga dobra, e a carga ou a condição em que a opção deixa de servir. THE SYSTEM SHALL marcar uma opção como recomendada e dizer por quê, a partir do brief.

### REQ-009: Menor desenho que atende
THE SYSTEM SHALL recomendar a opção de menor complexidade operacional que atende a carga de pico e os atributos do brief. IF a recomendação inclui um componente que a carga de hoje não exige (por exemplo orquestrador de containers, fila, cache distribuído, banco separado por serviço), THEN THE SYSTEM SHALL citar o item do brief que o exige.

### REQ-010: Escolha pelo usuário
WHEN as opções foram geradas, THE SYSTEM SHALL parar e esperar o usuário escolher uma, sem gerar `ARCHITECTURE.md` antes da escolha.

### REQ-011: Contrato ARCHITECTURE.md
WHEN o usuário aprova uma opção, `architecture-system` SHALL gravar `ARCHITECTURE.md` na raiz do projeto com front matter `status` e exatamente estas seções, nesta ordem: 1. Contexto e atributos de qualidade; 2. Componentes e fronteiras; 3. Dados; 4. Cache; 5. Comunicação; 6. Deploy e infraestrutura; 7. Observabilidade; 8. Segurança e permissões; 9. Estágios de escala; 10. Anti-padrões. Uma seção que não se aplica ao projeto SHALL dizer por que não se aplica, em vez de ser omitida.

### REQ-012: Conteúdo mínimo das seções
THE SYSTEM SHALL incluir, no mínimo: na seção 2, um diagrama Mermaid e a regra de dependência entre módulos; na seção 3, o banco escolhido e o motivo, a estratégia de migração e de backup com RPO e RTO; na seção 4, o que é cacheado, onde, com qual TTL e como invalida, ou a decisão de não ter cache; na seção 5, quais chamadas são síncronas e quais são assíncronas e, para cada fluxo assíncrono, a garantia de entrega e como a idempotência é obtida; na seção 6, o alvo de infraestrutura, os ambientes e o caminho do commit até produção; na seção 7, o formato dos logs (estruturado, com id de correlação), as métricas principais e os alertas com limiar; na seção 8, o modelo de autorização (por exemplo RBAC, ABAC, por tenant), onde os segredos ficam e quais portas e serviços são expostos para fora.

### REQ-013: Estágios de escala com gatilho medível
THE SYSTEM SHALL descrever na seção 9 o estágio atual (estágio 0) e pelo menos dois estágios seguintes. Cada estágio seguinte SHALL ter: o gatilho, como uma métrica com valor e unidade e a fonte da medida (por exemplo "p95 de leitura acima de 300 ms por 7 dias, medido no APM"); a mudança na arquitetura; o custo ou a complexidade que a mudança adiciona; e o que precisa estar pronto antes (por exemplo "sessão fora da memória do processo antes de ter duas instâncias").

### REQ-014: Gatilho vago é recusado
IF um gatilho de estágio não tem métrica com valor e unidade (por exemplo "quando crescer", "quando ficar lento"), THEN THE SYSTEM SHALL reescrever o gatilho com métrica e valor ou perguntar ao usuário qual valor usar, sem gravar o gatilho vago.

### REQ-015: Decisões viram ADR
WHEN uma seção de 3 a 8 registra uma escolha entre alternativas reais (por exemplo Postgres ou MongoDB, Redis ou cache em memória, fila ou chamada direta), THE SYSTEM SHALL criar uma ADR em `docs/architecture/ADR/` no formato do template de ADR do Workbench, com contexto, opções consideradas, decisão e consequências, e a seção do `ARCHITECTURE.md` SHALL citar o número da ADR.

### REQ-016: ARCHITECTURE.md existente
IF `ARCHITECTURE.md` já existe na raiz, THEN THE SYSTEM SHALL ler o arquivo, propor as mudanças por seção e só sobrescrever com confirmação explícita do usuário.

### REQ-017: Mudança de estágio
WHEN o usuário informa que um gatilho foi atingido ou pede para avançar de estágio, THE SYSTEM SHALL atualizar as seções afetadas do `ARCHITECTURE.md`, marcar o novo estágio atual na seção 9 e criar uma ADR para a mudança.

### REQ-018: Orquestração /architecture
WHEN o usuário invoca `architecture`, THE SYSTEM SHALL executar discovery, options, system e review nesta ordem, pulando a etapa cujo artefato já existe com `status: approved`, e parando nos pontos em que o usuário precisa responder ou escolher.

### REQ-019: Referências das skills
THE SYSTEM SHALL incluir nas skills os arquivos de referência:
- `architecture-md-format.md`: as 10 seções e o que cada uma contém;
- `scaling-stages.md`: a progressão típica de estágios (uma instância; banco separado; réplicas de leitura; cache; várias instâncias atrás de load balancer; trabalho assíncrono em fila; particionamento e sharding), com o sinal que costuma justificar cada passo e o que precisa estar pronto antes;
- `data-stores.md`: como escolher entre relacional, documento, chave-valor, colunar larga, busca textual, série temporal e armazenamento de objetos, por padrão de acesso e consistência;
- `caching.md`: cache-aside, write-through, write-behind, TTL, invalidação e proteção contra stampede;
- `messaging.md`: fila, pub/sub, arquitetura orientada a eventos, o problema do dual write e o padrão outbox, idempotência, retentativa com backoff e dead letter queue;
- `patterns.md`: CQRS, Event Sourcing, saga, circuit breaker, rate limiting, replicação, sharding, algoritmos de load balancing, e quando usar polling, Server-Sent Events ou WebSocket, cada um com "quando usar" e "quando não usar";
- `deploy.md`: VPS com Docker Compose e reverse proxy, PaaS, containers gerenciados, Kubernetes, e quando cada um vale o custo operacional;
- `observability.md`: logs estruturados, métricas RED e USE, tracing distribuído (OpenTelemetry), SLO e alerta por sintoma;
- `permissions.md`: autenticação e autorização, RBAC e ABAC, isolamento multi-tenant, menor privilégio para serviços e pessoas, gestão de segredos, com remissão à regra `08-security-engineering`;
- de 3 a 4 estudos de caso completos (brief, opções, contrato resumido e estágios), escritos para o Workbench, por exemplo encurtador de URL, venda de ingressos com pico, placar ao vivo e plataforma de vídeo.

### REQ-020: Créditos
THE SYSTEM SHALL registrar em `skills/architecture/references/CREDITS.md` as fontes que inspiraram as referências, com link e licença quando houver. Texto de fonte com licença não verificada ou incompatível não deve ser copiado.

### REQ-021: CLI do lint de infraestrutura
THE SYSTEM SHALL oferecer `agent-system/scripts/lint_infra.py`, só com stdlib, que aceita arquivos ou diretórios e as opções `--format text|json`, analisa `Dockerfile`, `Dockerfile.*`, `*.Dockerfile`, `docker-compose*.yml`, `docker-compose*.yaml`, `compose*.yml`, `compose*.yaml` e arquivos `.yml`/`.yaml` com `apiVersion:` e `kind:` (manifests Kubernetes), e ignora `node_modules`, `dist`, `build`, `.git`, `vendor` e `.venv`.

### REQ-022: Regras P0 bloqueantes
WHEN o lint encontra um P0, THE SYSTEM SHALL terminar com exit code 1. As regras P0 são:
- `P0-UNPINNED-IMAGE`: `FROM` ou `image:` sem tag, ou com tag `latest` (um digest `@sha256:` conta como fixado; `FROM` que referencia um estágio anterior do mesmo Dockerfile não conta);
- `P0-ROOT-USER`: Dockerfile cujo último estágio não tem `USER`, ou tem `USER root` ou `USER 0`; manifest Kubernetes com `runAsUser: 0` ou `runAsNonRoot: false`;
- `P0-PRIVILEGED`: `privileged: true` em Compose ou Kubernetes, ou `allowPrivilegeEscalation: true` em Kubernetes;
- `P0-SECRET-LITERAL`: valor literal para uma chave cujo nome contém `PASSWORD`, `PASSWD`, `SECRET`, `TOKEN`, `API_KEY`, `APIKEY`, `PRIVATE_KEY` ou `ACCESS_KEY`, em `ENV` ou `ARG` do Dockerfile, em `environment` do Compose ou em `env[].value` do Kubernetes. Interpolação (`${VAR}`, `$VAR`), valor vazio, `valueFrom`, `secretKeyRef` e `env_file` não contam;
- `P0-DB-PORT-PUBLIC`: porta de banco, cache ou broker (5432, 3306, 1433, 27017, 6379, 11211, 9200, 5672, 9092) publicada em todas as interfaces no Compose (sem `127.0.0.1:`), ou exposta por `Service` Kubernetes do tipo `LoadBalancer` ou `NodePort`;
- `P0-DOCKER-SOCKET`: montagem de `/var/run/docker.sock`.

### REQ-023: Regras P1 e P2 de aviso
WHEN o lint encontra apenas P1 ou P2, THE SYSTEM SHALL reportar os achados e terminar com exit code 0. P1: Dockerfile sem `HEALTHCHECK` cujo serviço também não tem `healthcheck` no Compose do mesmo diretório (`P1-NO-HEALTHCHECK`); container de `Deployment`, `StatefulSet` ou `DaemonSet` sem `readinessProbe` ou sem `livenessProbe` (`P1-NO-PROBE`); container Kubernetes sem `resources.requests` ou sem `resources.limits`, ou serviço Compose sem `deploy.resources.limits` nem `mem_limit` (`P1-NO-RESOURCE-LIMITS`); serviço Compose sem `restart` nem `deploy.restart_policy` (`P1-NO-RESTART`); `RUN` que baixa e executa script em um passo (`curl ... | sh`, `wget ... | bash`) (`P1-PIPE-TO-SHELL`); `COPY .` ou `ADD .` sem `.dockerignore` no diretório do contexto (`P1-NO-DOCKERIGNORE`); `ADD` com URL remota (`P1-ADD-REMOTE`). P2: Dockerfile de estágio único que instala dependências de build ou compila (`npm install`, `npm ci`, `go build`, `mvn`, `gradle`, `cargo build`, `pip install` com `gcc`) (`P2-SINGLE-STAGE`); serviço Compose sem `logging` configurado (`P2-NO-LOG-ROTATION`); `CMD` ou `ENTRYPOINT` em forma shell (`CMD npm start` em vez de `CMD ["npm", "start"]`), que impede o processo de receber o sinal de parada (`P2-SHELL-FORM-CMD`).

### REQ-024: Segredo nunca aparece na saída
WHEN o lint reporta `P0-SECRET-LITERAL`, THE SYSTEM SHALL mostrar só o nome da chave e a linha, nunca o valor, em texto e em JSON, e o evento gravado pelo hook SHALL seguir a mesma regra.

### REQ-025: Formato do achado
THE SYSTEM SHALL reportar cada achado com arquivo, linha, ID da regra, severidade, mensagem e sugestão de correção, em texto legível ou em JSON com `--format json`.

### REQ-026: Arquivo que não é infraestrutura
WHEN um `.yml` ou `.yaml` não tem `apiVersion:` e `kind:` e não é um arquivo Compose pelo nome, THE SYSTEM SHALL não analisá-lo (por exemplo workflows do GitHub Actions e configuração de aplicação).

### REQ-027: Supressão pontual
WHERE uma linha ou a linha anterior a ela contém o comentário `infra-lint-disable <REGRA> -- <motivo>`, THE SYSTEM SHALL não reportar essa regra naquela linha. IF o comentário não tiver motivo, THEN THE SYSTEM SHALL ignorar a supressão e reportar um P1 `P1-SUPPRESSION-NO-REASON`.

### REQ-028: Hook informativo
WHEN um arquivo analisado pelo lint, dentro da raiz do projeto, é editado pelo agente, THE SYSTEM SHALL rodar o lint só nesse arquivo, sem bloquear a edição (exit 0) e dentro do timeout do hook, com o mesmo comportamento por host do lint de design: no Claude Code os achados aparecem para o agente; no Cursor o resumo vai para a timeline do projeto com opt-in, como evento `INFRA_LINT` sem trecho do arquivo.

### REQ-029: Testes e CI
THE SYSTEM SHALL ter testes em `agent-system/tests` com fixtures que reproduzem cada regra P0, P1 e P2, uma fixture limpa sem achados (Dockerfile multi-stage com usuário não root, Compose e manifest Kubernetes corretos), uma fixture com segredo literal que confirma que o valor não aparece na saída, e uma fixture de GitHub Actions que não é analisada. Os testes rodam pela suíte que o CI já executa.

### REQ-030: Eval do pipeline
THE SYSTEM SHALL adicionar a `run_evals.py` pelo menos uma fixture que verifica, de forma determinística, a estrutura de um `ARCHITECTURE.md`: as 10 seções na ordem, cada estágio da seção 9 com gatilho que contém número e unidade, e cada ADR citada existindo em `docs/architecture/ADR/`. A mesma checagem SHALL estar disponível como `agent-system/scripts/validate_architecture.py`.

### REQ-031: Agente architect
THE SYSTEM SHALL oferecer o agente `architect`, que roda discovery, options e system, para e espera a escolha de opção, escreve só em `architecture/`, `ARCHITECTURE.md` e `docs/architecture/ADR/`, e não escreve código de produção nem arquivos de infraestrutura.

### REQ-032: Agente architecture-reviewer
THE SYSTEM SHALL oferecer o agente `architecture-reviewer`, independente de quem implementou, que compara código e infraestrutura com `ARCHITECTURE.md` e as ADRs e verifica, no mínimo: componente, banco, cache ou fila no código que não está no contrato; dependência entre módulos que viola a regra da seção 2; fluxo assíncrono sem idempotência declarada; ausência de log estruturado ou de id de correlação onde a seção 7 exige; segredo, porta ou permissão fora do que a seção 8 declara. Reporta achados com severidade e evidência (arquivo e linha ou trecho), não corrige, e não aprova enquanto houver P0 do lint de infraestrutura aberto.

### REQ-033: Registro e roteamento
THE SYSTEM SHALL registrar os dois agentes em `agent-system/agents.json` e os nós correspondentes em `agent-system/workflow.json`, e o `orchestrator` SHALL encaminhar ao `architect` um projeto novo de complexidade L ou XL, ou um pedido que adiciona banco, cache, fila, serviço externo ou unidade de deploy, quando não houver `ARCHITECTURE.md` aprovado, e ao `architecture-reviewer` a revisão de uma mudança que toca arquivos de infraestrutura ou adiciona um desses componentes.

### REQ-034: Planner e implementer seguem o contrato
WHEN existe `ARCHITECTURE.md` aprovado, THE SYSTEM SHALL fazer o `planner` ler o contrato antes de especificar e o `implementer` ler o contrato antes de implementar. IF a tarefa exige um componente, banco, cache, fila ou unidade de deploy que o contrato não tem, THEN THE SYSTEM SHALL parar e abrir um `change-request` em vez de adicionar o componente.

### REQ-035: Implementer roda o lint
WHEN o `implementer` altera um arquivo analisado pelo lint de infraestrutura, THE SYSTEM SHALL rodar `lint_infra.py` nos arquivos alterados e incluir a saída no relato, sem entregar com P0 aberto.

### REQ-036: Documentação do usuário
THE SYSTEM SHALL atualizar `README.md`, `README.pt-BR.md`, a skill `help` e o diagrama do workflow com o pipeline de arquitetura, os três agentes e o lint.

### REQ-037: Agente platform-implementer
THE SYSTEM SHALL oferecer o agente `platform-implementer`, que implementa uma tarefa de infraestrutura por vez seguindo `ARCHITECTURE.md` e as ADRs, escreve só arquivos de infraestrutura, CI/CD, deploy, observabilidade e backup (por exemplo `Dockerfile`, Compose, manifests, `.github/workflows/`, configuração de proxy, scripts de deploy), não altera código da aplicação, e roda `lint_infra.py` nos arquivos alterados antes de entregar, sem entregar com P0 aberto.

### REQ-038: Divisão entre implementer e platform-implementer
WHEN o `orchestrator` encaminha uma tarefa, THE SYSTEM SHALL encaminhar ao `platform-implementer` a tarefa que é inteiramente de infraestrutura (por exemplo subir ambiente, CI/CD, deploy, observabilidade, backup, mudança de estágio de escala) e ao `implementer` a tarefa mista de código e infraestrutura, sem dividir a tarefa mista entre os dois. O `implementer` SHALL alterar na infraestrutura só o que a feature exige e seguir o REQ-035. IF o `platform-implementer` descobre que a tarefa exige mudança no código da aplicação, THEN SHALL parar e abrir um `change-request` em vez de alterar o código.

## Acceptance Criteria

### AC-001: Limite e recomendações da entrevista
- Requirements: REQ-001
Given um projeto sem `architecture/brief.md`
When o usuário invoca `architecture-discovery`
Then a entrevista tem no máximo 6 perguntas, cada uma com resposta recomendada e no máximo 6 opções, e termos como "consistência eventual" ou "RPO" vêm com uma explicação de uma linha.

### AC-002: Pergunta já respondida é pulada
- Requirements: REQ-002
Given um README que diz que o sistema atende cerca de 200 clínicas com 5 usuários cada
When `architecture-discovery` roda
Then não há pergunta sobre o número de usuários, e o brief registra a carga como `observado` citando o README.

### AC-003: Alvo de infra sempre perguntado
- Requirements: REQ-003
Given um repositório com `fly.toml` na raiz
When a entrevista roda
Then existe uma pergunta sobre o alvo de infraestrutura, a resposta recomendada é Fly.io e a pergunta cita `fly.toml`; num repositório sem nenhum indício, a pergunta existe e inclui a opção "ainda não sei".

### AC-004: Estrutura do brief e estimativa
- Requirements: REQ-004, REQ-005
Given uma entrevista concluída com "1.000 usuários ativos por dia, 20 ações por usuário, pico 5 vezes a média"
When o brief é gravado
Then `architecture/brief.md` tem front matter `status`, as seções exigidas com a marcação de origem, e a estimativa mostra a conta de requisições por segundo média e de pico a partir desses números.

### AC-005: Sistema existente descrito antes
- Requirements: REQ-006, REQ-007
Given um projeto com `docker-compose.yml` que declara `app`, `postgres` e `redis`
When discovery e options rodam
Then o brief descreve os três componentes citando o arquivo, e `options.md` tem uma opção que mantém a arquitetura atual com ajustes.

### AC-006: Opções diferentes de verdade
- Requirements: REQ-007, REQ-008
Given um brief aprovado
When `architecture-options` roda
Then cada par de opções difere em pelo menos um dos três eixos, cada opção tem diagrama Mermaid e a tabela com as cinco colunas, e uma opção está marcada como recomendada com o motivo.

### AC-007: Sem overengineering
- Requirements: REQ-009
Given um brief com 50 requisições por segundo de pico, equipe de uma pessoa e orçamento de até 50 dólares por mês
When as opções são geradas
Then a opção recomendada não inclui Kubernetes, microsserviços nem cache distribuído, ou, se incluir algum, cita o item do brief que o exige.

### AC-008: Parada para escolha
- Requirements: REQ-010
Given as opções geradas
When a etapa termina
Then `ARCHITECTURE.md` não foi criado e o agente pediu ao usuário que escolha uma opção.

### AC-009: Seções e conteúdo do contrato
- Requirements: REQ-011, REQ-012
Given uma opção aprovada sem uso de cache
When `architecture-system` roda
Then `ARCHITECTURE.md` tem front matter `status` e as 10 seções na ordem exigida, a seção 4 registra a decisão de não ter cache e o motivo, e as seções 2, 3, 5, 6, 7 e 8 têm o conteúdo mínimo do REQ-012.

### AC-010: Estágios com gatilho medível
- Requirements: REQ-013, REQ-030
Given um `ARCHITECTURE.md` gerado
When `validate_architecture.py` roda
Then a seção 9 tem o estágio 0 e pelo menos dois estágios seguintes, cada um com gatilho contendo número e unidade, mudança, custo e pré-requisito, e o script termina com exit 0.

### AC-011: Gatilho vago recusado
- Requirements: REQ-014, REQ-030
Given o usuário pede "adicionar cache quando o sistema ficar lento"
When o estágio é gravado
Then o gatilho gravado tem métrica com valor e unidade, ou o agente perguntou o valor; e `validate_architecture.py` sobre um contrato com gatilho "quando crescer" termina com exit 1 citando o estágio.

### AC-012: Decisão vira ADR citada
- Requirements: REQ-015, REQ-030
Given um contrato que escolhe Postgres em vez de MongoDB
When `architecture-system` termina
Then existe uma ADR nova em `docs/architecture/ADR/` com contexto, opções, decisão e consequências, a seção 3 cita o número dela, e `validate_architecture.py` falha se a ADR citada não existir.

### AC-013: Não sobrescreve sem confirmação
- Requirements: REQ-016
Given um `ARCHITECTURE.md` existente
When `architecture-system` roda
Then o agente mostra as mudanças por seção e o arquivo só muda depois da confirmação do usuário.

### AC-014: Avanço de estágio
- Requirements: REQ-017
Given um contrato no estágio 0 e o usuário diz que o p95 de leitura passou do gatilho do estágio 1
When o agente processa o pedido
Then a seção 9 marca o estágio 1 como atual, as seções afetadas mudam, e existe uma ADR nova para a mudança.

### AC-015: /architecture pula etapa aprovada
- Requirements: REQ-018
Given `architecture/brief.md` com `status: approved` e nenhum `options.md`
When o usuário invoca `architecture`
Then a entrevista não roda e o fluxo começa em `architecture-options`.

### AC-016: Referências e créditos presentes
- Requirements: REQ-019, REQ-020
Given as skills de arquitetura instaladas
When os arquivos são listados
Then existem os nove arquivos de referência do REQ-019, de 3 a 4 estudos de caso e `CREDITS.md`; `patterns.md` tem "quando usar" e "quando não usar" para cada padrão; e nenhum arquivo contém transcrição de vídeo.

### AC-017: Varredura, exclusões e arquivo que não é infra
- Requirements: REQ-021, REQ-026
Given um diretório com `Dockerfile` e `node_modules/x/Dockerfile`, ambos com `FROM node:latest`, e `.github/workflows/ci.yml` com `image: node:latest`
When `lint_infra.py` roda no diretório
Then só o `Dockerfile` da raiz é reportado.

### AC-018: Cada P0 reprova
- Requirements: REQ-022, REQ-025
Given uma fixture para cada regra P0
When o lint roda em cada uma
Then o exit code é 1 e o achado traz arquivo, linha, ID da regra, severidade, mensagem e sugestão.

### AC-019: Casos que não são P0
- Requirements: REQ-022
Given um Dockerfile multi-stage com `FROM node:20.11-alpine AS build`, `FROM build AS test`, `FROM gcr.io/distroless/nodejs20@sha256:<digest>` e `USER 1000`, e um Compose com `DB_PASSWORD: ${DB_PASSWORD}` e `ports: ["127.0.0.1:5432:5432"]`
When o lint roda
Then não há nenhum P0.

### AC-020: P1 e P2 só avisam
- Requirements: REQ-023
Given um Compose sem `restart` e um manifest Kubernetes sem `resources`, sem nenhum P0
When o lint roda
Then os achados `P1-NO-RESTART` e `P1-NO-RESOURCE-LIMITS` aparecem e o exit code é 0.

### AC-021: Segredo não vaza
- Requirements: REQ-024
Given um Compose com `API_KEY: sk-test-abc123`
When o lint roda em texto, em JSON e pelo hook
Then o achado cita `API_KEY` e a linha, e a string `sk-test-abc123` não aparece em nenhuma saída nem no evento da timeline.

### AC-022: Saída JSON
- Requirements: REQ-025
Given uma fixture com achados
When o lint roda com `--format json`
Then a saída é JSON válido com uma lista de achados contendo `file`, `line`, `rule`, `severity`, `message` e `suggestion`.

### AC-023: Supressão com e sem motivo
- Requirements: REQ-027
Given um Compose com `/var/run/docker.sock` montado e precedido de `infra-lint-disable P0-DOCKER-SOCKET -- agente de CI isolado`, e outra montagem igual precedida de `infra-lint-disable P0-DOCKER-SOCKET` sem motivo
When o lint roda
Then a primeira montagem não gera achado, a segunda gera `P0-DOCKER-SOCKET` e `P1-SUPPRESSION-NO-REASON`, e o exit code é 1.

### AC-024: Hook não bloqueia
- Requirements: REQ-028
Given o agente edita `Dockerfile` e introduz `FROM python:latest`
When o hook roda
Then no Claude Code o achado aparece para o agente; no Cursor a resposta é vazia e a timeline de um projeto com opt-in ganha um evento `INFRA_LINT` sem trecho do arquivo; o hook termina com exit 0 dentro do timeout; e edições em `.py`, `.md` ou fora da raiz do projeto não disparam o lint de infraestrutura.

### AC-025: Testes no CI
- Requirements: REQ-029
Given as fixtures do lint
When `python -I agent-system/scripts/test_system.py` roda no CI (Ubuntu e Windows)
Then os testes do lint passam, incluindo a fixture limpa sem achados, a fixture de segredo e a fixture de GitHub Actions ignorada.

### AC-026: Eval de estrutura
- Requirements: REQ-030
Given a fixture de `ARCHITECTURE.md` válida e uma com a seção 9 fora de ordem
When `run_evals.py` roda
Then o eval passa na primeira e reprova a segunda citando a seção.

### AC-027: architect não implementa
- Requirements: REQ-031
Given o agente `architect` recebe "quero criar uma API de agendamento"
When ele termina
Then gravou só arquivos em `architecture/`, `ARCHITECTURE.md` e `docs/architecture/ADR/`, sem código de produção nem Dockerfile, e parou na escolha de opção.

### AC-028: architecture-reviewer encontra desvio
- Requirements: REQ-032
Given um contrato sem fila e um código que publica mensagens em RabbitMQ
When o `architecture-reviewer` revisa
Then há um achado que cita arquivo e linha do uso do RabbitMQ e a seção 5 do contrato, o veredito não é aprovado, e o reviewer não altera arquivos.

### AC-029: Agentes registrados e roteados
- Requirements: REQ-033
Given o plugin instalado
When `agents.json` e `workflow.json` são validados e o orchestrator recebe "adicionar busca textual com Elasticsearch" num projeto sem `ARCHITECTURE.md`
Then os dois agentes estão registrados como ativos, `validate_workflow.py` termina com exit 0, e o orchestrator encaminha ao `architect`.

### AC-030: Componente fora do contrato abre change request
- Requirements: REQ-034
Given um `ARCHITECTURE.md` aprovado sem cache e uma tarefa cuja implementação pede Redis
When o `implementer` encontra a necessidade
Then ele para sem adicionar o Redis e abre um `change-request` citando a seção 4 do contrato.

### AC-031: Implementer roda o lint
- Requirements: REQ-035
Given uma tarefa que altera `docker-compose.yml`
When o `implementer` entrega
Then o relato inclui a saída de `lint_infra.py` nos arquivos alterados, sem P0.

### AC-032: Documentação atualizada
- Requirements: REQ-036
Given a fase 3 concluída
When os READMEs, `/help` e o diagrama são lidos
Then os três citam `/architecture`, os agentes `architect`, `architecture-reviewer` e `platform-implementer` e o `lint_infra.py`, e o teste de drift do diagrama passa.

### AC-033: platform-implementer fica na infraestrutura
- Requirements: REQ-037
Given uma tarefa "configurar deploy na VPS com Docker Compose e Caddy" e um `ARCHITECTURE.md` aprovado
When o `platform-implementer` entrega
Then só arquivos de infraestrutura e deploy mudaram, nenhum arquivo de código da aplicação mudou, e o relato inclui a saída de `lint_infra.py` sem P0.

### AC-034: Roteamento de tarefa de infra e de tarefa mista
- Requirements: REQ-038, REQ-033
Given as tarefas "adicionar pipeline de CI com testes" e "adicionar upload de arquivos com volume no Compose"
When o orchestrator encaminha cada uma
Then a primeira vai ao `platform-implementer`, a segunda vai inteira ao `implementer`, e o grafo do `workflow.json` tem as duas arestas.

### AC-035: platform-implementer não altera código da aplicação
- Requirements: REQ-038
Given uma tarefa de healthcheck em que a aplicação não tem rota `/health`
When o `platform-implementer` encontra a falta
Then ele não cria a rota no código e abre um `change-request` dizendo que a rota precisa ser criada.

## Assumptions

- Os projetos-alvo são sistemas com back-end (API, workers, banco). Projeto só de front-end estático pode usar a entrevista, mas a maior parte do contrato vai dizer "não se aplica".
- O lint é heurístico, baseado em varredura de texto linha a linha, sem parser YAML (só stdlib). Falso positivo e falso negativo são aceitos dentro do que os fixtures cobrem; YAML com âncoras, multi-documento complexo ou Helm templates (`{{ }}`) pode ser analisado de forma parcial.
- Helm charts, Terraform, Pulumi e CloudFormation ficam fora do lint nesta versão; as skills podem recomendá-los.
- Os valores de custo em `options.md` são faixas aproximadas, sem consulta a preço em tempo real, e o contrato diz isso.
- O hook reaproveita `agent-system/scripts/hook.py`, o timeout já configurado e o mecanismo por host do lint de design.

## Constraints

- Só stdlib Python, compatível com 3.10 a 3.13, Windows e Linux, como o resto de `agent-system/scripts`.
- Skills seguem o formato de `skills/<nome>/SKILL.md` com `references/` e funcionam em Cursor e Claude Code.
- Nenhuma referência transcreve conteúdo de vídeo, curso ou livro; estudos de caso não usam nome ou marca de empresa real como se fosse o sistema dela.
- O hook nunca bloqueia nem altera arquivo, e nunca grava valor de segredo.
- As skills existentes `security-best-practices` e `security-review` continuam valendo; a seção 8 do contrato cita a regra `08` e a revisão de segurança segue com o `security-reviewer`.

Fora de escopo: provisionamento real de infraestrutura (criar VPS, cluster ou recurso de cloud), geração de Terraform ou Helm, teste de carga, cálculo de custo com preço real de provedor, migração automática de arquitetura, Clean Code, SOLID e Design Patterns no nível do código (Frente 2).

## Open Questions

- [x] Quem implementa a infraestrutura: meio-termo (decisão do usuário, 2026-11-13). O agente novo `platform-implementer` faz as tarefas inteiramente de infraestrutura, e o `implementer` faz as tarefas mistas e roda o lint (REQ-037, REQ-038).
- [x] Regra para `CMD`/`ENTRYPOINT` em forma shell: entra como P2 `P2-SHELL-FORM-CMD` (decisão do usuário, 2026-11-13).
- [x] Estudos de caso: os quatro sugeridos (encurtador, ingressos, placar ao vivo, vídeo), só como referência (decisão do usuário, 2026-11-13).

## Decisions

- Duas frentes, arquitetura e DevOps primeiro; Clean Code, SOLID e Design Patterns num spec próprio depois (escolha do usuário, 2026-11-13).
- Escala por estágios com gatilho medível, começando no menor desenho que atende a carga (escolha do usuário).
- Sem alvo de infraestrutura padrão: a entrevista sempre pergunta, recomendando o que o repositório já mostra (escolha do usuário).
- Lint determinístico de Dockerfile, Compose e Kubernetes, bloqueando P0 e só avisando P1/P2 (escolha do usuário), no mesmo formato de saída e de supressão do `lint_design.py`.
- Opções em Markdown com Mermaid, não em HTML: a escolha de arquitetura se faz lendo trade-offs, não reagindo a um visual.
- Skills separadas (`architecture-discovery`, `architecture-options`, `architecture-system`, `architecture-review`) mais a skill `architecture` que encadeia as quatro, espelhando o pipeline de design.
- O canal Renato Augusto Tech entra como checklist de temas a cobrir, não como fonte de texto.
