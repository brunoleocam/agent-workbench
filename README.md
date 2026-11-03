# Agent Workbench

Plugin do Cursor com um harness de desenvolvimento spec-driven: regras, skills, subagents, hooks e um roadmap por projeto, ajustados para gastar poucos tokens.

O objetivo não é a IA programar mais rápido. É trabalhar como uma equipe de engenharia: entender, especificar, planejar, implementar, testar, revisar, avaliar risco e mostrar evidência de que o software faz o que foi pedido. Os gates de M ou maior são scripts determinísticos, não instruções em Markdown.

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
| `rules/` | Engenharia rastreável (`00`–`07`), segurança (`08`), economia de tokens, triagem de MCP |
| `skills/` | Comandos `/nome`, incluindo `/security-review`, `/security-best-practices`, e `/lessons`. Rode `/help` para o guia completo |
| `agents/` | `orchestrator`, `planner`, `implementer`, `tester`, `reviewer`, `debugger`, `security-reviewer` |
| `hooks/` | Timeline e estado do projeto; contexto curto no início do chat |
| `agent-system/scripts/` | Python (stdlib): timeline, validadores (`validate_spec`, `validate_tasks`, `check_proofs`, `validate_verification`), `lessons`, `run_evals` |
| `agent-system/docs/` | Formato dos artefatos, contratos de CLI e de handoff |
| `agent-system/evals/` | Fixtures determinísticas dos gates |

Fluxo típico: `/brainstorm` → spec → `/implementation-plan` → `/tdd` ou `/implementation` → `/code-review` → `/commit-push`. Defeito: `/investigacao-enxuta` ou `/debug` → `/bug-fix`. Em M ou maior, cada fase tem um gate: spec e tarefas validadas, provas com exit code real, review com Verification Audit e `validate_verification.py` antes de declarar pronto. Detalhes em [`agent-system/README.md`](agent-system/README.md).

## Por projeto

`/init-agent-system` na raiz do projeto liga a timeline, o estado (`.cursor/agent-system/state.json`) e o roadmap (`docs/progress/ROADMAP.md`). Sem isso, os hooks não gravam nada no projeto.

Cloud Agents não carregam plugin local. Para eles, use `/init-agent-system` com `--for-cloud`, que copia regras e subagents para o projeto.

## User Rules

A regra [`rules/economia-de-tokens.mdc`](rules/economia-de-tokens.mdc) já vale em toda conversa com o plugin instalado. Não cole o mesmo texto nas User Rules, ou ele carrega duas vezes.

## Testes

```powershell
python agent-system/scripts/test_system.py
python agent-system/scripts/run_evals.py
```

## Licença

MIT. As referências de segurança em `skills/security-best-practices/references/` são texto próprio, escrito a partir das fontes oficiais citadas em cada arquivo (OWASP e documentação dos frameworks).
