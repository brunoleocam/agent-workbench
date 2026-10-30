# Princípios de design e processo

Os oito princípios de *Principles of Great Design* (WWDC 2026), citados pela skill original. Use estes nomes ao justificar uma decisão de design.

1. **Propósito.** Faça com intenção e decida o que não construir. Cada recurso pede tempo, atenção e confiança do usuário; gaste só onde compensa.
2. **Agência.** O usuário no controle: ofereça escolhas, não um caminho único. Perdoe erros com desfazer fácil; diálogo de confirmação só para ação destrutiva e irreversível. Confirmação em excesso ensina a clicar sem ler.
3. **Responsabilidade.** Aja no interesse do usuário. Privacidade: peça na hora certa, só o necessário, com transparência. Segurança: antecipe mau uso e dano, especialmente com IA. Use prévia, confirmação e aviso; corte o recurso cujo risco supera o valor.
4. **Familiaridade.** Construa sobre o que as pessoas já conhecem. Metáforas nem literais nem abstratas demais (lixeira = apagar), respeitando a física delas. O que parece igual se comporta igual e fica no mesmo lugar. Só quebre um padrão familiar se provar que o novo é melhor, e teste.
5. **Flexibilidade.** Projete para contextos, dispositivos e capacidades diferentes. Celular é toque rápido; desktop é fluxo profundo com ponteiro preciso. Inclua idade, idioma, experiência e acessibilidade. Quando nenhum layout serve a todos, deixe personalizar.
6. **Simplicidade, não minimalismo.** Tire o desnecessário para o propósito aparecer; esconder tudo num lugar parece mínimo mas não é simples. Linguagem direta, menos passos, hierarquia clara por ordem, espaçamento e contraste. Às vezes adicionar contexto simplifica. Caminho comum primeiro; opção avançada um nível abaixo.
7. **Cuidado artesanal.** Atenção ao detalhe gera confiança: tipografia, cores que se adaptam a claro e escuro, ícones claros, animação responsiva. Nenhum valor é aleatório; todo espaçamento, tempo e alinhamento tem justificativa. Scroll trêmulo e ícone desalinhado parecem descuido.
8. **Encanto.** Resultado de acertar os outros sete, não confete colado por cima. Decida a emoção (calma, confiança, empolgação) e reforce em cada decisão.

## Regras táticas

- **Feedback tem quatro tipos:** status, conclusão, aviso e erro. Confirme ações relevantes, exponha status em andamento, avise antes do problema, valide inline e não só no envio.
- **Orientação.** Toda tela responde: onde estou, para onde posso ir, o que há lá, como saio. Nunca prenda o usuário.
- **Agrupamento e mapeamento.** Proximidade indica relação. Coloque o controle perto do que ele afeta, organizado como aquilo que ele muda. Se o controle precisa de rótulo para explicar, o mapeamento está fraco.
- **Rótulo específico vence rótulo genérico.** Nomeie a navegação pelo conteúdo ("Progresso", "Biblioteca"), não por guarda-chuvas vagos ("Início").

## Processo

- Prototipe de forma interativa. Um protótipo funcionando vale mais que muitas telas estáticas e fixa um padrão concreto para a versão final.
- Projete interação e visual juntos; movimento não é uma camada aplicada depois dos pixels.
- Teste com pessoas reais em contexto real. Revise o movimento em câmera lenta ou frame a frame para pegar o que passa despercebido na velocidade normal.
