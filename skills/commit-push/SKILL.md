---
name: commit-push
description: Git flow for features and bug fixes - branch before editing, then one approval for commit, push, PR and merge after green tests. Use when starting or finishing a feature or bug fix in a git repo, or when the user asks to commit, push, open a PR or merge (commit, push, PR, subir para o GitHub).
---

# Branch, commit, push, PR e merge

Toda feature ou correção de bug em repositório git segue este fluxo.

Pasta sem `.git`: não rode `git init` nem crie repositório sem o usuário pedir. Avise e siga sem o fluxo.

## 1. Antes de editar código: branch

1. Em paralelo: `git status --short`, `git branch --show-current`, `git remote get-url origin`.
2. Working tree com mudança que não é desta tarefa: pergunte antes de criar a branch.
3. Branch-base, nesta ordem:
   - a que uma rule ou skill do repositório definir (ex.: `develop` para integração; `main` é produção);
   - `develop` ou `dev`, se existir no remoto;
   - a branch padrão (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`).
4. Atualize a base e crie a branch a partir dela:

```powershell
git fetch origin
git switch -c feat/<slug-curto> origin/<base>
```

Prefixo `feat/` para feature e `fix/` para bug. Se o repositório já usa outro padrão nas branches (ex.: `feature/`), siga o padrão dele.

## 2. Ao concluir: resumo e uma aprovação

Só depois de testes verdes. Teste falhando: não peça aprovação, corrija ou reporte.

Mostre ao usuário: o que mudou, arquivos, resultado dos testes, branch e base. Peça uma única aprovação para commit, push, PR e merge. Sem aprovação, nada sai da máquina.

## 3. Com a aprovação

1. Se as User Rules ou uma rule do repositório definirem a conta do `gh`, confirme que ela está ativa:

```powershell
gh api user --jq .login
gh auth switch -u <conta>
```

   Rode o switch só se a primeira linha não retornar a conta definida. Não altere `git config`.

2. Commit:
   - Revise `git status` e `git diff`. Não inclua segredo (`.env`, credencial, token) nem artefato de build.
   - Mensagem curta, no estilo do repositório (`git log -8 --oneline`), focada no porquê.
   - Não use `--no-verify` nem `--amend`. No PowerShell, mensagem com here-string:

```powershell
git commit -m @"
Por que esta mudança existe.
"@
```

3. Push: `git push -u origin HEAD`. Nunca `--force` em `main`, `master`, `develop` ou `dev`.

4. PR contra a branch-base:

```powershell
gh pr create --base <base> --title "<título curto>" --body @"
## Summary
- <o que mudou e por quê>

## Test plan
- [x] <comando de teste e resultado>
"@
```

5. Checks e merge:

```powershell
gh workflow list
gh pr checks --watch --fail-fast
gh pr merge --squash --delete-branch
```

   - `gh workflow list` vazio: o repositório não tem checks e `gh pr checks` falharia. Pule esse comando; o merge segue com base nos testes locais.
   - Check falhando: não faça merge. Investigue, corrija na mesma branch, faça push e espere de novo.
   - Nunca faça merge automático numa branch que o repositório marca como produção quando há branch de integração (ex.: `develop → main`). Abra o PR de promoção só se o usuário pedir, e deixe o merge com ele.

6. Depois do merge: `git switch <base>` e `git pull`. Informe a URL do PR, o hash do merge e qualquer passo de deploy que a rule do repositório exigir.
