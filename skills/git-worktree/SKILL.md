---
name: git-worktree
description: Creates or reuses a git worktree so implementation happens off the current checkout and can be pushed to GitHub later. Use when the user asks for a worktree, an isolated branch, or a second working copy (worktree, worktree do GitHub, branch isolada).
---

# Git worktree

Isolates the work in a copy linked to the same repository. Pushing to GitHub remains `commit-push`, when the user asks.

Do not create a worktree without the user agreeing. If they already asked for a worktree, that is the agreement.

## Before creating

```bash
git rev-parse --show-toplevel
git worktree list
git rev-parse --git-dir
git rev-parse --git-common-dir
```

If `git-dir` and `git-common-dir` differ and it is not a submodule (`git rev-parse --show-superproject-working-tree` is empty), you are already in a worktree. Do not create another. Say the path and the branch.

## Create

1. A new branch, in the repo's pattern (`feat/<slug>` if there is no other).
2. A sibling directory of the repository, not inside the working tree: `../<repo>-<slug>`.
3. `git worktree add -b <branch> <path>`
4. Move the agent to that root before editing files.
5. Do not copy `.env`. Do not use interactive git commands. Do not delete the worktree unless the user asks (`git worktree remove <path>`).

When done, say the path, the branch, and that commit or push follow `commit-push`.
