---
status: approved
---

# Brief de design: Agenda Vet

Origem de cada item: `fornecido` (o usuário disse), `observado` (visto numa referência ou no código), `inferido` (deduzido do contexto; confirme se estiver errado).

## Público

- Quem usa: recepcionista de clínica veterinária pequena, com 1 a 3 veterinários (inferido, do README)
- Em que situação: no computador da recepção, muitas vezes com o tutor no telefone ou no balcão (inferido, do README)
- O que já usam hoje: agenda de papel ou planilha, e WhatsApp para confirmar (inferido)

## Tarefa principal

- A tarefa que precisa terminar na tela principal: ver a agenda de hoje e encaixar uma consulta num horário livre (fornecido)
- Como se sabe que deu certo: a consulta aparece no horário certo, com animal, tutor e motivo, sem trocar de tela (inferido)

## Tom de voz

- Como o produto fala: direto e caloroso, como uma colega experiente. Exemplo: "Rex volta para a vacina dia 12." (fornecido)
- Como não fala: linguagem de sistema ("registro efetuado com sucesso") nem piadas com bichos (inferido)

## Densidade

- Equilibrada: o dia inteiro visível sem parecer planilha, com espaço entre os horários (fornecido)

## Idioma

- Português do Brasil (inferido, do README)

## Restrições

- Marca existente (cores, fontes, logo): nenhuma (inferido; confirme)
- Acessibilidade: mínimo WCAG AA; leitura rápida de relance enquanto atende (inferido)
- Plataforma: web, desktop na recepção, de 1280px para cima; precisa funcionar em 320px sem quebrar (inferido, do README)
- Não gosta de: nada informado (fornecido)

## Referências

Uma referência (fornecido). É uma landing page de marketing para pet care; o Agenda Vet é uma ferramenta de trabalho da recepção, então a referência dá a temperatura e o caráter, não a estrutura.

| Referência | Keep | Change | Do not copy |
| --- | --- | --- | --- |
| [Pet Care / Veterinary website UI (Figma Community, XpartUI)](https://www.figma.com/pt-br/comunidade/file/1610793395088085487/pet-care-or-pet-grooming-or-veterinary-or-vaccination-figma-website-ui-design) (fornecido) | Paleta quente: laranja forte sobre creme, com azul-marinho escuro como tinta e um verde-azulado de apoio (observado). Títulos em fonte display encorpada e amigável (observado). Fotos de animais recortadas em formas redondas (observado). Clima acolhedor, nada clínico ou hospitalar (observado). | A estrutura: de página de marketing (hero, serviços, chamada) para uma agenda do dia, densa o suficiente para a recepção (inferido). O laranja vira destaque pontual, não fundo de faixas inteiras (inferido). | Os contadores "2300+" e similares, emoji no título, pontinhos e brilhos decorativos, a grade de quatro cards de serviço iguais, as fotos, os textos e o layout do arquivo (observado). |
