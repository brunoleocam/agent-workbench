---
status: approved
complexity: XL
security_risk: LOW
security_triggers: file_system, command_execution
approved_by: brunoleocam
---

# Spec: pipeline de design UI/UX (skills, agentes e lint anti-slop)

Problema: quando o Workbench gera front-end, o agente decide o visual sozinho e tela por tela. O resultado tem cara de IA (índigo padrão, gradiente roxo, emoji como ícone, hero centralizado, sequência Hero → Features → Pricing) e não mantém consistência entre telas. A skill `apple-design` cobre movimento, mas não decide identidade visual. O usuário não tem experiência de UI/UX e não sabe responder perguntas abstratas ("qual escala de espaçamento?").

Resultado: um pipeline com quatro etapas encadeadas. Primeiro uma entrevista curta com respostas recomendadas. Depois 3 direções visuais renderizadas em HTML, para o usuário escolher reagindo ao que vê. A direção escolhida vira um contrato (`DESIGN.md` + `design/tokens.css`) que toda tela segue. Por fim, uma revisão com autocrítica e um lint determinístico que reprova os sinais clássicos de design genérico. Três agentes dividem o trabalho: decidir o visual, implementar e revisar de forma independente.

Fontes adaptadas: formato DESIGN.md de VoltAgent/awesome-design-md (MIT); `craft/anti-ai-slop.md`, `discovery-question-form`, `reference-design-contract` e `critique-theater` de nexu-io/open-design (Apache-2.0); prioridades, dials e padrão master + override de nextlevelbuilder/ui-ux-pro-max-skill; regras de microcopy e formato de eval de petergyang/no-ai-slop (MIT); autocrítica de seis eixos e regras do slop-test de Nutlope/hallmark (MIT).

## Requirements

### REQ-001: Entrevista com respostas recomendadas
WHEN o usuário invoca `design-discovery` e não existe `design/brief.md` com `status: approved`, THE SYSTEM SHALL fazer no máximo 5 perguntas, cada uma com uma resposta recomendada já preenchida, opções em linguagem leiga (sem jargão de design) e no máximo 7 opções por pergunta.

### REQ-002: Perguntar só o que falta
WHEN a resposta de uma pergunta da entrevista já pode ser obtida do pedido, do README, do código ou de um brief anterior, THE SYSTEM SHALL usar essa informação, marcá-la como inferida no brief e não fazer a pergunta.

### REQ-003: Brief com referências decompostas
WHEN a entrevista termina, THE SYSTEM SHALL gravar `design/brief.md` com front matter `status`, e as seções público, tarefa principal do usuário, tom de voz, densidade, idioma, restrições e referências. Cada referência deve ter uma tabela Keep / Change / Do not copy, e cada informação deve estar marcada como `fornecido`, `observado` ou `inferido`.

### REQ-004: Pedido de referências
WHEN o usuário não forneceu nenhuma referência, THE SYSTEM SHALL pedir de 2 a 3 referências (URL ou imagem) e, IF o usuário não tiver nenhuma, THEN seguir sem elas e registrar no brief que a direção parte só do brief.

### REQ-005: Três direções estruturalmente diferentes
WHEN `design-directions` roda com um brief aprovado, THE SYSTEM SHALL gerar 3 direções em que cada par difere em pelo menos dois destes eixos: macroestrutura de layout, família tipográfica de display, temperatura da paleta e densidade. Uma diferença só de cor não conta.

### REQ-006: Prévias em HTML no projeto
THE SYSTEM SHALL gravar cada direção como `design/directions/a.html`, `b.html` e `c.html`, mais um `design/directions/index.html` que mostra as três lado a lado. Os arquivos devem ser autocontidos (CSS inline, sem JavaScript ou imagem externos), podem carregar fontes externas só com pilha de fallback local, e devem usar o conteúdo real do brief, sem lorem ipsum nem texto de preenchimento.

### REQ-007: Identificação de cada direção
THE SYSTEM SHALL abrir cada arquivo de direção com um comentário contendo nome da direção, a postura em uma frase, a escolha distintiva (o "20%") e os valores dos dials variedade, movimento e densidade (1 a 10).

### REQ-008: Escolha pelo usuário
WHEN as 3 direções foram geradas, THE SYSTEM SHALL parar e esperar o usuário escolher uma, sem gerar DESIGN.md antes da escolha.

