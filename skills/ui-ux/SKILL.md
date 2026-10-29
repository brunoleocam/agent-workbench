---
name: ui-ux
description: Designs and builds a user interface for a defined task, including empty, error, and loading states. Use when creating a screen, flow, component, or experience (criar UI, criar UX, tela, fluxo, interface).
---

# Criar UI/UX

Constrói a interface já escolhida. Se ainda houver alternativas em aberto, use `ui-ux-experiment` ou `brainstorm` antes.

1. Nomeie a tarefa do usuário e o estado de sucesso.
2. Se existir design system no repo, reutilize componente, espaçamento e tom. Não substitua o sistema.
3. Cubra estado vazio, carregando, erro e sucesso. Cada um com o próximo passo do usuário.
4. Controles com nome acessível, foco por teclado e contraste legível.
5. Implemente pela spec ou pelo plano. Siga `tdd` onde a lógica de interface for testável.
6. Em aplicação web, verifique o fluxo no browser: clicar, digitar, enviar, navegar. Screenshot sozinho não fecha a tarefa. Confira também a outra tela que lê o mesmo estado.

Não crie `AGENTS.md`. Não commite a menos que o usuário peça.
