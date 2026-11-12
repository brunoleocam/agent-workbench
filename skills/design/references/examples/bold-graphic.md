---
status: approved
direction: a
---

# Pauta — design system

Produto fictício: agenda cultural independente de uma cidade média, com shows, teatro e exposições da semana.

## 1. Tema visual e atmosfera

- Postura: um muro de lambe-lambes; cada evento disputa atenção, mas a hierarquia é clara.
- Densidade: equilibrada, com contraste forte entre blocos.
- **Escolha distintiva:** o dia da semana em caixa alta gigante (até 160px), cortado pela borda da tela, e cada categoria com uma cor chapada de cartaz.
- É: barulhento com intenção, local, impresso. Não é: corporativo, minimalista, "app de eventos".

## 2. Cor

| Token | Valor | Papel | Uso |
| --- | --- | --- | --- |
| `--color-surface` | `#f2efe6` | fundo | papel |
| `--color-ink` | `#111111` | texto | corpo e títulos |
| `--color-muted` | `#55524a` | texto secundário | local, horário |
| `--color-music` | `#e4572e` | categoria | bloco de shows |
| `--color-music-ink` | `#111111` | texto sobre categoria | título do show |
| `--color-stage` | `#29335c` | categoria | bloco de teatro |
| `--color-stage-ink` | `#f2efe6` | texto sobre categoria | título da peça |
| `--color-art` | `#f3a712` | categoria | bloco de exposições |
| `--color-art-ink` | `#111111` | texto sobre categoria | título da exposição |
| `--color-accent` | `#111111` | ação | botão principal |
| `--color-accent-ink` | `#f2efe6` | texto sobre ação | rótulo do botão |
| `--color-danger` | `#b3261e` | erro | evento cancelado |
| `--color-danger-ink` | `#ffffff` | texto sobre erro | faixa "cancelado" |
| `--color-focus` | `#0b6e4f` | foco | anel de foco |

Cada tela usa no máximo duas cores de categoria em destaque.

## 3. Tipografia

| Token | Família | Fallback |
| --- | --- | --- |
| `--font-display` | Anton | Impact, sans-serif |
| `--font-body` | Archivo | system-ui, sans-serif |
| `--font-mono` | Space Mono | ui-monospace, monospace |

| Token | Tamanho | Altura de linha | Peso | Uso |
| --- | --- | --- | --- | --- |
| `--text-day` | clamp(72px, 18vw, 160px) | 0.9 | 400 | dia da semana, caixa alta |
| `--text-event` | 32px | 1.05 | 400 | título do evento, caixa alta |
| `--text-body` | 17px | 1.5 | 400 | descrição |
| `--text-meta` | 14px | 1.4 | 400 | mono: horário e preço |

A altura de linha 0.9 só vale para uma linha. Títulos que quebram usam 1.05 para as letras não se chocarem.

## 4. Espaçamento e grid

Escala: `--space-1: 4px`, `--space-2: 8px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`, `--space-12: 48px`, `--space-16: 64px`.

Grid de 6 colunas com gutter de 16px. Os blocos de evento ocupam 2, 3 ou 6 colunas conforme o destaque, sem uma grade de cards iguais.

## 5. Layout e composição

Capítulos por dia: o dia gigante abre o capítulo e os eventos se empilham em blocos chapados de larguras diferentes. O olho cai no dia e depois no maior bloco. O dia fica alinhado à esquerda e cortado; nada é centralizado.

## 6. Componentes

- Bloco de evento: fundo da categoria, sem raio, sem sombra, título em `--font-display`, horário e preço em mono. Foco por teclado com anel de 3px `--color-focus` e offset de 3px.
- Botão: altura 48px, sem raio, borda de 2px `--color-ink`. Hover inverte as cores; focus-visible com anel; disabled com borda tracejada, `aria-disabled` e cursor `not-allowed`.
- Filtro de categoria: chips que quebram linha, com estado selecionado indicado por texto e preenchimento, não só cor.

## 7. Movimento e interação

- `--duration-feedback: 90ms`. Sem parallax.
- Ao mudar de dia, o dia gigante desliza 24px e entra; é o único movimento.
- Com reduced-motion, a troca de dia é instantânea.

## 8. Voz e microcopy

Fala como o cartaz: curto, local, com gíria da cidade quando cabe. Botões: "Quero ir", "Ver no mapa", "Avisar quando abrir venda", "Mostrar só grátis", "Compartilhar a semana". Erros: "Esse show foi cancelado pela banda. Os ingressos são reembolsados até sexta."

## 9. Anti-padrões

- Todos os P0 do lint.
- Sem grade de três cards iguais com ícone em cima.
- Sem foto de banco de imagens: cartaz real do evento ou bloco de cor com o título.
- Sem sombras e sem cantos arredondados: o papel é chapado.
- Rejeitado da referência: os contadores "+500 eventos" de sites de ingresso.
