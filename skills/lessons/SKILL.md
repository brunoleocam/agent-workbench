---
name: lessons
description: Proposes, lists, confirms, or rejects project lessons learned with lessons.py, loading only confirmed lessons relevant to the current activity. Use when a significant step reveals a reusable lesson, when the user says "registrar lição", "lições aprendidas", "confirmar lição", or before work in a category that has confirmed lessons.
---

# Lições aprendidas

Projeto inicializado (`.cursor/agent-system/state.json`). A fonte de verdade é `.cursor/agent-system/lessons.json`; `LESSONS.md` é gerado. Comandos em `agent-system/docs/cli.md`.

## Propor

Só proponha uma lição que mudaria o comportamento num trabalho futuro e que tenha evidência (TEST, FIND, SEC, commit, caminho). Não registre toda observação da conversa. No máximo uma por passo relevante.

```powershell
python .cursor/agent-system/scripts/lessons.py add --category testing --title "Teste de expiração usa relógio injetado" --description "Testes de tempo usam clock falso; sleep real deixou TEST-004 instável." --evidence TEST-004 --agent tester
```

Sem segredo, token, senha, dado pessoal nem trecho de código privado: o script recusa o que parecer segredo, mas a responsabilidade é sua. Duplicata (mesmo título normalizado, inclusive rejeitada) é recusada.

Depois de propor, mostre a lição ao usuário e pergunte se confirma.

## Confirmar ou rejeitar

Só com decisão explícita do usuário. O agente não confirma por conta própria.

```powershell
python .cursor/agent-system/scripts/lessons.py confirm --id LESSON-003
python .cursor/agent-system/scripts/lessons.py reject --id LESSON-004 --reason "específica demais"
```

## Carregar

O início da sessão já traz até cinco títulos confirmados. Antes de trabalho numa área, carregue só a categoria dela:

```powershell
python .cursor/agent-system/scripts/lessons.py list --status confirmed --category security --verbose
```

Candidatas e rejeitadas nunca entram no contexto automaticamente.
