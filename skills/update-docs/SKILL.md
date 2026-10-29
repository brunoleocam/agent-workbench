---
name: update-docs
description: Updates project documentation so specs, ADRs, verification notes, and progress match the behavior just changed. Use when the user asks to update docs, or when a meaningful change left specification or architecture docs stale (atualizar documentação, spec desatualizada, ADR).
---

# Atualizar documentação

A doc descreve o que o sistema deve fazer e as decisões vigentes. Não reescreva histórico.

1. Leia a doc canônica do repo antes de editar. Se já existir lugar para spec ou ADR, use-o. Não crie a árvore `docs/` inteira num repo antigo.
2. Atualize só o que esta mudança alterou:
   - comportamento → spec e critérios de aceite
   - decisão de arquitetura nova → ADR novo; não edite o ADR aceito
   - verificação → nota em `docs/tests/` ou o arquivo de testes que o repo já usa para estratégia
   - estado da frente → `docs/progress/CURRENT.md` ou o progresso que o repo já tiver
3. Não documente comportamento que você não leu no código ou não verificou.
4. Não duplique o mesmo fato em dois arquivos. Aponte para o canônico.
5. Não crie `AGENTS.md` neste fluxo.

Diga quais arquivos mudaram e qual comportamento cada um passou a descrever.
