---
name: resumo-de-contexto
description: Gera um resumo de até 10 linhas com objetivo, decisões, arquivos e próximos passos, pronto para colar num chat novo. Use quando a conversa ficou longa, o assunto mudou ou o usuário quer continuar em outro chat (resumo, resumir contexto, chat novo, continuar em outro chat).
---

# Resumo de contexto

Responda só com o bloco abaixo, no máximo 10 linhas, e uma linha dizendo para colá-lo no chat novo.

```
Objetivo: <o que se quer alcançar, em uma frase>
Decisões: <decisão>; <decisão>
Arquivos: <caminho> (<o que mudou ou por que importa>); <caminho> (...)
Estado: <pronto e verificado>; <o que ainda falha>
Evitar: <tentativa descartada e por quê> (só se evitar repetir erro)
Próximos passos: 1) <...> 2) <...>
```

## Regras

- Fonte é o que já está no chat. Não releia arquivos nem rode comandos para montar o resumo.
- Caminhos relativos à raiz do repositório. Sem código e sem log. Comando de verificação só se for essencial para o próximo passo.
- Só decisões que mudam o próximo passo. Dúvida em aberto vai para Próximos passos.
- Se o projeto tem `docs/progress/CURRENT.md`, cite-o numa linha em vez de repetir o conteúdo.
- Não grave arquivo. O resumo fica só no chat.
