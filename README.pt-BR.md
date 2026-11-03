<div align="right">
  <img src="https://img.shields.io/badge/version-0.4.0-green?style=flat-square" alt="Versão 0.4.0" />
  <a href="README.md">
    <img src="https://img.shields.io/badge/README-EN-blue?style=flat-square" alt="English 🇺🇸" />
  </a>
</div>

# Agent Workbench

**Um harness pragmático de engenharia com IA para o Cursor e o Claude Code.**

O Agent Workbench transforma agentes de código com IA em um fluxo de engenharia de software mais estruturado, rastreável e verificável.

Em vez de otimizar a velocidade de geração de código, ele foca no que realmente importa: entender os requisitos, tomar decisões deliberadas, implementar a solução certa, validar o comportamento e produzir evidências de que o software funciona.

## Por que o Agent Workbench?

Agentes de código com IA geram código rápido, mas velocidade sozinha não garante software bom.

Problemas comuns:
- Implementar requisitos ambíguos.
- Tomar decisões de arquitetura sem documentar os trade-offs.
- Escrever testes que não verificam o comportamento de verdade.
- Repetir revisões e refinamentos desnecessários.
- Perder o contexto do projeto entre sessões.
- Tratar código gerado com sucesso como prova de que o trabalho está pronto.

O Agent Workbench ataca esses problemas com um fluxo de engenharia leve, construído em torno de rastreabilidade, verificação e decisões conscientes de risco.

## Filosofia de engenharia

O princípio que guia o projeto é a **Minimum Effective Engineering (MEE)**, a engenharia mínima eficaz:

Usar o mínimo de processo, complexidade, agentes e tokens necessário para entregar software com o nível adequado de qualidade e segurança.

Isso significa:
- O processo acompanha a complexidade e o risco.
- O risco de segurança é avaliado separadamente da complexidade de implementação.
- Requisitos e critérios de aceite ficam claros antes da implementação.
- Testes precisam produzir evidência significativa.
- Revisões focam em problemas relevantes, não em refinamento sem fim.
- O trabalho para quando os critérios de aceite são atendidos e os riscos relevantes estão controlados.

O objetivo não é mais processo. É menos retrabalho e resultados mais confiáveis.

## Como funciona

```text
     Intenção do usuário
            |
            v
  Requisitos e especificação
            |
            v
  Decisões de arquitetura
            |
            v
  Planejamento de tarefas
            |
            v
       Implementação
            |
            v
     Testes e evidências
            |
            v
 Revisão de código e segurança
            |
            v
    Gate de verificação
            |
            v
     Estado do projeto
```

O fluxo se adapta à complexidade e ao risco de segurança da tarefa. Mudanças pequenas não exigem o processo completo.

Em tarefas médias ou maiores, validadores determinísticos verificam especificações, tarefas, resultados de teste e evidências de conclusão. As revisões dos agentes fazem a avaliação semântica complementar.

## O que está incluído?

| Componente | Função |
|---|---|
| Rules | Princípios de engenharia persistentes, limites de segurança e economia de tokens |
| Skills | Fluxos reutilizáveis para features, planejamento, implementação, depuração, revisões e mais |
| Agents | Papéis especializados para planejar, implementar, testar, revisar e depurar |
| Hooks | Contexto da sessão, estado do projeto e timeline de desenvolvimento |
| Scripts | Validação determinística, execução de testes, coleta de evidências e avaliação |
| References | Guias de código seguro sob demanda para as stacks suportadas |

### Verificação e evidências

O harness tem quatro ferramentas principais de validação:

- `validate_spec.py`: valida a estrutura e a rastreabilidade da especificação.
- `validate_tasks.py`: valida tarefas, dependências e definições de verificação.
- `check_proofs.py`: executa os testes e grava o exit code real, a saída e o fingerprint do workspace.
- `validate_verification.py`: avalia se as evidências, revisões e condições das tarefas exigidas foram atendidas.

As provas ficam presas ao estado do workspace, o que ajuda a detectar quando o código muda depois que os testes rodaram.

### Segurança

