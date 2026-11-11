---
name: commit-push
description: Git flow for features and bug fixes - branch before editing, then one approval for commit, push, PR and merge after green tests. Use when starting or finishing a feature or bug fix in a git repo, or when the user asks to commit, push, open a PR or merge (commit, push, PR, subir para o GitHub).
---

# Branch, commit, push, PR, and merge

Every feature or bug fix in a git repository follows this flow.

A folder without `.git`: do not run `git init` or create a repository unless the user asks. Warn and proceed without the flow.

## 1. Before editing code: branch

1. In parallel: `git status --short`, `git branch --show-current`, `git remote get-url origin`.
2. Working tree with a change that is not from this task: ask before creating the branch.
3. Base branch, in this order:
   - the one a repository rule or skill defines (e.g. `develop` for integration; `main` is production);
   - `develop` or `dev`, if it exists on the remote;
   - the default branch (`gh repo view --json defaultBranchRef -q .defaultBranchRef.name`).
4. Update the base and create the branch from it:

```powershell
git fetch origin
git switch -c feat/<short-slug> origin/<base>
```

Prefix `feat/` for a feature and `fix/` for a bug. If the repository already uses another branch pattern (e.g. `feature/`), follow its pattern.

## 2. When done: summary and one approval

Only after green tests. A failing test: do not ask for approval, fix it or report it.

Show the user: what changed, files, test results, branch and base. Ask for a single approval for commit, push, PR, and merge. Without approval, nothing leaves the machine.

## 3. With the approval

1. If the User Rules or a repository rule define the `gh` account, confirm it is active:

```powershell
gh api user --jq .login
gh auth switch -u <account>
```

   Run the switch only if the first line does not return the defined account. Do not change `git config`.

2. Commit:
   - Review `git status` and `git diff`. Do not include secrets (`.env`, credentials, tokens) or build artifacts.
   - A short message, in the repository's style (`git log -8 --oneline`), focused on why.
   - Do not use `--no-verify` or `--amend`. In PowerShell, use a here-string for the message:

```powershell
git commit -m @"
Why this change exists.
"@
```

3. Push: `git push -u origin HEAD`. Never `--force` on `main`, `master`, `develop`, or `dev`.

4. PR against the base branch:

```powershell
gh pr create --base <base> --title "<short title>" --body @"
## Summary
- <what changed and why>

## Test plan
- [x] <test command and result>
"@
```

5. Checks and merge:

```powershell
gh workflow list
gh pr checks --watch --fail-fast
gh pr merge --squash --delete-branch
```

   - Empty `gh workflow list`: the repository has no checks and `gh pr checks` would fail. Skip that command; the merge proceeds based on the local tests.
   - A failing check: do not merge. Investigate, fix on the same branch, push, and wait again.
   - Never auto-merge into a branch the repository marks as production when an integration branch exists (e.g. `develop → main`). Open the promotion PR only if the user asks, and leave the merge to them.

6. After the merge: `git switch <base>` and `git pull`. Report the PR URL, the merge hash, and any deploy step the repository rule requires.