### REQ-009: Ajuste da direção escolhida
WHEN o usuário pede ajuste na direção escolhida, por dial (1 a 10) ou por texto livre, THE SYSTEM SHALL regenerar só a direção escolhida, mantendo os arquivos das outras duas.

### REQ-010: Mistura de direções
IF o usuário pede para combinar partes de direções diferentes, THEN THE SYSTEM SHALL explicar o risco de incoerência e propor uma única versão coerente que incorpore o que foi pedido, em vez de colar as partes.

### REQ-011: Contrato DESIGN.md
WHEN o usuário aprova uma direção, `design-system` SHALL gravar `DESIGN.md` na raiz do projeto com front matter `status` e exatamente estas seções, nesta ordem: 1. Tema visual e atmosfera; 2. Cor; 3. Tipografia; 4. Espaçamento e grid; 5. Layout e composição; 6. Componentes; 7. Movimento e interação; 8. Voz e microcopy; 9. Anti-padrões.

### REQ-012: Tokens
THE SYSTEM SHALL gravar `design/tokens.css` com custom properties em `:root` para cor (cada cor com papel semântico e, para cada cor usada como fundo de texto, um par `-ink` com contraste mínimo 4.5:1), escala tipográfica, famílias de fonte (no máximo 3), escala de espaçamento em múltiplos de 4px, raios, sombras e durações de movimento. Todo valor citado em `DESIGN.md` deve existir em `tokens.css` com o mesmo valor.

### REQ-013: Escolha distintiva registrada
THE SYSTEM SHALL registrar na seção 1 do `DESIGN.md` a escolha distintiva da direção, em uma frase concreta (por exemplo uma fonte, uma proporção ou uma decisão de cor), e na seção 9 os anti-padrões proibidos para o projeto, incluindo os P0 do lint.

### REQ-014: DESIGN.md existente
IF `DESIGN.md` já existe na raiz, THEN THE SYSTEM SHALL ler o arquivo, propor as mudanças por seção e só sobrescrever com confirmação explícita do usuário.

### REQ-015: Exceções por página
WHERE uma página precisa de regra diferente do contrato geral, THE SYSTEM SHALL gravar a exceção em `design/pages/<pagina>.md`, citando qual regra do `DESIGN.md` ela substitui e por quê.

### REQ-016: Revisão de design
WHEN `design-review` roda sobre uma tela ou prévia, THE SYSTEM SHALL dar nota de 1 a 5 em seis eixos (postura, hierarquia, execução, especificidade, contenção e variedade). IF algum eixo tiver nota abaixo de 3, THEN deve revisar e reavaliar, com no máximo 3 passadas. Também deve aplicar a checklist P0/P1/P2 e as regras de microcopy e rodar o lint.

### REQ-017: Relato da revisão
THE SYSTEM SHALL relatar a revisão em prosa, no idioma do usuário: o que verificou, o que corrigiu, as notas finais e o que ficou aberto com o motivo, sem gravar arquivo de pontuação.

### REQ-018: Orquestração /design
WHEN o usuário invoca `design`, THE SYSTEM SHALL executar discovery, directions, design-system e review nesta ordem, pulando a etapa cujo artefato já existe com `status: approved`, e parando nos pontos em que o usuário precisa responder ou escolher.

### REQ-019: ui-ux segue o contrato
WHEN `ui-ux` constrói uma tela e existe `DESIGN.md`, THE SYSTEM SHALL ler `DESIGN.md`, `design/tokens.css` e a exceção da página quando houver, e usar só os tokens declarados para cor, fonte, espaçamento, raio, sombra e duração.

### REQ-020: ui-ux sem contrato
IF `ui-ux` vai criar uma interface visual nova e não existe `DESIGN.md`, THEN THE SYSTEM SHALL recomendar rodar `design` antes, sem bloquear mudança pequena em interface que já tem sistema visual próprio.

### REQ-021: Referências das skills
THE SYSTEM SHALL incluir nas skills os arquivos de referência `anti-slop.md` (regras P0/P1/P2 e a regra 80/20), `design-md-format.md` (as 9 seções com o que cada uma contém), `microcopy.md` e de 3 a 4 exemplos de DESIGN.md com estéticas diferentes, escritos para o Workbench e sem copiar identidade de marca.

### REQ-022: Atribuição
THE SYSTEM SHALL registrar a atribuição das fontes adaptadas, com licença e link, em um arquivo de créditos dentro das skills de design. Texto de fonte com licença não verificada ou incompatível não deve ser copiado.

