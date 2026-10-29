---
name: new-project
description: Scaffolds a spec-driven greenfield project with PRD, architecture, ADR, specs, tasks, and progress before implementation. Use when starting a new project, new repository, new product, or when the user asks to create a project from scratch (projeto novo, greenfield, do zero).
---

# Novo projeto

Projeto greenfield. Não implemente comportamento antes de existir problema, requisitos e critérios de aceite.

## Antes de criar arquivos

1. Confirme o nome do projeto. Sugira um padrão a partir do que foi descrito. Pergunte preferências de layout, git ou boilerplate só se o usuário quiser decidir; caso contrário, use defaults sensatos.
2. Crie o diretório (prefira `~/Projects/` ou `~/Developer/` se existirem; senão o home), inicialize git e mova o agente para essa raiz antes de qualquer scaffolding.
3. Não grave a árvore `docs/` no home nem no perfil do usuário. Não crie `AGENTS.md`. Ele só entra se o usuário pedir o processo versionado dentro do repositório.

## Árvore

Crie só o que tiver conteúdo:

```
docs/
├── product/PRD.md
├── architecture/ARCHITECTURE.md
├── architecture/ADR/
├── specs/
├── tests/VERIFICATION.md
├── tasks/
├── changes/
└── progress/CURRENT.md
```

Se o usuário já indicou outra pasta canônica, use essa.

## PRD

`docs/product/PRD.md` deve ter: problema, resultado desejado, usuários, requisitos funcionais, não funcionais quando couberem, restrições, premissas, fora de escopo, critérios de aceite, comportamento existente afetado (nenhum, se for greenfield).

## Arquitetura

`docs/architecture/ARCHITECTURE.md`: visão, limites dos módulos, dados e integrações conhecidas.

ADR só para decisão já tomada. Arquivo `docs/architecture/ADR/0001-titulo.md` com: contexto, problema, decisão, alternativas, racional, consequências, riscos. Não reescreva ADR aceito; crie outro se a decisão mudar.

## Spec, verificação e tarefas

- `docs/specs/`: o que o sistema deve fazer, rastreável aos requisitos do PRD.
- `docs/tests/VERIFICATION.md`: níveis (unidade, integração, contrato, e2e, aceite, property-based, eval) e o que cada critério de aceite exige.
- `docs/tasks/`: passos pequenos. Cada tarefa cita o requisito, os testes e as dependências. Exemplo: `TASK-X` depende de `TASK-Z`.
- `docs/progress/CURRENT.md`: fase atual, próximo passo, bloqueios. O próximo passo não é "continuar codando" por padrão.

## Verificar o design

Antes de implementar, confira spec e arquitetura contra o PRD e os critérios de aceite. Corrija o artefato, não o código, se o design não fecha.

## Implementar

Só depois do plano. Cada tarefa segue a skill `implementation`. Cerimônia proporcional: se o usuário pediu um esboço mínimo, entregue PRD curto, uma spec e a primeira tarefa, e pare para confirmar antes de expandir.
