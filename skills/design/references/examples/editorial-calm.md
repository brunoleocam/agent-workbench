---
status: approved
direction: a
---

# Caderno — design system

Produto fictício: caderno de pesquisa para mestrandos e doutorandos, que organiza leituras, citações e rascunhos de capítulo.

## 1. Tema visual e atmosfera

- Postura: uma mesa de biblioteca silenciosa; o texto do usuário é o protagonista e a interface fica de lado.
- Densidade: espaçosa. A pessoa lê por longos períodos.
- **Escolha distintiva:** títulos em serifa de texto (Newsreader) em corpo grande, com números de capítulo em versalete na margem esquerda, como num livro.
- É: calmo, preciso, paciente. Não é: brincalhão, corporativo, "produtividade turbinada".

## 2. Cor

| Token | Valor | Papel | Uso |
| --- | --- | --- | --- |
| `--color-surface` | `#f6f3ec` | fundo | página |
| `--color-raised` | `#fffdf8` | superfície elevada | cartão de citação, diálogo |
| `--color-ink` | `#22201c` | texto | corpo e títulos |
| `--color-muted` | `#6b655b` | texto secundário | metadados, datas |
| `--color-rule` | `#d9d2c3` | divisória | fios entre seções |
| `--color-accent` | `#8a3b12` | destaque | link ativo, ação principal |
| `--color-accent-ink` | `#ffffff` | texto sobre destaque | rótulo do botão principal |
| `--color-danger` | `#a3261b` | erro | mensagem de erro |
| `--color-danger-ink` | `#ffffff` | texto sobre erro | faixa de erro |
| `--color-success` | `#2f6b3a` | sucesso | marcação "revisado" |
| `--color-focus` | `#1f4e79` | foco | anel de foco |

Orçamento do destaque: no máximo dois elementos por tela.

## 3. Tipografia

| Token | Família | Fallback |
| --- | --- | --- |
| `--font-display` | Newsreader | Georgia, serif |
| `--font-body` | Source Serif 4 | Georgia, serif |
| `--font-mono` | IBM Plex Mono | ui-monospace, monospace |

| Token | Tamanho | Altura de linha | Peso | Uso |
| --- | --- | --- | --- | --- |
| `--text-display` | 48px | 1.05 | 500 | título de capítulo |
| `--text-h2` | 28px | 1.2 | 500 | seção |
| `--text-body` | 19px | 1.6 | 400 | leitura |
| `--text-small` | 15px | 1.45 | 400 | metadados |

Medida de leitura: 66 caracteres.

## 4. Espaçamento e grid

Escala: `--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`, `--space-12: 48px`, `--space-16: 64px`, `--space-24: 96px`.

Grid de 12 colunas, gutter de 24px, largura máxima de 1120px. A margem esquerda de 2 colunas guarda os números de capítulo. Seções separadas por 96px e por um fio de 1px.

## 5. Layout e composição

Coluna editorial única com margem anotada à esquerda. O olho cai primeiro no título do capítulo, depois no primeiro parágrafo. Nada fica centralizado, exceto o estado vazio.

## 6. Componentes

- Botão: altura 44px, raio de 2px, padding horizontal de 16px. Principal com fundo `--color-accent`; secundário só com texto sublinhado. Estados: hover escurece o fundo, focus-visible com anel de 2px `--color-focus`, active desce 1px, disabled com cursor `not-allowed`, `aria-disabled` e opacidade 0.55, loading troca o rótulo por "Salvando…".
- Campo de texto: altura 44px, borda inferior de 1px, sem caixa. O erro aparece abaixo, em `--color-danger`.
- Citação: bloco com fio vertical de 1px `--color-rule` e sem raio (não é um card com faixa colorida).

## 7. Movimento e interação

- `--duration-feedback: 100ms`, `--duration-transition: 180ms`, easing `cubic-bezier(0.2, 0, 0, 1)`.
- Só a opacidade e a posição vertical se movem. Nada pula nem quica.
- Com `prefers-reduced-motion: reduce`, as transições somem.

## 8. Voz e microcopy

Tom de orientadora gentil: direto, sem euforia. Botões: "Guardar citação", "Abrir capítulo", "Comparar versões", "Exportar para ABNT", "Arquivar leitura". Erros dizem o que fazer: "A página da citação ficou vazia. Informe a página para a referência sair completa."

## 9. Anti-padrões

- Todos os P0 do lint: índigo padrão, gradiente roxo/azul, emoji como ícone, card com faixa lateral, texto de preenchimento, métrica inventada, CDN de placeholder.
- Sem ilustração decorativa: o conteúdo do usuário já é a imagem.
- Sem fundo branco puro: cansa a leitura longa.
- Rejeitado da referência: a barra lateral escura de apps de notas populares.
