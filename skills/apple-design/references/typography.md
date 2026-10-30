# Tipografia: tamanho óptico, tracking e leading

De *The Details of UI Typography* (WWDC 2020). A Apple desenha a fonte para mudar de forma conforme o tamanho; a mesma disciplina vale na web.

- **Tracking (letter-spacing) depende do tamanho.** Texto grande de display pede tracking negativo, porque as letras parecem afastadas ao crescer; texto pequeno pede tracking levemente positivo. Um `letter-spacing` fixo está errado em algum tamanho. Aperte títulos, deixe o corpo perto de `0`.
- **Leading (line-height) é inverso ao tamanho.** Apertado em títulos grandes, mais solto no corpo. Aumente para scripts com ascendentes e descendentes altos; aperte em UI densa de informação.
- **Hierarquia vem de peso, tamanho e leading juntos**, não só de tamanho. Enfatize com peso: dá presença sem ocupar mais espaço.
- **Respeite o tamanho de texto do usuário.** Escale o layout junto com o texto, com espaçamento em `rem`/`em`, não px fixo, para fonte maior não quebrar o layout.
- **Comece pela fonte do sistema.** Ela já traz tamanho óptico, tabelas de tracking e ajuste de legibilidade. Troque só com motivo.

```css
:root { font: 100%/1.5 system-ui, sans-serif; }

.display {
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1.05;
  letter-spacing: -0.02em;
  font-optical-sizing: auto;
}
```
