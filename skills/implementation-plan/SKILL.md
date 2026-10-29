---
name: implementation-plan
description: Writes a comprehensive implementation plan with exact file paths, complete code examples, and verification steps for an engineer with zero codebase context. Use when the design or spec is approved and tasks must be detailed before coding (plano de implementação, quebrar em tarefas, design pronto).
---

# Plano de implementação

O design ou a spec já está aprovado. Esta skill produz o plano. Não implementa.

O leitor é um engenheiro habilidoso, sem contexto deste repositório e com pouco conhecimento do domínio. Caminho de arquivo, exemplo e verificação têm de bastar sozinhos.

## Antes de escrever

1. Leia a spec aprovada e o código que os caminhos citam. Não invente path. Se o arquivo ainda não existe, marque como criar e mostre o diretório pai real.
2. Se a spec cobre subsistemas independentes, proponha um plano por subsistema. Cada plano entrega software testável.
3. Mapeie os arquivos a criar ou alterar e a responsabilidade de cada um. Siga o padrão do repo. Não reestruture arquivo alheio à spec.

## Onde gravar

`docs/tasks/` se o projeto usa a árvore spec-driven. Senão, o lugar de planos que o repo já tiver. Um arquivo por frente: `docs/tasks/NNNN-titulo.md`.

## Cada tarefa

Uma tarefa é o menor pedaço que um revisor pode aceitar ou recusar sozinho, com teste próprio.

Para cada tarefa:

- Requisito ou critério de aceite que ela cobre
- Paths exatos
- Passos em ordem: teste que falha, comando para ver a falha, código mínimo, comando para ver o verde, regressão
- Exemplo de código completo do que não for óbvio, no estilo do repo. Sem pseudocódigo no lugar do código
- Resultado esperado de cada comando
- Dependência de outra tarefa, se houver

Cabeçalho do arquivo: objetivo em uma frase, abordagem, stack já usada no repo, restrições copiadas da spec.

Não commite o plano a menos que o usuário peça. Ao terminar, o próximo passo é `implementation` ou `tdd`, uma tarefa por vez.
