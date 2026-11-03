<div align="right">
  <a href="README.md">
    <img src="https://img.shields.io/badge/README-EN-blue?style=flat-square" alt="English 🇺🇸" />
  </a>
</div>

# Agent Workbench

**Um harness pragmático de engenharia com IA para o Cursor.**

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

- Cursor
- Python 3
- Git

### Instalação

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

### Inicializar um projeto

Na raiz do seu projeto, rode:

```text
/init-agent-system
```

Isso cria o estado, a timeline e o roadmap do projeto sem substituir a documentação existente nem hooks não relacionados.

Cloud Agents não carregam plugins locais. Use `/init-agent-system` com `--for-cloud` ao preparar um projeto para esse ambiente.

### Fluxos típicos

Desenvolvimento de feature:

```text
/brainstorm
/implementation-plan
/implementation
/code-review
```

Investigação de bug:

```text
/investigacao-enxuta
/bug-fix
```

Use `/help` dentro do Cursor para ver os comandos e fluxos disponíveis.

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
