---
status: approved
direction: c
---

# Turno — design system

Produto fictício: painel de despacho para uma central de entregas urbanas, usado o dia inteiro por despachantes em monitor grande.

## 1. Tema visual e atmosfera

- Postura: uma mesa de controle; cada pixel mostra estado, nenhum enfeita.
- Densidade: compacta. Muitas linhas visíveis sem rolagem.
- **Escolha distintiva:** todos os números em fonte mono tabular, alinhados à direita, e o estado de cada entrega mostrado por uma palavra curta em caixa alta, nunca só por cor.
- É: preciso, calmo sob pressão, legível de longe. Não é: festivo, gamificado, "dashboard de demo".

## 2. Cor

| Token | Valor | Papel | Uso |
| --- | --- | --- | --- |
| `--color-surface` | `#14171a` | fundo | aplicação |
| `--color-raised` | `#1c2024` | superfície elevada | painel, linha selecionada |
| `--color-ink` | `#e6e8e3` | texto | corpo |
| `--color-muted` | `#9aa19a` | texto secundário | rótulos de coluna |
| `--color-rule` | `#2c3237` | divisória | linhas da tabela |
| `--color-accent` | `#e0b341` | destaque | linha em foco, ação principal |
| `--color-accent-ink` | `#1a1404` | texto sobre destaque | rótulo do botão principal |
| `--color-danger` | `#ef6a5b` | atraso | estado ATRASADA |
| `--color-danger-ink` | `#1a0806` | texto sobre erro | faixa de alerta |
| `--color-success` | `#6fcf8f` | entregue | estado ENTREGUE |
| `--color-focus` | `#7cc4ff` | foco | anel de foco |

Orçamento do destaque: uma linha e um botão por vez.

## 3. Tipografia

| Token | Família | Fallback |
| --- | --- | --- |
| `--font-display` | Inter Tight | system-ui, sans-serif |
| `--font-body` | Inter Tight | system-ui, sans-serif |
| `--font-mono` | JetBrains Mono | ui-monospace, monospace |

| Token | Tamanho | Altura de linha | Peso | Uso |
| --- | --- | --- | --- | --- |
| `--text-h1` | 20px | 1.2 | 600 | nome da central |
| `--text-body` | 16px | 1.4 | 400 | linhas |
| `--text-label` | 12px | 1.3 | 600 | cabeçalho de coluna, caixa alta, tracking 0.06em |
| `--text-num` | 16px | 1.4 | 500 | mono tabular |

## 4. Espaçamento e grid

Escala: `--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`.

Layout em três painéis: fila (360px), mapa (flexível) e detalhe (400px). Linha de tabela com 36px de altura. Gutter de 8px entre painéis.

## 5. Layout e composição

Índice denso à esquerda, mapa ao centro, detalhe à direita. O olho cai primeiro na coluna ATRASO da fila, ordenada pelo mais crítico. Nada centralizado.

## 6. Componentes

- Linha da fila: 36px; selecionada com fundo `--color-raised` e fio superior e inferior em `--color-accent`; foco por teclado com anel de 2px `--color-focus`.
- Etiqueta de estado: texto em caixa alta mais ícone de forma (círculo, triângulo, quadrado) para não depender só de cor.
- Botão: altura 36px no desktop e 44px no toque, raio de 4px. Estados: default, hover, focus-visible, active, disabled (`aria-disabled`, cursor e opacidade), loading com spinner de 12px e rótulo mantido.

## 7. Movimento e interação

- `--duration-feedback: 80ms`. Nada de transição de página.
- Linha nova entra com fade de 120ms; contagem regressiva não anima.
- Com reduced-motion, nenhum fade.
- Atalhos de teclado (J/K para navegar, E para reatribuir) aparecem no tooltip de cada ação.

## 8. Voz e microcopy

Telegráfico e exato. Botões: "Reatribuir", "Ligar para o entregador", "Marcar como entregue", "Abrir rota", "Silenciar alerta por 10 min". Erros: "Sem sinal do entregador há 6 min. Ligue ou reatribua."

## 9. Anti-padrões

- Todos os P0 do lint.
- Sem cards: dado tabular fica em tabela.
- Sem gráfico decorativo no topo; o painel não é uma apresentação.
- Cor nunca é o único sinal de estado.
- Rejeitado da referência: os gradientes neon de painéis de cripto.