### REQ-023: Agente designer
THE SYSTEM SHALL oferecer o agente `designer`, que roda discovery, directions e design-system, para e espera a escolha de direção, e não escreve código de produção.

### REQ-024: Agente frontend-implementer
THE SYSTEM SHALL oferecer o agente `frontend-implementer`, que implementa uma tela ou tarefa por vez seguindo `DESIGN.md` e os tokens, cobre os estados vazio, carregando, erro e sucesso, e roda o lint nos arquivos alterados antes de entregar.

### REQ-025: Agente design-reviewer
THE SYSTEM SHALL oferecer o agente `design-reviewer`, independente de quem implementou, que compara a tela com `DESIGN.md` e `design/brief.md`, reporta achados com severidade e evidência (arquivo e linha ou trecho), não corrige, e não aprova enquanto houver P0 do lint aberto.

### REQ-026: Registro e roteamento dos agentes
THE SYSTEM SHALL registrar os três agentes em `agent-system/agents.json`, e o `orchestrator` SHALL encaminhar trabalho de interface visual para `designer` quando não houver `DESIGN.md` aprovado, para `frontend-implementer` na implementação e para `design-reviewer` na revisão de design.

### REQ-027: CLI do lint
THE SYSTEM SHALL oferecer `agent-system/scripts/lint_design.py`, só com stdlib, que aceita arquivos ou diretórios, as opções `--design`, `--tokens` e `--format text|json`, analisa arquivos `.html`, `.css`, `.scss`, `.jsx`, `.tsx`, `.vue` e `.svelte`, e ignora `node_modules`, `dist`, `build`, `.next` e `.git`.

### REQ-028: Regras P0 bloqueantes
WHEN o lint encontra um P0, THE SYSTEM SHALL terminar com exit code 1. As regras P0 são:
- `P0-INDIGO`: hex índigo/violeta padrão do Tailwind (`#6366f1`, `#4f46e5`, `#4338ca`, `#3730a3`, `#8b5cf6`, `#7c3aed`, `#a855f7`) ou classe utilitária `indigo|violet|purple` de 400 a 700;
- `P0-GRADIENT`: gradiente de duas paradas entre matizes roxo, azul, ciano e rosa, ou texto com gradiente (`background-clip: text`);
- `P0-EMOJI-ICON`: emoji dentro de `h1`–`h6`, `button`, `li` ou elemento com classe contendo `icon`;
- `P0-SIDE-STRIPE`: regra ou elemento com borda lateral colorida de 2px ou mais junto com raio de borda;
- `P0-FILLER`: lorem ipsum, "feature one/two/three", "placeholder text", "sample content", "John Doe", "Jane Doe", "Acme";
- `P0-METRIC`: métrica de marketing no texto, como "10x faster", "99.9% uptime", "trusted by 50,000+ teams" e equivalentes em português;
- `P0-PLACEHOLDER-CDN`: `unsplash.com`, `placehold.co`, `placekitten.com`, `picsum.photos` ou `via.placeholder.com`.

### REQ-029: Regras P1 e P2 de aviso
WHEN o lint encontra apenas P1 ou P2, THE SYSTEM SHALL reportar os achados e terminar com exit code 0. P1: cor literal (hex, `rgb`, `hsl`, `oklch`) fora de `:root` e do arquivo de tokens; `font-family` literal fora dos tokens; mais de 3 famílias de fonte; `transition: all` ou `transition-all`; `outline: none` ou `outline: 0` sem `:focus-visible` no mesmo arquivo; animação, transição ou `@keyframes` sem `@media (prefers-reduced-motion: reduce)` no mesmo arquivo. P2: a variável de accent usada mais de 6 vezes num arquivo; o mesmo hover de escala aplicado em mais de 3 elementos.

### REQ-030: Cor de marca declarada
WHERE uma cor está declarada em `DESIGN.md` ou no arquivo de tokens, THE SYSTEM SHALL não reportar `P0-INDIGO` nem `P0-GRADIENT` para essa cor.

### REQ-031: Formato do achado
THE SYSTEM SHALL reportar cada achado com arquivo, linha, ID da regra, severidade, mensagem e sugestão de correção, em texto legível ou em JSON com `--format json`.