Segurança é tratada como uma dimensão independente do risco de engenharia.

O projeto inclui:
- Regras de engenharia segura.
- Referências de código seguro por stack.
- Uma skill e um agente dedicados à revisão de segurança.
- Redação de segredos nos logs e saídas relevantes.
- Guardrails para execução de comandos.

**Importante:** os guardrails de comandos são proteções de melhor esforço, não uma sandbox nem uma fronteira de segurança contra código malicioso. Arquivos de teste executam o que contêm e precisam ser revisados antes da execução.

## Início rápido

### Requisitos

- Cursor ou Claude Code
- Python 3, disponível como `python` no PATH (os hooks chamam `python`)
- Git

### Instalação

#### Cursor

Windows (PowerShell):

```powershell
git clone https://github.com/brunoleocam/agent-workbench "$env:USERPROFILE\.cursor\plugins\local\agent-workbench"
```

Linux:

```bash
git clone https://github.com/brunoleocam/agent-workbench ~/.cursor/plugins/local/agent-workbench
```

Recarregue a janela do Cursor com `Developer: Reload Window`.

Depois abra **Customize** e confira se as rules, skills e subagents do plugin estão disponíveis.

#### Claude Code

O repositório também é um marketplace do Claude Code. No terminal:

```bash
claude plugin marketplace add brunoleocam/agent-workbench
claude plugin install agent-workbench@agent-workbench
```

Dentro de uma sessão do Claude Code, os mesmos passos são:

```text
/plugin marketplace add brunoleocam/agent-workbench
/plugin install agent-workbench@agent-workbench
```

Abra uma sessão nova (ou rode `/reload-plugins`). Para conferir o que foi carregado:

```bash
claude plugin details agent-workbench
```

No Claude Code, todo comando tem o prefixo do plugin: `/agent-workbench:feature` em vez de `/feature`, e os subagents aparecem como `agent-workbench:planner`, `agent-workbench:implementer` e assim por diante.

Para trabalhar no próprio plugin, carregue o seu clone só por uma sessão, sem instalar:

```bash
claude --plugin-dir /caminho/para/agent-workbench
```

### Inicializar um projeto

Na raiz do seu projeto, rode:

```text
/init-agent-system
```

No Claude Code, rode `/agent-workbench:init-agent-system`.

Isso cria o estado, a timeline e o roadmap do projeto sem substituir a documentação existente nem hooks não relacionados.

No Claude Code, plugins não têm rules sempre ativas. Por isso o init também grava uma versão condensada das rules `00` a `08` no `CLAUDE.md` do projeto, num bloco gerenciado entre os marcadores `<!-- agent-workbench:begin -->` e `<!-- agent-workbench:end -->`. Ele cria o `CLAUDE.md` se não existir e acrescenta o bloco ao final se o arquivo já existir. Texto fora dos marcadores nunca é alterado. Commite o `CLAUDE.md` junto com o projeto para versionar as rules com ele.

Cloud Agents não carregam plugins locais. Use `/init-agent-system` com `--for-cloud` ao preparar um projeto para esse ambiente.

### Atualização

#### Cursor

Confira a versão instalada em `.cursor-plugin/plugin.json` (campo `version`) e compare com o selo no topo desta página no GitHub.

1. Baixe a versão nova na pasta do plugin.

   Windows (PowerShell):

   ```powershell
   git -C "$env:USERPROFILE\.cursor\plugins\local\agent-workbench" pull --ff-only
   ```

   Linux:

   ```bash
   git -C ~/.cursor/plugins/local/agent-workbench pull --ff-only
   ```

   Se o pull recusar por causa de alterações locais, rode `git status` na pasta do plugin e guarde (stash) ou descarte essas alterações antes de tentar de novo.

2. Recarregue a janela do Cursor com `Developer: Reload Window`. Rules, skills, subagents e hooks vêm do plugin, então já ficam atualizados.

3. Em cada projeto inicializado, rode `/init-agent-system` de novo. Ele atualiza os scripts gerenciados em `.cursor/agent-system/scripts/` e adiciona chaves novas ao estado, mantendo o estado, a timeline, o roadmap, a documentação e os hooks existentes.

