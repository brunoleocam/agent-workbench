---
name: git-worktree
description: Creates or reuses a git worktree so implementation happens off the current checkout and can be pushed to GitHub later. Use when the user asks for a worktree, an isolated branch, or a second working copy (worktree, worktree do GitHub, branch isolada).
---

# Git worktree

Isola o trabalho numa cópia ligada ao mesmo repositório. O push para o GitHub continua sendo `commit-push`, quando o usuário pedir.

Não crie worktree sem o usuário concordar. Se ele já pediu worktree, isso é a concordância.

## Antes de criar

```bash
git rev-parse --show-toplevel
git worktree list
git rev-parse --git-dir
git rev-parse --git-common-dir
```

Se `git-dir` e `git-common-dir` forem diferentes e não for submodule (`git rev-parse --show-superproject-working-tree` vazio), já está num worktree. Não crie outro. Diga o caminho e a branch.

## Criar

1. Branch nova, no padrão do repo (`feat/<slug>` se não houver outro).
2. Diretório irmão do repositório, não dentro da working tree: `../<repo>-<slug>`.
3. `git worktree add -b <branch> <path>`
4. Mova o agente para essa raiz antes de editar arquivos.
5. Não copie `.env`. Não use comando git interativo. Não apague worktree a menos que o usuário peça (`git worktree remove <path>`).

Ao terminar, diga caminho, branch e que commit ou push seguem `commit-push`.
