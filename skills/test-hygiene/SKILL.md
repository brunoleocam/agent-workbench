---
name: test-hygiene
description: Reviews or writes tests so each one proves a behavior, fails for the right reason, and stays deterministic. Use when adding, cleaning, or reviewing tests (higiene de teste, teste frágil, teste que não prova nada).
---

# Higiene de teste

Teste é evidência de comportamento, não descrição da implementação interna.

Ao escrever ou revisar:

- O nome diz o comportamento e a condição.
- Um teste falha por um motivo. Se precisa de vários asserts sem relação, separe.
- Arrange, act, assert visíveis. Sem dado mágico espalhado.
- Determinístico: sem `sleep` para sincronizar, sem relógio ou aleatório sem controle, sem rede real em teste de unidade.
- Não depende da ordem da suíte.
- Não afirma detalhe privado (quantas vezes uma função interna foi chamada) se o contrato é o resultado observável.
- O teste que cobre um bug falha no código antigo pelo motivo do bug.
- Fixture e mock explícitos. Mock só na fronteira que você não controla.

Se um teste passa com a implementação errada, ele não serve. Reescreva o teste antes de confiar nele.

Aplique `tdd` quando ainda for criar o teste. Esta skill julga a qualidade; não substitui ver o teste falhar.