### REQ-032: Hook informativo
WHEN um arquivo com extensão analisada pelo lint, dentro da raiz do projeto, é editado pelo agente, THE SYSTEM SHALL rodar o lint só nesse arquivo, sem bloquear a edição (exit 0) e dentro do timeout do hook. No Claude Code (PostToolUse de Edit, Write ou MultiEdit), os achados aparecem para o agente. No Cursor (`afterFileEdit`, que não tem canal de volta para o agente), o resumo vai para a timeline do projeto com opt-in, e as skills `ui-ux` e `design-review` e o agente `frontend-implementer` rodam o lint por conta própria antes de entregar.

### REQ-033: Testes e CI
THE SYSTEM SHALL ter testes em `agent-system/tests` com fixtures que reproduzem cada regra P0, P1 e P2, uma fixture limpa sem achados e uma fixture com cor de marca roxa declarada nos tokens. Os testes rodam pela suíte que o CI já executa.

### REQ-034: Supressão pontual
WHERE uma linha ou a linha anterior a ela contém o comentário `design-lint-disable <REGRA> -- <motivo>`, THE SYSTEM SHALL não reportar essa regra naquela linha. IF o comentário não tiver motivo, THEN THE SYSTEM SHALL ignorar a supressão e reportar um P1 `P1-SUPPRESSION-NO-REASON`.

## Acceptance Criteria

### AC-001: Limite e recomendações da entrevista
- Requirements: REQ-001
Given um projeto sem `design/brief.md`
When o usuário invoca `design-discovery`
Then a entrevista tem no máximo 5 perguntas, cada uma com resposta recomendada e no máximo 7 opções, sem termos como "editorial", "bento" ou "glassmorphism" sem explicação.

### AC-002: Pergunta já respondida é pulada
- Requirements: REQ-002
Given um README que diz que o produto é para clínicas veterinárias
When `design-discovery` roda
Then não há pergunta sobre o público, e o brief registra o público como `inferido`.

### AC-003: Estrutura do brief
- Requirements: REQ-003
Given uma entrevista concluída com uma URL de referência
When o brief é gravado
Then `design/brief.md` tem front matter `status`, as seções exigidas, uma tabela Keep / Change / Do not copy para a referência e a marcação de origem em cada informação.

### AC-004: Sem referências
- Requirements: REQ-004
Given um usuário que responde que não tem referências
When a entrevista termina
Then o brief registra que a direção parte só do brief, e a etapa seguinte continua.

### AC-005: Direções diferentes de verdade
- Requirements: REQ-005, REQ-007
Given um brief aprovado
When `design-directions` roda
Then o comentário de cada direção mostra que cada par difere em pelo menos dois dos quatro eixos, e nenhum par difere só em cor.

### AC-006: Prévias autocontidas e com conteúdo real
- Requirements: REQ-006
Given as direções geradas
When os quatro HTML são abertos sem rede
Then o layout e as cores renderizam (fontes caem no fallback), não há `<script src>` nem `<img src>` externos, e o lint não reporta `P0-FILLER` nem `P0-PLACEHOLDER-CDN`.

### AC-007: Parada para escolha
- Requirements: REQ-008
Given as 3 direções geradas
When a etapa termina
Then `DESIGN.md` não foi criado e o agente pediu ao usuário que escolha uma direção.

### AC-008: Ajuste só na escolhida
- Requirements: REQ-009
Given o usuário escolheu a direção B e pediu "densidade 8"
When o ajuste é aplicado
Then só `design/directions/b.html` muda e seu comentário mostra densidade 8.

### AC-009: Pedido de mistura
- Requirements: REQ-010
Given o usuário pede "a tipografia da A com as cores da C"
When o agente responde
Then explica o risco de incoerência e entrega uma única direção revisada, sem colar trechos das duas.

### AC-010: Seções do DESIGN.md
- Requirements: REQ-011, REQ-013
Given uma direção aprovada
When `design-system` roda
Then `DESIGN.md` tem front matter `status` e as 9 seções na ordem exigida, a seção 1 cita a escolha distintiva e a seção 9 lista os P0 do lint.

### AC-011: Tokens coerentes com o contrato
- Requirements: REQ-012
Given `DESIGN.md` e `design/tokens.css` gerados
When os valores são comparados
Then todo valor de cor, fonte e espaçamento citado em `DESIGN.md` existe em `tokens.css` com o mesmo valor, o espaçamento é múltiplo de 4px, há no máximo 3 famílias de fonte e cada par de fundo com `-ink` atinge 4.5:1.