Em projetos preparados com `--for-cloud`, as cópias de rules e subagents nunca são sobrescritas. Para atualizá-las, apague as cópias que vieram do plugin (rules `00` a `08` e os subagents) e rode `/init-agent-system` com `--for-cloud` de novo.

#### Claude Code

1. Atualize o marketplace e o plugin:

   ```bash
   claude plugin marketplace update agent-workbench
   claude plugin update agent-workbench@agent-workbench
   ```

2. Reinicie o Claude Code. A atualização vale para as sessões novas.

3. Em cada projeto inicializado, rode `/agent-workbench:init-agent-system` de novo. Ele atualiza os scripts gerenciados e substitui só o conteúdo do bloco gerenciado no `CLAUDE.md`: edições dentro do bloco se perdem, edições fora dele são mantidas.

#### Diferenças no Claude Code

- Rules: só as rules `00` a `08` chegam ao Claude Code, pelo `CLAUDE.md`. `economia-de-tokens`, `mcp-triagem-obrigatoria` e `uso-ferramentas-mcp` são exclusivas do Cursor.
- Hooks: o Claude Code roda `hooks/claude-hooks.json`, que alimenta a mesma timeline dos hooks do Cursor.
- Estado: o projeto guarda o estado em `.cursor/agent-system/` e `.cursor/timeline/` nos dois editores, então um projeto inicializado num editor continua no outro.
- `--for-cloud` e `/roadmap visual` (Canvas) são exclusivos do Cursor.

Desde a 0.4.0, os subagents `implementer`, `tester` e `debugger` usam `model: inherit` nos dois editores (antes usavam um modelo exclusivo do Cursor). Para fixar um modelo no Cursor, altere o `model:` no arquivo do agente.

Comandos renomeados na 0.3.0: `investigacao-enxuta` agora é `/lean-investigation`, `resumo-de-contexto` agora é `/context-summary` e `tarefa-em-etapas` agora é `/staged-task`.

## Como usar o Agent Workbench

### Como os comandos funcionam

- Digite `/` no chat e escolha o comando (no Claude Code, os comandos começam com `/agent-workbench:`). Você pode escrever o contexto depois dele, por exemplo `/feature adicionar exportação CSV no relatório de vendas`.
- Cada comando cuida de uma fase. A próxima fase não começa sozinha, a menos que o próprio comando diga qual vem depois.
- Mudança trivial não precisa de comando. Basta pedir; o agente classifica o pedido (classe, complexidade de XS a XL e risco de segurança) e ajusta o processo a ele.
- Rules e subagents são aplicados automaticamente. Você não chama subagent direto: em tarefas médias ou maiores, o agente principal delega a `planner`, `implementer`, `tester`, `reviewer`, `security-reviewer` e `debugger`.
- Em trabalhos maiores, abra um chat novo para cada fase. Em projetos inicializados, o estado atual fica em `docs/progress/CURRENT.md` e `docs/progress/ROADMAP.md`, então o chat novo continua de onde o anterior parou.

### Fluxos recomendados

Feature nova, da ideia ao merge:

```text
# Amadurece a ideia com perguntas e alternativas até você aprovar um design
/brainstorm
# Transforma o design aprovado em plano com caminhos reais e comandos de verificação
/implementation-plan
# (Opcional) Cria uma cópia isolada do repositório para trabalhar sem mexer na principal
/git-worktree
# Implementa cada passo com teste primeiro: vermelho, código mínimo, refactor
/tdd
# Confere se os testes provam comportamento e falham pelo motivo certo
/test-hygiene
# Revisão independente contra requisitos, spec, critérios de aceite e testes
/code-review
# Alinha spec, ADR e progresso ao que mudou
/update-docs
# Com testes verdes, uma única aprovação sua para commit, push, PR e merge
/commit-push
```

Feature em sistema existente, num fluxo guiado único:

```text
# Impacto, spec, tarefas, implementação, testes e review em sequência
/feature
```

