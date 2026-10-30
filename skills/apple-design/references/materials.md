# Materiais, profundidade e feedback multimodal

## Translucidez indica hierarquia

A Apple usa materiais translúcidos como uma camada funcional flutuante, que organiza sem roubar o foco. Na web, aproxime com `backdrop-filter`.

- Barras de navegação, toolbars e sheets como camadas translúcidas (`backdrop-filter: blur()` + fundo semitransparente) com o conteúdo rolando por baixo, não barras opacas ocupando uma faixa fixa.
- O peso do material codifica hierarquia: materiais mais escuros e densos separam regiões estruturais (sidebars); mais claros chamam atenção para elementos interativos (botões). Nunca empilhe uma superfície translúcida clara sobre outra; a legibilidade desaba.
- Superfície maior parece mais espessa: blur mais forte e sombra mais funda que em chips pequenos. Sombra mais pesada sobre conteúdo movimentado ou texto; mais leve sobre fundo liso.
- Escureça para focar, separe para manter o fluxo. Tarefa modal: superfície com scrim escuro e fundo empurrado para trás. Painel paralelo, não bloqueante: translucidez e deslocamento, sem scrim. Em sheets empilhados, escureça e empurre cada camada pai progressivamente.
- Texto sobre superfície translúcida: nada de cinza chapado. Use mais contraste, peso um pouco maior e um leve aumento de letter-spacing. Cor vai numa camada sólida, não no primeiro plano translúcido.
- Em vez de divisória de 1px sob um header fixo, use um leve blur ou máscara de gradiente onde o conteúdo encontra o elemento flutuante, só onde há sobreposição de fato.
- Materialize, não só faça fade: em superfícies com blur, anime raio do blur e escala juntos na entrada e na saída.

```css
.toolbar {
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(20px) saturate(180%);
  border-top: 1px solid rgba(255, 255, 255, 0.4);
}
```

## Acessibilidade dos materiais

- `prefers-reduced-transparency: reduce`: superfície mais sólida, fundo mais opaco, sem blur.
- `prefers-contrast: more`: fundo quase sólido e borda definida e contrastante.

`prefers-reduced-transparency` ainda não tem suporte amplo entre navegadores. O visual padrão precisa ser legível sem depender dessa media query.

```css
@media (prefers-reduced-transparency: reduce) {
  .toolbar { background: white; backdrop-filter: none; }
}
```

## Feedback multimodal: movimento, som e haptics

Três regras, de *Designing Audio-Haptic Experiences*:

1. **Causalidade**: fica óbvio o que causou o feedback. Dispare no evento causal real (o toggle virou, o item encaixou) e combine o caráter do feedback com a fisicalidade da ação.
2. **Harmonia**: visual, som e haptic no mesmo frame. Atraso entre eles quebra a ilusão; não deixe uma transition CSS atrasar o som ou a vibração.
3. **Utilidade**: só onde vale a pena. Reserve som e haptic para momentos relevantes (sucesso, erro, confirmação, encaixe). Excesso ensina o usuário a ignorar tudo.

A Vibration API não funciona no Safari do iOS. Na web, haptic é bônus em Android; o feedback visual tem de bastar sozinho.