### AC-012: Não sobrescreve sem confirmação
- Requirements: REQ-014
Given um `DESIGN.md` existente
When `design-system` roda
Then o agente mostra as mudanças por seção e o arquivo só muda depois da confirmação do usuário.

### AC-013: Exceção por página
- Requirements: REQ-015, REQ-019
Given `design/pages/dashboard.md` que troca a densidade para compacta
When `ui-ux` constrói o dashboard
Then a tela usa a densidade compacta, e as outras páginas continuam com a densidade do `DESIGN.md`.

### AC-014: Revisão refaz eixo fraco
- Requirements: REQ-016, REQ-017
Given uma prévia com hero genérico que recebe nota 2 em especificidade
When `design-review` roda
Then há pelo menos uma revisão antes da entrega, no máximo 3 passadas, e o relato em prosa traz as notas finais e o que ficou aberto.

### AC-015: /design pula etapa aprovada
- Requirements: REQ-018
Given `design/brief.md` com `status: approved` e nenhuma direção gerada
When o usuário invoca `design`
Then a entrevista não roda e o fluxo começa em `design-directions`.

### AC-016: ui-ux usa só tokens
- Requirements: REQ-019
Given um projeto com `DESIGN.md` e `tokens.css`
When `ui-ux` cria uma tela nova
Then o lint não reporta cor literal nem `font-family` literal fora dos tokens nos arquivos criados.

### AC-017: ui-ux sem contrato recomenda /design
- Requirements: REQ-020
Given um projeto novo sem `DESIGN.md`
When o usuário pede uma landing page por `ui-ux`
Then o agente recomenda rodar `design` antes e, numa mudança pequena em um projeto com sistema visual próprio, segue sem essa recomendação.

### AC-018: Referências e créditos presentes
- Requirements: REQ-021, REQ-022
Given as skills de design instaladas
When os arquivos são listados
Then existem `anti-slop.md`, `design-md-format.md`, `microcopy.md`, de 3 a 4 exemplos de DESIGN.md e um arquivo de créditos com fonte, licença e link de cada material adaptado.

### AC-019: designer não implementa
- Requirements: REQ-023
Given o agente `designer` recebe um pedido de landing page
When ele termina
Then gerou só artefatos em `design/` e `DESIGN.md`, sem código de produção, e parou na escolha de direção.

### AC-020: frontend-implementer segue o contrato
- Requirements: REQ-024
Given uma tarefa de tela com `DESIGN.md` aprovado
When o `frontend-implementer` entrega
Then a tela cobre os quatro estados e o relato inclui a saída do lint nos arquivos alterados, sem P0.

### AC-021: design-reviewer bloqueia P0
- Requirements: REQ-025
Given uma tela com emoji em um `h3`
When o `design-reviewer` revisa
Then o veredito não é aprovado, o achado cita arquivo e linha, e o reviewer não altera o arquivo.

### AC-022: Agentes registrados e roteados
- Requirements: REQ-026
Given o plugin instalado
When `agents.json` é lido e o orchestrator recebe um pedido de tela nova sem `DESIGN.md`
Then os três agentes estão registrados como ativos e o orchestrator encaminha ao `designer`.

### AC-023: Varredura e exclusões
- Requirements: REQ-027
Given um diretório com `src/App.tsx` e `node_modules/x/index.html`, ambos com `#6366f1`
When `lint_design.py` roda no diretório
Then só `src/App.tsx` é reportado.

### AC-024: Cada P0 reprova
- Requirements: REQ-028, REQ-031
Given uma fixture para cada regra P0
When o lint roda em cada uma
Then o exit code é 1 e o achado traz arquivo, linha, ID da regra, severidade, mensagem e sugestão.

### AC-025: P1 e P2 só avisam
- Requirements: REQ-029
Given uma fixture com `transition: all` e cor literal fora de `:root`, sem nenhum P0
When o lint roda
Then os dois achados aparecem e o exit code é 0.

### AC-026: Marca roxa declarada passa
- Requirements: REQ-030
Given `design/tokens.css` que declara `--color-accent: #7c3aed` e um componente que usa `#7c3aed`
When o lint roda com `--tokens design/tokens.css`
Then não há `P0-INDIGO` para esse valor.