Repositório novo:

```text
# Cria PRD, arquitetura, spec, tarefas e progresso do projeto
/new-project
```

Bug:

```text
# Acha a causa lendo o mínimo de código e log, uma hipótese por vez
/lean-investigation
# (Opcional) Registra sintoma, mecanismo, evidência e o teste que faltou
/root-cause
# Correção mínima com teste de regressão, depois da causa confirmada
/bug-fix
```

Bug difícil ou intermitente:

```text
# Reproduz a falha e prova a causa com evidência, sem chutar patch
/debug
# Registra sintoma, mecanismo, evidência e o teste que faltou
/root-cause
# Escreve o teste que falha pelo bug e só então corrige
/tdd
```

Interface:

```text
# Gera 2 ou 3 opções de interface para você comparar e escolher
/ui-ux-experiment
# Constrói a opção escolhida com estados de vazio, erro, loading e sucesso
/ui-ux
# (Opcional) Adiciona motion interativo estilo Apple: drag, swipe, sheets e springs
/apple-design
```

Pedido grande sem spec formal:

```text
# Divide o pedido em 3 a 7 etapas verificáveis e executa uma por vez
/staged-task
```

Conversa longa, antes de trocar de chat:

```text
# Gera um resumo de até 10 linhas para colar no chat novo
/context-summary
```

### Referência dos comandos

Instalação e estado do projeto:

- `/init-agent-system` — instala estado, timeline e roadmap no projeto atual sem substituir configuração existente nem criar documentos vazios. Rode na raiz do projeto. Use `--for-cloud` para copiar também rules e subagents para Cloud Agents.
- `/agent-status` — mostra agentes, skills, rules, hooks e o estado atual do workflow.
- `/roadmap` — mostra a fase e a tarefa atuais, o que falta e o que está bloqueado. Também cria ou atualiza o roadmap, e `/roadmap visual` gera a visão em Canvas. Exige `/init-agent-system`.
- `/timeline` — mostra o histórico append-only de eventos de um projeto inicializado.
- `/lessons` — propõe, lista, confirma ou rejeita lições do projeto. Só você confirma uma lição, e só as confirmadas entram no contexto do agente.
- `/help` — mostra o guia de comandos dentro do Cursor.

Planejamento:

- `/brainstorm` — para ideia ainda crua. Faz uma pergunta por vez, propõe alternativas e termina com um design aprovado por você. Não escreve código nem plano.
- `/new-project` — repositório novo: PRD, arquitetura, especificação, tarefas e progresso. Não cria `AGENTS.md`.
- `/feature-development` — feature em sistema existente: análise de impacto, especificação, tarefas, implementação, testes e review.
- `/feature` — atalho para `/feature-development`.
- `/investigation` — entende como uma parte do sistema funciona. Não implementa.
- `/implementation-plan` — para design já aprovado. Gera um plano com caminhos reais, exemplos de código e comandos de verificação, escrito para quem não conhece o repositório.
- `/change-request` — escopo novo descoberto no meio da tarefa. Atualiza a especificação ou cria uma dependência antes de continuar.

Implementação:

- `/implementation` — executa um passo do plano, ligado a um requisito.
- `/tdd` — escreve um teste que falha pelo motivo certo, depois o código mínimo, depois refatora. Sem código de produção antes do teste vermelho.
- `/staged-task` — divide um pedido grande em 3 a 7 etapas verificáveis e executa uma por vez. Não cria PRD, ADR nem plano detalhado.
- `/refactoring` — muda a estrutura mantendo o comportamento, coberto por testes.
- `/git-worktree` — cria uma cópia isolada do repositório para trabalhar. Pede sua concordância e nunca faz push.

Bugs:

- `/lean-investigation` — acha a causa de um bug lendo o mínimo de código e log, uma hipótese por vez. Não corrige.
- `/debug` — reproduz a falha e acha a causa com evidência. Não chuta patch.
- `/root-cause` — registra sintoma, mecanismo, evidência e o teste que faltou. Só depois da causa confirmada.
- `/bug-fix` — correção mínima depois da causa confirmada, com teste de regressão.

