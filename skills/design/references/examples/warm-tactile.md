---
status: approved
direction: b
---

# Brota — design system

Produto fictício: assinatura semanal de hortaliças de pequenos produtores da região, pedida pelo celular.

## 1. Tema visual e atmosfera

- Postura: uma feira de bairro num sábado de manhã; quem planta tem nome e rosto.
- Densidade: equilibrada.
- **Escolha distintiva:** cada produtor tem um carimbo tipográfico próprio (nome em caixa alta dentro de um selo redondo de 1px) que aparece na cesta e na entrega, como uma etiqueta de feira.
- É: acolhedor, honesto, de mão em mão. Não é: luxuoso, "wellness" genérico, startup de delivery.

## 2. Cor

| Token | Valor | Papel | Uso |
| --- | --- | --- | --- |
| `--color-surface` | `#fbf6ee` | fundo | aplicativo |
| `--color-raised` | `#ffffff` | superfície elevada | cesta, folha inferior |
| `--color-ink` | `#2a2118` | texto | corpo |
| `--color-muted` | `#76695a` | texto secundário | origem, peso |
| `--color-rule` | `#e8dccb` | divisória | listas |
| `--color-accent` | `#2f6b3a` | destaque | ação principal |
| `--color-accent-ink` | `#ffffff` | texto sobre destaque | rótulo do botão principal |
| `--color-highlight` | `#f2c14e` | ênfase | etiqueta "colhido ontem" |
| `--color-highlight-ink` | `#2a2118` | texto sobre ênfase | texto da etiqueta |
| `--color-danger` | `#b3261e` | erro | mensagem de erro |
| `--color-danger-ink` | `#ffffff` | texto sobre erro | faixa de erro |
| `--color-focus` | `#1d4f91` | foco | anel de foco |

Orçamento do destaque: o botão principal e no máximo uma etiqueta amarela por tela.

## 3. Tipografia

| Token | Família | Fallback |
| --- | --- | --- |
| `--font-display` | Fraunces | Georgia, serif |
| `--font-body` | Nunito Sans | system-ui, sans-serif |

| Token | Tamanho | Altura de linha | Peso | Uso |
| --- | --- | --- | --- | --- |
| `--text-display` | 32px | 1.1 | 600 | nome da cesta |
| `--text-h2` | 22px | 1.25 | 600 | seção |
| `--text-body` | 17px | 1.5 | 400 | corpo |
| `--text-stamp` | 12px | 1 | 800 | selo do produtor, caixa alta |

## 4. Espaçamento e grid

Escala: `--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`, `--space-4: 16px`, `--space-5: 20px`, `--space-6: 24px`, `--space-8: 32px`, `--space-12: 48px`.

Mobile primeiro: margem lateral de 20px, uma coluna. No desktop, coluna de 640px e lateral fixa com a cesta.

## 5. Layout e composição

Lista de itens da semana com foto real do produtor, agrupada por sítio. A cesta fica numa folha inferior que sobe com arrasto. O olho cai primeiro no nome do produtor, depois no item.

## 6. Componentes

- Botão principal: altura 48px, raio de 24px, largura total no mobile. Estados: hover, focus-visible (anel de 2px `--color-focus` com offset de 2px), active, disabled, loading ("Separando sua cesta…").
- Item: foto quadrada de 72px com raio de 8px, nome, produtor e peso, e o seletor de quantidade com alvos de 44px.
- Selo do produtor: círculo de 1px em `--color-ink`, texto `--text-stamp`.

## 7. Movimento e interação

- `--duration-feedback: 120ms`, `--duration-sheet: 280ms`.
- A folha da cesta segue o dedo e solta com mola: siga a skill `apple-design` (interrupção, velocidade herdada, mola em vez de duração fixa).
- Ao adicionar um item, o contador da cesta sobe 2px e volta. É a única animação de destaque.
- Com reduced-motion, a folha abre sem mola e o contador não se move.

## 8. Voz e microcopy

Fala como a pessoa da banca. Botões: "Pôr na cesta", "Trocar por outro item", "Pular esta semana", "Avisar o produtor", "Confirmar entrega de sábado". Erros: "O Sítio Boa Vista não colhe couve esta semana. Quer trocar por espinafre do mesmo sítio?"

## 9. Anti-padrões

- Todos os P0 do lint.
- Sem foto de banco de imagens: só foto real do produtor ou um bloco rotulado "foto do produtor".
- Sem verde-limão de "saudável" nem folhas decorativas.
- Rejeitado da referência: o carrossel automático de promoções.