### AC-027: Saída JSON
- Requirements: REQ-031
Given uma fixture com achados
When o lint roda com `--format json`
Then a saída é JSON válido com uma lista de achados contendo `file`, `line`, `rule`, `severity`, `message` e `suggestion`.

### AC-028: Hook não bloqueia
- Requirements: REQ-032
Given o agente edita `src/Hero.tsx` e introduz um P0
When o hook roda
Then no Claude Code o achado aparece para o agente; no Cursor a resposta é vazia e a timeline de um projeto com opt-in ganha um evento `DESIGN_LINT` sem trecho do arquivo; o hook termina com exit 0 dentro do timeout, inclusive com um CSS minificado de 300 KB; e edições em arquivos `.py` ou `.md`, ou fora da raiz do projeto, não disparam o lint.

### AC-029: Testes no CI
- Requirements: REQ-033
Given as fixtures de lint
When `python -I agent-system/scripts/test_system.py` roda no CI (Ubuntu e Windows)
Then os testes do lint passam, incluindo a fixture limpa sem achados e a fixture de marca roxa.

### AC-030: Supressão com e sem motivo
- Requirements: REQ-034
Given uma linha com "99.9% uptime" precedida de `design-lint-disable P0-METRIC -- SLA contratual` e outra linha igual precedida de `design-lint-disable P0-METRIC` sem motivo
When o lint roda
Then a primeira linha não gera achado, a segunda gera `P0-METRIC` e `P1-SUPPRESSION-NO-REASON`, e o exit code é 1.

## Assumptions

- O usuário abre os HTML de `design/directions/` no navegador do Cursor, do Claude Code ou no navegador do sistema.
- Os projetos-alvo são web (HTML/CSS ou frameworks que geram HTML). Apps nativos (SwiftUI, Flutter, Compose) ficam fora do lint, mas podem usar as skills.
- O lint é heurístico, baseado em regex e varredura de texto, sem parser completo de CSS ou JSX. Falso positivo e falso negativo são aceitos dentro do que os fixtures cobrem.
- O hook reaproveita `agent-system/scripts/hook.py` e o timeout de 20 s já configurado.

## Constraints

- Só stdlib Python, compatível com 3.10 a 3.13, Windows e Linux, como o resto de `agent-system/scripts`.
- Skills seguem o formato de `skills/<nome>/SKILL.md` com `references/` e funcionam em Cursor e Claude Code.
- Nenhum DESIGN.md de exemplo reproduz identidade de marca real (logo, nome, paleta proprietária).
- O hook nunca bloqueia nem altera arquivo.
- As skills existentes `ui-ux-experiment` e `apple-design` continuam válidas; `apple-design` passa a ser citada pela seção 7 do DESIGN.md quando o projeto tiver gesto ou mola.

Fora de escopo: geração de imagem, integração com Figma, biblioteca de componentes, migração automática de projeto existente para DESIGN.md, publicação como Artifact, teste de regressão visual por screenshot.

## Open Questions

- [x] Supressão pontual no lint: entra neste spec como REQ-034.
- [x] Licença do Hallmark: MIT (Nutlope/hallmark, distribuído em `plugins/community/hallmark` do open-design). Pode ser adaptado com atribuição.

## Decisions

- Supressão por comentário `design-lint-disable <REGRA> -- motivo`, exigindo motivo, para que métrica real ou emoji intencional não bloqueie o CI.
- Fontes adaptadas incluem Hallmark (MIT) para a autocrítica de seis eixos e para regras do slop-test.

- Escopo único com skills, agentes e lint (escolha do usuário), complexidade XL.
- Direções mostradas como HTML versionado no projeto, não como Artifact.
- Lint bloqueia P0 e só avisa P1/P2; o hook apenas informa.
- Skills separadas (`design-discovery`, `design-directions`, `design-system`, `design-review`) mais a skill `design` que encadeia as quatro.
- O usuário escolhe a direção inteira e ajusta por dials; o agente não monta direção a partir de peças de direções diferentes.
- Change request (2026-11-12, aprovado pelo usuário, a partir do FIND-003 da revisão independente): REQ-032 e AC-028 passam a dizer o que cada host faz. O `afterFileEdit` do Cursor não devolve contexto ao agente, então no Cursor o achado vai para a timeline e as skills e o `frontend-implementer` rodam o lint; antes, o spec prometia o mesmo comportamento nos dois hosts.
