---
name: apple-design
description: Builds or reviews fluid, Apple-style interactive motion on the web — drag, swipe, sheets, carousels, spring animations, momentum, interruptible transitions, and reduced-motion fallbacks. Use when implementing or reviewing gesture-driven UI or spring animation (animação fluida, gesto, arrastar, swipe, sheet, drawer, spring, momentum, estilo Apple).
---

# Apple design: motion interativo na web

Baseada nas palestras de design da Apple na WWDC, principalmente *Designing Fluid Interfaces* (2018), traduzidas para a web: CSS, Pointer Events, `requestAnimationFrame` e bibliotecas de spring como Motion.

Complementa `ui-ux`: aquela constrói a tela e os estados; esta define como a interface se move e responde ao toque.

Princípio central: a interface parece viva quando o movimento parte do valor atual na tela, herda a velocidade do usuário, projeta o momentum adiante e pode ser agarrado e revertido a qualquer instante. Springs resolvem isso porque são interrompíveis e aceitam velocidade inicial.

Referências, carregue só quando o pedido tocar no assunto:

- [references/materials.md](references/materials.md): translucidez, profundidade, `backdrop-filter`, feedback com som e haptics.
- [references/typography.md](references/typography.md): tracking, leading, tamanho óptico, fonte do sistema.
- [references/principles.md](references/principles.md): os oito princípios de design da Apple, feedback, navegação e processo.

## 1. Resposta imediata

- Dê feedback no `pointerdown`, não no `click`. Destaque o botão no instante do toque; confirme a ação no `pointerup`.
- Corte latência no caminho do input: debounce, timer artificial, espera de transição. Garanta `<meta name="viewport" content="width=device-width">` e `touch-action: manipulation` para não haver atraso de toque.
- Em drag, slider ou drawer, atualize a interface 1:1 com o ponteiro durante todo o gesto, não só no fim.

```css
.button:active {
  transform: scale(0.97);
  transition: transform 100ms ease-out;
}
```

No Safari do iOS, `:active` só dispara se houver um listener de toque na página. Em componente crítico, prefira uma classe aplicada no `pointerdown`.

## 2. Manipulação direta

O elemento acompanha o dedo a partir do ponto onde foi agarrado. Pular para o centro do elemento quebra a ilusão.

- Use Pointer Events com `setPointerCapture`, para o rastreamento continuar fora dos limites do elemento.
- Guarde um histórico curto de posição e timestamp dos últimos `pointermove`; a velocidade de soltura sai daí.

```js
el.addEventListener('pointerdown', (e) => {
  el.setPointerCapture(e.pointerId);
  const grabOffset = e.clientY - el.getBoundingClientRect().top;
  // registrar posição + timestamp a cada pointermove para calcular a velocidade
});
```

## 3. Interrupção

O princípio mais importante: toda animação pode ser agarrada e redirecionada a qualquer momento. Um modal fechando que o usuário agarra de novo segue o dedo; não termina de fechar para depois reabrir.

- Nunca bloqueie input durante uma transição.
- Anime sempre a partir do valor apresentado na tela, nunca do valor-alvo. Na interrupção, leia o transform atual e comece dali.
- Para gesto, não use transition CSS nem `@keyframes`. Uma transition interrompida até reverte a partir do valor atual, mas perde a velocidade e dá um tranco. Springs carregam a velocidade no re-target.
- Na reversão do gesto, a nova animação herda a velocidade atual. Trocar uma animação por outra do zero cria um "muro" de velocidade.
- Movimento 2D: um spring independente para X e outro para Y. Um spring só sobre a distância 2D dessincroniza quando as velocidades diferem.

## 4. Springs em vez de duração fixa

Animação com duração fixa não responde a input novo. Num spring, input novo só muda o alvo e o movimento continua. Use spring para tudo que o usuário pode tocar.

A Apple usa dois parâmetros em vez de massa, rigidez e amortecimento:

- **Damping ratio**: controla o overshoot. `1.0` = criticamente amortecido, sem quique. Abaixo de `1.0`, quica; quanto menor, mais quica.
- **Response**: rapidez para chegar ao alvo, em segundos. Menor = mais ágil. Não é duração; o tempo de assentar emerge dos parâmetros.

Padrões:

- Comece com damping `1.0`.
- Use damping perto de `0.8` só quando o gesto trouxe momentum (flick, arremesso, soltar um drag). Quique num menu que apenas apareceu fica errado; num card arremessado fica certo.

| Interação | Damping | Response |
| --- | --- | --- |
| Mover / reposicionar (ex.: PiP) | `1.0` | `0.4` |
| Rotação | `0.8` | `0.4` |
| Drawer / sheet | `0.8` | `0.3` |

No Motion, `bounce` e `visualDuration` aproximam damping e response: `bounce ≈ 1 − damping` e `visualDuration ≈ response`. É uma aproximação; ajuste no olho.

```js
import { animate } from 'motion';

animate(el, { y: 0 }, { type: 'spring', bounce: 0, visualDuration: 0.4 });

// quique leve, só porque um flick veio antes
animate(el, { y: target }, { type: 'spring', bounce: 0.2, visualDuration: 0.4, velocity: releaseVelocity });
```

## 5. Passagem de velocidade

Quando o gesto termina, a animação continua na velocidade exata do dedo, sem emenda visível entre arrastar e animar. É o detalhe que mais separa "fluido" de "ok".

Passe a velocidade de soltura como velocidade inicial do spring. Motion aceita px/s absoluto na opção `velocity`. APIs que pedem velocidade relativa:

