# ADR-0001: Formato dos artefatos rastreáveis

Status: aceito
Data: 2026-11-03

## Contexto

Os validadores precisam ler spec, tarefas, testes e reviews sem dependência externa. O projeto já guarda documentos em Markdown nos caminhos de `layout.json`, e o TLC usa `.specs/`.

## Decisão

- Markdown continua sendo o formato. Um item rastreável é um título `##`–`######` que começa com o ID (`### REQ-001: título`). O bloco vai até o próximo título de nível igual ou maior.
- Os campos do bloco são linhas `- Chave: valor` com chaves conhecidas (lista em `agent-system/docs/artifacts.md`). O resto do bloco é texto livre (EARS, Given/When/Then).
- Front matter simples `chave: valor` no topo da spec e da review (`status`, `complexity`, `security_risk`). Sem YAML completo.
- Um arquivo por feature, com o mesmo slug em cada pasta: `<specs>/<slug>.md`, `<tasks>/<slug>.md`, `<tests>/<slug>.md` (opcional), `<reviews>/<slug>.md`, `<security>/<slug>.md`.
- Caminhos vêm de `layout.json` (`overrides` primeiro), com `docs/...` como padrão. `.specs/` não é imposto.

## Alternativas

- Bloco YAML ou JSON dentro do Markdown: parser mais fácil, leitura pior para pessoas e agentes, e YAML exigiria dependência.
- `.specs/` do TLC: quebraria o layout dos projetos existentes.

## Consequências

- Specs antigas sem IDs continuam válidas como texto e não passam pelos validadores.
- O parser reconhece só chaves conhecidas, então prosa com dois-pontos não vira campo por engano.
