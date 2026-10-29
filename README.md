# Agent Workbench

Plugin do Cursor com um harness de desenvolvimento spec-driven: regras, skills, subagents, hooks e um roadmap por projeto, ajustados para gastar poucos tokens.

Inspirado em [tech-leads-club/agent-skills](https://github.com/tech-leads-club/agent-skills) e [mattpocock/skills](https://github.com/mattpocock/skills).

## Instalar

Requisitos: Cursor e Python 3 no `PATH`.

```powershell
git clone https://github.com/brunoleocam/agent-workbench "$env:USERPROFILE\.cursor\plugins\local\agent-workbench"
```

```bash
git clone https://github.com/brunoleocam/agent-workbench ~/.cursor/plugins/local/agent-workbench
```

Depois, `Developer: Reload Window` e confira em **Customize** se as regras, skills e subagents aparecem. O clone precisa ficar dentro de `~/.cursor/plugins/local/`; o Cursor ignora symlink que aponta para fora dessa pasta.

Atualizar: `git pull` na pasta do plugin e recarregar a janela.

## O que vem no plugin

| Pasta | Conteúdo |
|-------|----------|
| `rules/` | Engenharia rastreável (`00`–`07`), economia de tokens, triagem de MCP |
| `skills/` | Comandos `/nome`. Rode `/help` para o guia completo |
| `agents/` | `orchestrator`, `planner`, `implementer`, `tester`, `reviewer`, `debugger` |
| `hooks/` | Timeline e estado do projeto; contexto curto no início do chat |
| `agent-system/` | Scripts Python (stdlib) e documentação do sistema |

Fluxo típico: `/brainstorm` → spec → `/implementation-plan` → `/tdd` ou `/implementation` → `/code-review` → `/commit-push`. Defeito: `/investigacao-enxuta` ou `/debug` → `/bug-fix`. Detalhes em [`agent-system/README.md`](agent-system/README.md).

## Por projeto

`/init-agent-system` na raiz do projeto liga a timeline, o estado (`.cursor/agent-system/state.json`) e o roadmap (`docs/progress/ROADMAP.md`). Sem isso, os hooks não gravam nada no projeto.

Cloud Agents não carregam plugin local. Para eles, use `/init-agent-system` com `--for-cloud`, que copia regras e subagents para o projeto.

## User Rules

A regra [`rules/economia-de-tokens.mdc`](rules/economia-de-tokens.mdc) já vale em toda conversa com o plugin instalado. Não cole o mesmo texto nas User Rules, ou ele carrega duas vezes.

## Testes

```powershell
python agent-system/scripts/test_system.py
```

## Licença

MIT
