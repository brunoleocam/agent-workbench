---
status: draft
---

<!-- architecture/brief.md. Write the content in the user's language. Every line ends with its origin:
     (fornecido) = the user said it; (observado: <file>) = seen in a file; (inferido) = deduced.
     A section that does not apply says why in one sentence. -->

# Brief de arquitetura: <nome do sistema>

## Propósito

- O que o sistema faz e para quem, em uma ou duas frases. (fornecido)

## Usuários e carga

- Usuários ativos hoje: <número> por <dia | mês>. (fornecido | observado: <arquivo> | inferido)
- Usuários ativos em 12 meses: <número>. (fornecido | inferido)
- Ações por usuário por dia: <número>. (inferido)
- Picos: quando acontecem e quantas vezes a média. (fornecido | inferido)

## Padrão de acesso

- Proporção leitura/escrita: <por exemplo 50 para 1>. (inferido)
- Tamanho típico dos dados: registros de texto, imagens, vídeo, com o tamanho médio. (observado: <arquivo> | inferido)
- Consultas mais frequentes: <as 3 principais>. (observado: <arquivo> | inferido)

## Consistência

- O que nunca pode estar errado ou ser perdido: <dinheiro, estoque, lugares, ...>. (fornecido)
- O que pode ficar desatualizado, e por quanto tempo: <por exemplo contagem de visualizações, até 5 min>. (fornecido | inferido)

## Latência e disponibilidade

- Tempo de resposta esperado nas ações principais (p95): <por exemplo 300 ms>. (fornecido | inferido)
- Disponibilidade esperada e o impacto de uma hora fora do ar: <por exemplo 99,5% ao mês; perde vendas>. (fornecido)
- Perda de dados aceitável num desastre (RPO) e tempo para voltar (RTO): <por exemplo 1 h e 4 h>. (fornecido | inferido)

## Dados sensíveis e obrigações legais

- Dados pessoais, de saúde, de pagamento, ou nenhum: <lista>. (fornecido | observado: <arquivo>)
- Obrigações: <LGPD, retenção, auditoria, residência dos dados>. (fornecido | inferido)

## Equipe

- Quantas pessoas vão operar e a experiência com servidores, bancos e containers. (fornecido)

## Orçamento

- Orçamento mensal de infraestrutura: <faixa>. (fornecido)

## Alvo de infraestrutura

- Alvo: <VPS | PaaS | containers gerenciados | Kubernetes | ainda não sei>. (fornecido)
- Indício no repositório, se houver: <arquivo>. (observado: <arquivo>)

## Restrições

- Linguagem, framework, provedor, serviços já contratados, prazos, coisas que a equipe não quer operar. (fornecido | observado: <arquivo>)

## Arquitetura atual

<!-- Only for an existing system; otherwise: "Sistema novo, sem arquitetura atual." -->
- Componente: <nome>, <tecnologia>, <papel>. (observado: <arquivo>)
- Banco, cache, fila: <...>. (observado: <arquivo>)
- Forma de deploy: <...>. (observado: <arquivo>)

## Estimativa de capacidade

<!-- Show every step of the arithmetic and the premises it uses. Mark as estimate what depends on an inferido premise. -->
- Requisições por segundo, média: <usuários × ações ÷ segundos do período = N req/s>. (estimativa se depender de inferido)
- Requisições por segundo, pico: <média × fator de pico = N req/s>.
- Armazenamento por ano: <registros × tamanho = N GB>.
- Banda de saída por mês: <respostas × tamanho médio + arquivos ou mídia servidos = N GB ou TB>.
