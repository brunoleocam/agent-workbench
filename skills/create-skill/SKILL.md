---
name: create-skill
description: Creates a personal Cursor skill in the user profile, with a slash name and a /help entry. Use when the user asks to create, add, or author a skill (criar skill, nova skill, comando novo).
---

# Criar skill

Skill nova do plugin agent-workbench, disponível em qualquer repositório e em qualquer máquina com o plugin. Não crie skill dentro do repositório aberto, a menos que o usuário peça skill do projeto.

Não grave em `~/.cursor/skills-cursor/`. Esse diretório é do Cursor.

## Destino

`<plugin>/skills/<nome>/SKILL.md`, onde `<plugin>` é a raiz do plugin agent-workbench, dois níveis acima deste `SKILL.md`. O `name` do frontmatter é igual ao nome da pasta. Skill específica de empresa ou linguagem não entra no plugin, que é público: pergunte onde gravar.

Se o usuário pedir skill só daquele repositório, aí sim use `.cursor/skills/<nome>/SKILL.md` do projeto.

## Antes de escrever

1. Extraia do pedido: o que a skill faz, quando dispara, e se é comando explícito (`/nome`) ou se o agente deve puxá-la sozinho.
2. Nome: minúsculas, números e hífen, no máximo 64 caracteres. O nome é o comando.
3. Se o texto da skill foi dado pelo usuário para usar exatamente, copie esse texto. Não parafraseie.
4. Não duplique uma skill do perfil que já cubra o mesmo trabalho. Estenda a existente se for o mesmo comando.

## SKILL.md

```markdown
---
name: nome-da-skill
description: O que faz e quando usar, em terceira pessoa, com o gatilho em português entre parênteses.
---
```

`disable-model-invocation: true` só quando a skill deve rodar exclusivamente porque a pessoa digitou `/nome` (como `/help`). Sem esse campo, o agente pode aplicar a skill quando o pedido combinar com a description.

Corpo em pt-BR. Passos acionáveis. Abaixo de 500 linhas. Detalhe longo vai para um arquivo ao lado, linkado uma vez a partir do `SKILL.md`. Sem path Windows no texto da skill.

Description: o que faz e quando usar. Inclua as palavras com que a pessoa pede isso.

## Depois de criar

1. Acrescente um item em `skills/help/SKILL.md`, na lista de comandos: o que o comando faz e o que ele não faz.
2. Se a skill mudar a classificação de pedido de código, uma linha na regra `01-request-classification`. Não inflar essa regra com skill que não escolhe fluxo de implementação.
3. Não crie `AGENTS.md`. Não commite, a menos que o usuário peça.

Responda com o comando (`/nome`) e em que situação ele entra.
