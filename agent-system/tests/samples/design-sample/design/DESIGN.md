---
status: approved
direction: a
---

# Agenda Vet — design system

Clínica veterinária pequena, recepção, agenda do dia. Direção escolhida: A — Balcão, com densidade 8 e o nome do animal em itálico serifado trazido da direção B. Tokens em `design/tokens.css`.

## 1. Tema visual e atmosfera

- Postura: o balcão de uma clínica de bairro; a agenda de hoje é uma linha do tempo calorosa, e encaixar quem está no telefone nunca exige trocar de tela.
- Densidade: compacta-equilibrada (dial 8). O dia inteiro cabe na tela do computador da recepção sem virar planilha.
- **Escolha distintiva:** horários livres desenhados como "vagas" pontilhadas que se clica para encaixar, e o nome de cada animal em itálico serifado ao lado de um retrato redondo com a inicial.
- É: acolhedor, ágil, confiável. Não é: hospitalar, planilha, app de pet shop festivo.

## 2. Cor

| Token | Valor | Papel | Uso |
| --- | --- | --- | --- |
| `--color-surface` | `#fbf4ea` | fundo | página |
| `--color-raised` | `#ffffff` | superfície elevada | consulta, painel de encaixe |
| `--color-ink` | `#1f2a44` | texto | corpo e títulos (marinho da referência) |
| `--color-muted` | `#5e6475` | texto secundário | tutor, veterinário, data |
| `--color-rule` | `#ecdcc6` | divisória | borda pontilhada das vagas |
| `--color-accent` | `#c2410c` | destaque | botão principal, hover da vaga |
| `--color-accent-ink` | `#ffffff` | texto sobre destaque | rótulo do botão principal |
| `--color-soft` | `#fde4cc` | fundo suave | retrato do animal, etiqueta "esperando resposta" |
| `--color-soft-ink` | `#7a2d07` | texto sobre fundo suave | inicial do animal, texto da etiqueta |
| `--color-support` | `#0f766e` | confirmação | etiqueta "confirmado" |
| `--color-support-ink` | `#ffffff` | texto sobre confirmação | texto da etiqueta |
| `--color-danger` | `#b42318` | erro | aviso de WhatsApp desconectado |
| `--color-danger-ink` | `#ffffff` | texto sobre erro | texto do aviso |
| `--color-focus` | `#1d4ed8` | foco | anel de foco |

Contraste conferido por cálculo: todos os pares com `-ink`, a tinta e o texto secundário sobre o fundo passam de 4.5:1; o foco passa de 3:1. Orçamento do destaque: o botão principal e o hover da vaga, nada mais por tela. Estado nunca só por cor: a etiqueta sempre tem texto.

## 3. Tipografia

| Token | Família | Fallback |
| --- | --- | --- |
| `--font-display` | Baloo 2 | Trebuchet MS, system-ui, sans-serif |
| `--font-body` | Nunito Sans | system-ui, Segoe UI, sans-serif |
| `--font-pet` | Fraunces itálico | Georgia, serif |

| Token | Tamanho | Altura de linha | Peso | Uso |
| --- | --- | --- | --- | --- |
| `--text-h1` | 32px | 1.05 | 800 | resumo do dia |
| `--text-h2` | 24px | 1.1 | 800 | título do painel |
| `--text-pet` | 18px | 1.5 | 500 itálico | nome do animal, só nesse lugar |
| `--text-body` | 16px | 1.5 | 400 | corpo |
| `--text-small` | 14px | 1.5 | 400 | tutor e veterinário |
| `--text-tag` | 13px | 1.5 | 700 | etiquetas de estado |

Horários em números tabulares. `--font-pet` é a terceira família e fica restrita ao nome do animal.

## 4. Espaçamento e grid

Escala: `--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`, `--space-4: 16px`, `--space-6: 24px`, `--space-8: 32px`, `--space-12: 48px`. Nas telas de trabalho (densidade 8), use de 4px a 32px; 48px só em estados vazios.

Grid: coluna principal fluida e painel lateral de 360px (`--side-panel`) a partir de 960px; abaixo disso, uma coluna. Coluna de hora com 56px (`--time-column`). Linhas da agenda separadas por 4px.

## 5. Layout e composição

Linha do tempo à esquerda e painel de encaixe fixo à direita. O olho cai primeiro no resumo ("Hoje tem 6 consultas e 4 vagas"), depois na próxima vaga livre. Nada centralizado. As vagas ocupam a mesma linha que uma consulta ocuparia, para o encaixe parecer "preencher o buraco".

## 6. Componentes

- **Consulta:** cartão `--color-raised`, raio de 12px, padding 8px/12px, retrato redondo de 32px com a inicial, nome do animal em `--font-pet`, motivo, tutor e veterinário, etiqueta de estado à direita (quebra para baixo em telas estreitas).
- **Vaga livre:** botão de largura total, altura mínima de 44px, borda pontilhada de 2px `--color-rule`. Hover: borda `--color-accent` e fundo `--color-raised`. Focus-visible: anel de 2px `--color-focus` com offset de 2px.
- **Botão principal:** altura 44px, raio pill, fundo `--color-accent`, rótulo com o resultado ("Encaixar Thor às 09:30"). Estados: hover escurece; focus-visible com anel; active desce 1px; disabled com `aria-disabled`, cursor `not-allowed` e opacidade 0.55; loading troca o rótulo por "Encaixando…".
- **Campo:** altura 44px, raio de 8px, borda de 1px `--color-muted`, rótulo sempre visível acima; o erro aparece abaixo do campo.
- **Etiqueta de estado:** pill de 13px. "Confirmado" em `--color-support`; "Esperando resposta" em `--color-soft`.
- **Aviso de erro:** faixa `--color-danger` com causa e próximo passo.
- **Estado vazio:** bloco `--color-surface` no painel, com o que vai aparecer e a ação.

## 7. Movimento e interação

- `--duration-feedback: 120ms`, `--ease-standard: ease-out`. Só cor de borda e de fundo se movem.
- Com `prefers-reduced-motion: reduce`, a duração vai a 0.
- Não há gesto de arrastar nem mola nesta versão. Se um dia a agenda permitir arrastar consultas, siga a skill `apple-design`.

## 8. Voz e microcopy

Direto e caloroso, como uma colega experiente. Botões: "Encaixar Thor às 09:30", "Confirmar pelo WhatsApp", "Remarcar", "Ligar para o tutor", "Ver amanhã". Erros dizem causa e próximo passo: "O WhatsApp da clínica desconectou. A consulta fica marcada; reconecte para enviar a confirmação." Vazio convida: "Amanhã ainda está vazio depois das 15h."

## 9. Anti-padrões

- Todos os P0 do lint: índigo padrão, gradiente roxo/azul, emoji como ícone, card com faixa lateral, texto de preenchimento, métrica inventada, CDN de placeholder.
- Sem foto de banco de imagens: retrato com inicial, ou foto real do animal quando a clínica cadastrar.
- Sem piadas com bichos na interface; o tom é caloroso, não brincalhão.
- O laranja nunca vira fundo de faixa inteira.
- Rejeitado da referência (Do not copy do brief): contadores "2300+", emoji no título, pontinhos e brilhos decorativos, a grade de quatro cards de serviço iguais, as fotos, os textos e o layout de landing page.