Interface:

- `/ui-ux-experiment` — constrói 2 ou 3 opções de interface para comparar. Não implementa todas.
- `/ui-ux` — constrói a interface escolhida com os estados de vazio, erro, loading e sucesso, e verifica o fluxo.
- `/apple-design` — motion interativo estilo Apple na web: drag, swipe, sheets, springs, momentum, interrupção e reduced motion. Também revisa interações existentes. Não cuida de layout nem dos estados da tela.

Qualidade e segurança:

- `/test-hygiene` — confere se os testes provam comportamento, são determinísticos e falham pelo motivo certo.
- `/code-review` — confronta requisitos, especificação, critérios de aceite, testes e código, com Verification Audit (o teste falharia se o requisito estivesse errado?). Cada achado tem severidade e evidência.
- `/security-review` — auditoria de segurança de uma feature ou do repositório inteiro pelo subagent `security-reviewer`, com as referências da stack. Gera relatório com achados SEC e não corrige nada sem sua autorização. Não é o subagent built-in `security-review` do Cursor.
- `/security-best-practices` — orientação de código seguro para a stack detectada, carregando só a referência dela. Diferencia vulnerabilidade de hardening.

Documentação e entrega:

- `/update-docs` — alinha a especificação, um ADR novo ou o progresso ao que mudou. Não reescreve ADR aceito.
- `/commit-push` — branch antes de editar; com testes verdes, uma única aprovação sua para commit, push, PR e merge. Sem aprovação, nada sai da sua máquina.
- `/context-summary` — resumo de até 10 linhas (objetivo, decisões, arquivos, próximos passos) para colar num chat novo. Não relê arquivos nem grava nada.

Extensão do harness:

- `/create-skill` — cria uma skill nova no seu perfil e a inclui no `/help`. Não cria a skill dentro do repositório aberto, a menos que você peça.
- `/create-agent` — cria um subagent especializado e registra quando o orchestrator deve delegar a ele.

## Aprovação humana e automação

O Agent Workbench automatiza o trabalho repetitivo de engenharia, mas não delega todas as decisões a um agente.

A aprovação humana continua importante para:
- Decisões de especificação e de arquitetura.
- Mudanças no comportamento de negócio.
- Mudanças sensíveis de segurança e permissões.
- Infraestrutura nova e operações destrutivas.
- Aceitação de riscos residuais.
- Commit e push, quando autorizados explicitamente.

Agentes podem propor decisões e mudanças, mas as decisões importantes continuam sob controle humano.

## Documentação

| Documento | Descrição |
|---|---|
| [Agent System](agent-system/README.md) | Arquitetura, fluxos, agentes e validação |
| [Formato dos artefatos](agent-system/docs/artifacts.md) | Formatos de especificação, tarefas e evidências |
| [Referência da CLI](agent-system/docs/cli.md) | Comandos e opções dos scripts |
| [Contratos dos agentes](agent-system/docs/contracts.md) | Responsabilidades e passagens entre agentes |
| [Decisões de arquitetura](docs/architecture/ADR/) | Decisões de arquitetura e trade-offs |
| [Documentação de segurança](docs/security/) | Revisões de segurança e limitações aceitas |
| [Progresso do projeto](docs/progress/) | Estado atual da implementação e roadmap |

## Testes e avaliações

Rode a suíte de testes automatizados:

```bash
python agent-system/scripts/test_system.py
```

Rode as avaliações determinísticas:

```bash
python agent-system/scripts/run_evals.py
```

As avaliações verificam o comportamento do harness com fixtures de projeto controladas. Elas não avaliam automaticamente a qualidade das decisões do modelo de IA nem do código gerado.

A implementação atual foi testada no Windows e no Linux (WSL2). O macOS ainda não foi testado. Não há CI configurado no momento.

## Licença

MIT.

Os materiais de referência de segurança são documentação original do projeto, baseada em fontes oficiais, como a OWASP e a documentação dos frameworks. Veja as fontes em cada referência.