```
velocidadeRelativa = velocidadeDoGesto / (alvo − valorAtual)
```

Exemplo: elemento em `y=50`, alvo `y=150`, dedo a 50 px/s → `50 / 100 = 0.5`.

## 6. Projeção de momentum

Não escolha o ponto de encaixe mais próximo de onde o dedo soltou. Projete onde o elemento pararia, como na desaceleração do scroll, e encaixe no ponto mais próximo da projeção. Isso faz o flick parecer um arremesso.

```js
// decelerationRate ≈ 0.998 para sensação de scroll normal; 0.99 para mais ágil
function project(initialVelocity /* px/s */, decelerationRate = 0.998) {
  return (initialVelocity / 1000) * decelerationRate / (1 - decelerationRate);
}

const projectedEndpoint = currentPosition + project(releaseVelocity);
const target = nearestSnapPoint(projectedEndpoint);
animateSpringTo(target, { velocity: releaseVelocity });
```

É a função do sample code da Apple. Não use a fórmula de física `v²/(2·desaceleração)`. Para decidir entre fechar e voltar, use o sinal da velocidade na soltura, não só a posição.

## 7. Consistência espacial

- Entra e sai pelo mesmo caminho. Painel que entra pela direita sai pela direita.
- Ancore no gatilho: menu, popover ou sheet nasce do elemento que o abriu. Use `transform-origin` no lado do gatilho, não no centro.
- O movimento intermediário aponta para o resultado. Os módulos do Control Center "crescem para cima e para fora, em direção ao dedo".
- Em transição reversível sem gesto, espelhe a curva: ida e volta com pontos de controle de cubic-bézier invertidos. Com gesto, use spring.

## 8. Rubber-band nos limites

No limite, resista de forma progressiva em vez de parar seco. Parada seca parece travamento; resistência contínua diz "responde, mas não há mais nada aqui".

```js
function rubberband(overshoot, dimension, constant = 0.55) {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot));
}
```

## 9. Detalhes de gesto

- Toque: destaque no down, confirme no up. Margem de uns 10px ao redor do alvo; permita cancelar arrastando para fora e voltar.
- Drag e swipe: limiar de uns 10px antes de fixar a direção, depois rastreie 1:1.
- Reconheça todos os gestos possíveis em paralelo desde o primeiro movimento e cancele os perdedores quando a intenção ficar clara. Evite recognizers que só informam o estado final (eventos tipo `swipeleft`).
- Detectar duplo toque atrasa o toque simples. Só pague esse custo onde o duplo toque existe.

## 10. Suavidade por frame

- Anime só `transform` e `opacity`. Use `will-change` quando o movimento for iminente e remova depois.
- `requestAnimationFrame` é o relógio sincronizado com a tela.
- Mantenha o deslocamento por frame abaixo do limiar de percepção para evitar efeito estroboscópico. Em movimento muito rápido, um leve blur ou estiramento comunica velocidade melhor que um rastro nítido.

## 11. Reduced motion

Reduced motion não é ausência de feedback; é um equivalente sem movimento vestibular.

- Com `prefers-reduced-motion: reduce`, troque slide, spring e parallax por fade curto ou mudança instantânea. Tire o quique. Mantenha as mudanças de opacidade e cor que ajudam a entender.
- Remova a animação, não a posição. Um sheet fechado com `translateY(100%)` continua fora da tela; só deixa de deslizar.

```css
@media (prefers-reduced-motion: reduce) {
  .sheet { transition: opacity 200ms ease; }
}
```

```js
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

animate(el, { y: target }, reduceMotion
  ? { duration: 0 }
  : { type: 'spring', bounce: 0, visualDuration: 0.4 });
```

Evite também fundo em movimento ocupando a tela toda, oscilação lenta em loop (perto de 0,2 Hz) e salto brusco de brilho; suavize a troca entre tema claro e escuro.

## Review

Ao revisar uma interação, percorra a lista e reporte só o que falha, com arquivo e linha:

1. Feedback aparece no `pointerdown`?
2. O drag respeita o ponto onde o elemento foi agarrado e usa `setPointerCapture`?
3. Dá para agarrar a animação no meio e reverter sem salto?
4. A animação parte do valor na tela e herda a velocidade de soltura?
5. O encaixe usa projeção de momentum e o sinal da velocidade?
6. Quique só aparece depois de gesto com momentum?
7. Limites usam rubber-band?
8. Entrada e saída pelo mesmo caminho, ancoradas no gatilho?
9. Só `transform` e `opacity` são animados?
10. Com reduced motion, o elemento termina na posição certa, sem slide nem spring?

Formato: `[falha] arquivo:linha — o que acontece — correção sugerida`. Se nada falhar, diga isso em uma linha.

## Referência rápida

| Necessidade | Técnica | Valor |
| --- | --- | --- |
| Spring padrão | Criticamente amortecido | damping `1.0`, response `0.3–0.4` |
| Spring após flick | Pouco quique | damping `~0.8`, response `0.3–0.4` |
| Gesto → spring | Passar a velocidade de soltura | `velocidade / (alvo − atual)` se relativa |
| Ponto de parada do flick | Projetar momentum | `atual + (v/1000)·d/(1−d)`, `d ≈ 0.998` |
| Interromper | Partir do valor na tela | ler o transform atual |
| Fechar ou voltar | Sinal da velocidade | na soltura |
| Drag 1:1 | Pointer Events + capture | respeitar o ponto agarrado |
| Limite | Rubber-band | resistência progressiva |
| Reduced motion | Fade ou salto, posição mantida | `prefers-reduced-motion` |
